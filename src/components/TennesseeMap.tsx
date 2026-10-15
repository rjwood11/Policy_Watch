"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { GlossaryText } from "@/components/GlossaryText";
import { assetPath } from "@/lib/assetPath";
import type { CountyIndexRecord, CountyRecord } from "@/lib/data";

type GeoJsonFeature = {
  type: "Feature";
  properties: Record<string, string | number | null>;
  geometry: {
    type: "Polygon" | "MultiPolygon";
    coordinates: number[][][] | number[][][][];
  };
};

type GeoJsonCollection = {
  type: "FeatureCollection";
  features: GeoJsonFeature[];
};

type ViewBox = {
  minLon: number;
  maxLon: number;
  minLat: number;
  maxLat: number;
};

type Point = [number, number];

const WIDTH = 960;
const HEIGHT = 315;
const PADDING = 18;

function flattenCoordinates(feature: GeoJsonFeature): number[][] {
  if (feature.geometry.type === "Polygon") {
    return (feature.geometry.coordinates as number[][][]).flat();
  }
  return (feature.geometry.coordinates as number[][][][]).flat(2);
}

function computeViewBox(collection: GeoJsonCollection): ViewBox {
  const points = collection.features.flatMap(flattenCoordinates);
  return coordinateBounds(points);
}

function coordinateBounds(points: number[][]): ViewBox {
  const lons = points.map((point) => point[0]);
  const lats = points.map((point) => point[1]);

  return {
    minLon: Math.min(...lons),
    maxLon: Math.max(...lons),
    minLat: Math.min(...lats),
    maxLat: Math.max(...lats)
  };
}

function featureBounds(feature: GeoJsonFeature) {
  return coordinateBounds(flattenCoordinates(feature));
}

function boundsOverlap(a: ViewBox, b: ViewBox) {
  return a.minLon <= b.maxLon && a.maxLon >= b.minLon && a.minLat <= b.maxLat && a.maxLat >= b.minLat;
}

function pointInRing(point: Point, ring: number[][]) {
  const [x, y] = point;
  let inside = false;

  for (let index = 0, previous = ring.length - 1; index < ring.length; previous = index, index += 1) {
    const [xi, yi] = ring[index];
    const [xj, yj] = ring[previous];
    const intersects = yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi;

    if (intersects) {
      inside = !inside;
    }
  }

  return inside;
}

function pointInPolygon(point: Point, rings: number[][][]) {
  if (!pointInRing(point, rings[0])) {
    return false;
  }

  return rings.slice(1).every((ring) => !pointInRing(point, ring));
}

function featureContainsPoint(feature: GeoJsonFeature, point: Point) {
  if (feature.geometry.type === "Polygon") {
    return pointInPolygon(point, feature.geometry.coordinates as number[][][]);
  }

  return (feature.geometry.coordinates as number[][][][]).some((polygon) => pointInPolygon(point, polygon));
}

function huc6Name(feature: GeoJsonFeature) {
  return String(feature.properties.name ?? "HUC6 basin").trim() || "HUC6 basin";
}

function sampleFeaturePoints(feature: GeoJsonFeature, maxSamples = 72) {
  const points = flattenCoordinates(feature).filter(
    (point): point is Point => Number.isFinite(point[0]) && Number.isFinite(point[1])
  );

  if (points.length <= maxSamples) {
    return points;
  }

  const step = Math.max(1, Math.floor(points.length / maxSamples));
  return points.filter((_, index) => index % step === 0).slice(0, maxSamples);
}

function huc6NamesForCounty(countyFeature: GeoJsonFeature | undefined, huc6Layer: GeoJsonCollection | null) {
  if (!countyFeature || !huc6Layer) {
    return [];
  }

  const countyBounds = featureBounds(countyFeature);
  const countyPoints = sampleFeaturePoints(countyFeature);
  const names = huc6Layer.features
    .filter((huc6Feature) => boundsOverlap(countyBounds, featureBounds(huc6Feature)))
    .filter((huc6Feature) => countyPoints.some((point) => featureContainsPoint(huc6Feature, point)))
    .map(huc6Name);

  return [...new Set(names)].sort();
}

function projectPoint(lon: number, lat: number, viewBox: ViewBox) {
  const usableWidth = WIDTH - PADDING * 2;
  const usableHeight = HEIGHT - PADDING * 2;
  const lonRange = viewBox.maxLon - viewBox.minLon;
  const latRange = viewBox.maxLat - viewBox.minLat;
  const scale = Math.min(usableWidth / lonRange, usableHeight / latRange);
  const xOffset = (WIDTH - lonRange * scale) / 2;
  const yOffset = (HEIGHT - latRange * scale) / 2;

  return {
    x: xOffset + (lon - viewBox.minLon) * scale,
    y: HEIGHT - (yOffset + (lat - viewBox.minLat) * scale)
  };
}

