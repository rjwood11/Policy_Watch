"""Download a coarse Tennessee Annual NLCD subset and export small county rasters."""

from __future__ import annotations

import argparse
import json
import os
from datetime import date
from pathlib import Path
from importlib.util import find_spec

from pyproj import CRS, Transformer

# Old system GIS installations can leave a PROJ_LIB path that breaks Rasterio.
rasterio_spec = find_spec("rasterio")
bundled_proj = Path(rasterio_spec.origin).parent / "proj_data" if rasterio_spec else None
for variable in ("PROJ_DATA", "PROJ_LIB"):
    configured = os.environ.get(variable)
    if configured and not (Path(configured) / "proj.db").is_file() and bundled_proj and bundled_proj.is_dir():
        os.environ[variable] = str(bundled_proj)

import geopandas as gpd
import numpy as np
import rasterio
import requests
from PIL import Image
from rasterio.io import MemoryFile
from rasterio.mask import mask

from scripts.common.prototype_config import LAYERS_DIR, METADATA_DIR, PUBLIC_DATA, RAW_DIR

YEAR = 2025
RESOLUTION = 300  # Web Mercator meters, approximately 240–250 ground meters in Tennessee.
SOURCE_URL = "https://dmsdata.cr.usgs.gov/geoserver/mrlc_Land-Cover-Native_conus_year_data/wcs"
COVERAGE = "mrlc_Land-Cover-Native_conus_year_data:Land-Cover-Native_conus_year_data"
OUTPUT_DIR = PUBLIC_DATA / "landuse"
CACHE_PATH = RAW_DIR / f"annual-nlcd-{YEAR}-tn-{RESOLUTION}m.tif"
CLASSES = [
    {"id": 1, "label": "Built-up / urban", "color": "#c43c39", "codes": [22, 23, 24],
     "description": "Developed land with housing, roads, businesses or industry. Groups low, medium and high intensity development (20–100% impervious cover)."},
    {"id": 2, "label": "Developed open space", "color": "#e8aa8b", "codes": [21],
     "description": "Mostly vegetation within developed settings, including lawns, parks, golf courses and large-lot housing. Less than 20% impervious cover; this is not a rural designation."},
    {"id": 3, "label": "Agriculture", "color": "#e5c65c", "codes": [81, 82],
     "description": "Pasture and hay fields, cultivated crops and orchards. Combines NLCD pasture/hay and cultivated crop classes."},
    {"id": 4, "label": "Forest", "color": "#4e8650", "codes": [41, 42, 43],
     "description": "Deciduous, evergreen and mixed forest. These wooded areas are common in rural landscapes; NLCD does not assign an official urban/rural designation."},
    {"id": 5, "label": "Grassland / shrubland", "color": "#a7b87a", "codes": [52, 71],
     "description": "Grass, herbaceous plants and low shrubs, including young woody vegetation. Often open rural landscapes; distinct from the pasture/hay agriculture class."},
    {"id": 6, "label": "Wetlands", "color": "#63aaa9", "codes": [90, 95],
     "description": "Woody and herbaceous wetlands with periodically saturated soils or standing water. Land-cover mapping does not establish a regulatory wetland boundary."},
    {"id": 7, "label": "Open water", "color": "#497fb7", "codes": [11],
     "description": "Lakes, reservoirs, rivers and other open water with little vegetation or exposed soil."},
    {"id": 8, "label": "Barren land", "color": "#b1a99d", "codes": [31],
     "description": "Exposed rock, sand or clay with little vegetation, including some quarries and excavated areas."},
    {"id": 9, "label": "Perennial ice / snow", "color": "#dce9f5", "codes": [12],
     "description": "Persistent ice or snow cover. Retained for completeness of the NLCD classification."},
]


def download_subset(counties: gpd.GeoDataFrame, force: bool) -> None:
    if CACHE_PATH.exists() and not force:
        return
    bounds = counties.total_bounds
    params = {
        "service": "WCS", "version": "2.0.1", "request": "GetCoverage",
        "coverageId": COVERAGE.replace(":", "__"),
        "subsettingCrs": "http://www.opengis.net/def/crs/EPSG/0/3857",
        "outputCrs": "http://www.opengis.net/def/crs/EPSG/0/3857",
        "subset": [f"X({bounds[0]},{bounds[2]})", f"Y({bounds[1]},{bounds[3]})", f'time("{YEAR}-01-01T00:00:00Z")'],
        "scaleSize": f"i({int(np.ceil((bounds[2] - bounds[0]) / RESOLUTION))}),j({int(np.ceil((bounds[3] - bounds[1]) / RESOLUTION))})",
        "format": "image/tiff", "interpolation": "http://www.opengis.net/def/interpolation/OGC/1/nearest-neighbor",
    }
    print(f"Downloading Tennessee-only {YEAR} Annual NLCD at coarse resolution...", flush=True)
    response = requests.get(SOURCE_URL, params=params, timeout=180)
    response.raise_for_status()
    if not response.content.startswith((b"II", b"MM")):
        raise ValueError(f"USGS did not return a GeoTIFF; previous imagery retained: {response.text[:900]}")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = CACHE_PATH.with_suffix(".tmp.tif")
    with MemoryFile(response.content) as memory:
        with memory.open() as source:
            if source.count != 1 or not source.crs or CRS.from_wkt(source.crs.to_wkt()).to_epsg() != 3857:
                raise ValueError("USGS returned an unexpected raster format / projection.")
            data = source.read(1)
            if not np.isin(data, [0, 250, 255] + [code for item in CLASSES for code in item["codes"]]).all():
                raise ValueError(f"USGS returned unknown NLCD classes: {np.unique(data)}")
            profile = source.profile.copy()
            profile.update(compress="deflate")
            with rasterio.open(temp_path, "w", **profile) as output:
                output.write(data, 1)
                output.update_tags(source=SOURCE_URL, year=str(YEAR), resampling="nearest")
    temp_path.replace(CACHE_PATH)
    print(f"Cached regional raster: {CACHE_PATH.stat().st_size / 1024 / 1024:.2f} MB", flush=True)