function polygonPath(rings: number[][][], viewBox: ViewBox) {
  return rings
    .map((ring) =>
      ring
        .map((point, index) => {
          const projected = projectPoint(point[0], point[1], viewBox);
          return `${index === 0 ? "M" : "L"}${projected.x.toFixed(2)},${projected.y.toFixed(2)}`;
        })
        .join(" ") + " Z"
    )
    .join(" ");
}

function featurePath(feature: GeoJsonFeature, viewBox: ViewBox) {
  if (feature.geometry.type === "Polygon") {
    return polygonPath(feature.geometry.coordinates as number[][][], viewBox);
  }
  return (feature.geometry.coordinates as number[][][][])
    .map((polygon) => polygonPath(polygon, viewBox))
    .join(" ");
}

function ActiveCountyPanel({
  county,
  huc6Basins
}: {
  county: CountyRecord | undefined;
  huc6Basins: string[];
}) {
  if (!county) {
    return (
      <div className="mt-2 rounded-md border border-ink/10 bg-white/90 px-4 py-3 text-sm">
        <p className="font-semibold text-ink">Hover or search for a county</p>
        <p className="mt-1 text-xs leading-5 text-ink/60">
          The selected county&apos;s HUC6 basin and local map context will appear here.
        </p>
      </div>
    );
  }

  return (
    <div className="mt-2 grid gap-3 rounded-md border border-ink/10 bg-white/90 px-4 py-3 text-sm md:grid-cols-[1fr_1.15fr]">
      <div>
        <p className="text-xs font-semibold uppercase tracking-normal text-river">Selected county</p>
        <h3 className="mt-1 text-lg font-semibold text-ink">{county.name} County</h3>
        <p className="mt-1 text-xs text-ink/60">{county.region}</p>
      </div>
      <div className="grid gap-3 sm:grid-cols-[1fr_0.9fr]">
        <div>
          <p className="text-xs font-semibold uppercase tracking-normal text-river">
            HUC6 basin{huc6Basins.length === 1 ? "" : "s"}
          </p>
          <p className="mt-1 text-xs leading-5 text-ink/70">
            {huc6Basins.length > 0 ? huc6Basins.join(", ") : "HUC6 basin not resolved"}
          </p>
        </div>
        <dl className="grid grid-cols-3 gap-2 text-xs">
          <div>
            <dt className="text-ink/55">Impaired</dt>
            <dd className="font-semibold text-ink">{county.streamMiles.impaired.toFixed(1)} mi</dd>
          </div>
          <div>
            <dt className="text-ink/55">Monitoring</dt>
            <dd className="font-semibold text-ink">{county.monitoringSummary.stations}</dd>
          </div>
          <div>
            <dt className="text-ink/55">Permits</dt>
            <dd className="font-semibold text-ink">{county.permittingSummary.activePermits}</dd>
          </div>
        </dl>
      </div>
    </div>
  );
}

export function TennesseeMap({
  counties,
  countyDetails
}: {
  counties: CountyIndexRecord[];
  countyDetails: CountyRecord[];
}) {
  const router = useRouter();
  const [countyLayer, setCountyLayer] = useState<GeoJsonCollection | null>(null);
  const [huc6Layer, setHuc6Layer] = useState<GeoJsonCollection | null>(null);
  const [hoveredCounty, setHoveredCounty] = useState<string | null>(null);
  const [selectedCounty, setSelectedCounty] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function loadLayers() {
      const [countiesData, huc6Data] = await Promise.all([
        fetch(assetPath("/data/layers/counties.geojson")).then((response) => response.json()),
        fetch(assetPath("/data/layers/huc6.geojson")).then((response) => response.json())
      ]);

      if (!cancelled) {
        setCountyLayer(countiesData);
        setHuc6Layer(huc6Data);
      }
    }

    void loadLayers();
    return () => {
      cancelled = true;
    };
  }, []);

  const countyLookup = useMemo(() => Object.fromEntries(counties.map((county) => [county.name, county])), [counties]);
  const countyDetailLookup = useMemo(
    () => Object.fromEntries(countyDetails.map((county) => [county.name, county])),
    [countyDetails]
  );
  const allCountyNames = useMemo(() => counties.map((county) => county.name).sort(), [counties]);
  const searchResults = useMemo(() => {
    const query = searchTerm.trim().toLowerCase();
    if (!query) {
      return [];
    }
    return allCountyNames.filter((name) => name.toLowerCase().includes(query)).slice(0, 8);
  }, [allCountyNames, searchTerm]);

  const activeCountyName = hoveredCounty ?? selectedCounty;
  const activeCountyDetail = activeCountyName ? countyDetailLookup[activeCountyName] : undefined;
  const activeCountyFeature = useMemo(
    () => countyLayer?.features.find((feature) => String(feature.properties.NAME) === activeCountyName),
    [activeCountyName, countyLayer]
  );
  const activeHuc6Basins = useMemo(
    () => huc6NamesForCounty(activeCountyFeature, huc6Layer),
    [activeCountyFeature, huc6Layer]
  );

  const viewBox = useMemo(() => {
    if (!countyLayer) {
      return null;
    }
    return computeViewBox(countyLayer);
  }, [countyLayer]);

  return (
    <section id="map" className="card scroll-mt-6 overflow-hidden">
      <div className="border-b border-ink/10 p-5">
        <div>
          <p className="text-xs font-semibold uppercase tracking-normal text-river">Statewide map</p>
          <h2 className="mt-1 text-2xl font-semibold">Select a County to Explore Local Issues</h2>
        </div>
      </div>
      <div className="grid gap-4 p-4 lg:grid-cols-[minmax(0,1fr)_18rem]">
        <div className="relative rounded-lg border border-ink/15 bg-[#dbe7de] p-2">
          {countyLayer && huc6Layer && viewBox ? (
            <>
              <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="h-auto w-full rounded-md bg-[#eef2e4]">
                {countyLayer.features.map((feature) => {
                  const countyName = String(feature.properties.NAME);
                  const county = countyLookup[countyName];
                  const isActive = activeCountyName === countyName;

                  return (
                    <g key={`county-${String(feature.properties.GEOID)}`}>
                      <path
                        d={featurePath(feature, viewBox)}
                        fill={isActive ? "#244f45" : "rgba(255,255,255,0.3)"}
                        stroke="#25312d"
                        strokeOpacity={isActive ? "0.98" : "0.9"}
                        strokeWidth={isActive ? "2.8" : "1.65"}
                        className="cursor-pointer transition-all"
                        onMouseEnter={() => setHoveredCounty(countyName)}
                        onMouseLeave={() => setHoveredCounty((current) => (current === countyName ? null : current))}
                        onClick={() => {
                          setSelectedCounty(countyName);
                          if (county) {
                            router.push(`/counties/${county.slug}`);
                          }
                        }}
                      />
                    </g>
                  );
                })}
                <g aria-hidden="true">
                  {huc6Layer.features.map((feature, index) => (
                    <path
                      key={`huc6-outline-${String(feature.properties.huc6 ?? index)}`}
                      d={featurePath(feature, viewBox)}
                      fill="none"
                      stroke="#547a5b"
                      strokeOpacity="0.42"
                      strokeWidth="1.05"
                      style={{ pointerEvents: "none" }}
                    />
                  ))}
                </g>
              </svg>
              <ActiveCountyPanel county={activeCountyDetail} huc6Basins={activeHuc6Basins} />
            </>
          ) : (
            <div className="flex min-h-[260px] items-center justify-center rounded-md bg-white text-sm text-ink/60">
              Loading Tennessee layers...
            </div>
          )}
        </div>

        <aside className="space-y-3">
          <div className="rounded-lg border border-ink/10 bg-white p-4">
            <p className="text-xs font-semibold uppercase tracking-normal text-river">Watershed view</p>
            <p className="mt-2 text-xs leading-5 text-ink/60">
              <GlossaryText text="Showing USGS WBD HUC6 basin boundaries. Hover or select a county to see its local basin context below the map." />
            </p>
            <Link href="/glossary#huc6" className="mt-2 inline-block text-xs">What do these acronyms mean?</Link>
          </div>

          <div className="rounded-lg border border-ink/10 bg-white p-4">
            <p className="text-xs font-semibold uppercase tracking-normal text-river">County search</p>
            <input
              type="search"
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
              placeholder="Search Tennessee counties"
              className="mt-4 w-full rounded-md border border-ink/15 bg-sand px-4 py-3 text-sm text-ink outline-none ring-0"
            />
            {searchResults.length > 0 ? (
              <ul className="mt-3 space-y-2 text-sm">
                {searchResults.map((name) => {
                  const county = countyLookup[name];
                  return (
                    <li key={name}>
                      <button
                        type="button"
                        className="w-full rounded-md border border-ink/10 bg-white px-4 py-3 text-left text-ink transition hover:border-gold/45"
                        onClick={() => {
                          setSelectedCounty(name);
                          setHoveredCounty(null);
                          setSearchTerm(name);
                          if (county) {
                            router.push(`/counties/${county.slug}`);
                          }
                        }}
                      >
                        <span className="block font-medium">{name} County</span>
                        <span className="block text-xs text-ink/60">
                          {county?.isFeatured ? "Featured county page" : "County summary page"}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            ) : null}
          </div>

          <div className="rounded-lg border border-ink/10 bg-white p-4">
            <p className="text-xs font-semibold uppercase tracking-normal text-river">Legend</p>
            <ul className="mt-3 space-y-2 text-sm">
              <li className="flex items-center gap-3">
                <span className="h-0 w-6 border-t-2 border-[#547a5b]" /> HUC6 basin boundary
              </li>
              <li className="flex items-center gap-3">
                <span className="h-0 w-6 border-t-2 border-[#25312d]" /> County boundary
              </li>
              <li className="flex items-center gap-3">
                <span className="h-4 w-4 rounded-sm bg-[#244f45]" /> Active county highlight
              </li>
            </ul>
          </div>
        </aside>
      </div>
    </section>
  );
}