def write_source_metadata(manifest: dict) -> None:
    path = METADATA_DIR / "data-sources.json"
    sources = json.loads(path.read_text(encoding="utf8"))
    sources = [source for source in sources if source["dataset"] != "Land use / land cover"]
    sources.append({
        "dataset": "Land use / land cover",
        "purpose": "Basic county land-cover context with category explanations on hover.",
        "sourceName": f"USGS Annual NLCD {manifest['year']}",
        "sourceUrl": "https://www.usgs.gov/centers/eros/science/annual-nlcd-data-access",
        "refreshFrequency": "Annual source release; regenerate with npm run data:build-landuse",
        "lastUpdated": manifest["retrievedAt"],
        "notes": f"Tennessee-only WCS subset, nearest-neighbor sampled at 300 Web Mercator meters (approximately 240–250 ground meters), grouped into broad classes and masked to county boundaries. Local compressed PNGs are loaded only when enabled. Small features can be omitted; this is land cover, not zoning or an official urban/rural classification. The source observation year is {manifest['year']}.",
    })
    path.write_text(json.dumps(sources, indent=2) + "\n", encoding="utf8")


def apply_cached_landuse_metadata() -> None:
    path = OUTPUT_DIR / "manifest.json"
    if path.exists():
        write_source_metadata(json.loads(path.read_text(encoding="utf8")))


def build_county_rasters(force: bool = False) -> dict:
    counties = gpd.read_file(LAYERS_DIR / "counties.geojson").to_crs("EPSG:3857")
    download_subset(counties, force)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    lookup = np.zeros(256, dtype="uint8")
    palette = [0] * 768
    for item in CLASSES:
        lookup[item["codes"]] = item["id"]
        offset = item["id"] * 3
        palette[offset:offset + 3] = list(bytes.fromhex(item["color"][1:]))
    to_lonlat = Transformer.from_crs(3857, 4326, always_xy=True)
    manifest = {
        "year": YEAR, "retrievedAt": date.fromtimestamp(CACHE_PATH.stat().st_mtime).isoformat(),
        "sourceUrl": SOURCE_URL, "resolutionMeters": RESOLUTION,
        "groundResolutionMeters": 250, "resampling": "nearest neighbor",
        "classes": CLASSES, "counties": {},
    }
    total_bytes = 0
    with rasterio.open(CACHE_PATH) as source:
        for county in counties.itertuples():
            raster, transform = mask(source, [county.geometry], crop=True, filled=True, nodata=0)
            grouped = lookup[raster[0]]
            if not grouped.any():
                raise ValueError(f"No land-cover data for {county.slug}")
            height, width = grouped.shape
            west, south, east, north = rasterio.transform.array_bounds(height, width, transform)
            corners = [(west, north), (east, north), (east, south), (west, south)]
            image_path = OUTPUT_DIR / f"{county.slug}.png"
            image = Image.fromarray(grouped).convert("P")
            image.putpalette(palette)
            image.save(image_path, transparency=0, optimize=True, bits=4)
            total_bytes += image_path.stat().st_size
            manifest["counties"][county.slug] = {
                "imageUrl": f"/data/landuse/{county.slug}.png", "width": width, "height": height,
                "bounds": [west, south, east, north],
                "coordinates": [list(to_lonlat.transform(*point)) for point in corners],
                "classCounts": {str(item["id"]): int(np.count_nonzero(grouped == item["id"])) for item in CLASSES},
                "bytes": image_path.stat().st_size,
            }
    (OUTPUT_DIR / "manifest.json").write_text(json.dumps(manifest, separators=(",", ":")) + "\n", encoding="utf8")
    write_source_metadata(manifest)
    print(f"Exported {len(manifest['counties'])} county images: {total_bytes / 1024 / 1024:.2f} MB total.")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true", help="Download a fresh regional subset even if cached.")
    args = parser.parse_args()
    build_county_rasters(args.download)


if __name__ == "__main__":
    main()
