"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
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

const WIDTH = 820;
const HEIGHT = 220;
const PADDING = 14;

function flattenCoordinates(feature: GeoJsonFeature): number[][] {
  if (feature.geometry.type === "Polygon") {
    return (feature.geometry.coordinates as number[][][]).flat();
  }
  return (feature.geometry.coordinates as number[][][][]).flat(2);
}

function computeViewBox(collection: GeoJsonCollection): ViewBox {
  const points = collection.features.flatMap(flattenCoordinates);
  const lons = points.map((point) => point[0]);
  const lats = points.map((point) => point[1]);

  return {
    minLon: Math.min(...lons),
    maxLon: Math.max(...lons),
    minLat: Math.min(...lats),
    maxLat: Math.max(...lats)
  };
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

export function TennesseeMap({
  counties,
  countyDetails
}: {
  counties: CountyIndexRecord[];
  countyDetails: CountyRecord[];
}) {
  const router = useRouter();
  const [countyLayer, setCountyLayer] = useState<GeoJsonCollection | null>(null);
  const [huc8Layer, setHuc8Layer] = useState<GeoJsonCollection | null>(null);
  const [hoveredCounty, setHoveredCounty] = useState<string | null>(null);
  const [selectedCounty, setSelectedCounty] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function loadLayers() {
      const [countiesData, huc8Data] = await Promise.all([
        fetch("/data/layers/counties.geojson").then((response) => response.json()),
        fetch("/data/layers/huc8.geojson").then((response) => response.json())
      ]);

      if (!cancelled) {
        setCountyLayer(countiesData);
        setHuc8Layer(huc8Data);
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

  const viewBox = useMemo(() => {
    if (!countyLayer) {
      return null;
    }
    return computeViewBox(countyLayer);
  }, [countyLayer]);

  const featuredCounties = useMemo(() => counties.filter((county) => county.isFeatured), [counties]);

  return (
    <section id="map" className="card scroll-mt-6 overflow-hidden">
      <div className="flex flex-col gap-3 border-b border-ink/10 p-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-normal text-river">Statewide map</p>
          <h2 className="mt-1 text-2xl font-semibold">Counties and HUC8 watersheds</h2>
        </div>
        <div className="flex flex-wrap gap-2 text-xs font-medium text-ink/65">
          <span className="rounded-md border border-ink/10 px-3 py-2">County boundaries</span>
          <span className="rounded-md border border-ink/10 px-3 py-2">Watershed layer</span>
        </div>
      </div>
      <div className="grid gap-5 p-5 lg:grid-cols-[minmax(0,1.45fr)_20rem]">
        <div className="relative rounded-lg border border-ink/10 bg-foam p-2">
          {countyLayer && huc8Layer && viewBox ? (
            <>
              <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="h-auto w-full rounded-md bg-[#fbfaf5]">
                {huc8Layer.features.map((feature, index) => (
                  <path
                    key={`huc8-${index}`}
                    d={featurePath(feature, viewBox)}
                    fill="#e6ede8"
                    fillOpacity="0.58"
                    stroke="#6f8f5f"
                    strokeOpacity="0.5"
                    strokeWidth="1"
                  />
                ))}
                {countyLayer.features.map((feature) => {
                  const countyName = String(feature.properties.NAME);
                  const county = countyLookup[countyName];
                  const isActive = activeCountyName === countyName;

                  return (
                    <g key={`county-${String(feature.properties.GEOID)}`}>
                      <path
                        d={featurePath(feature, viewBox)}
                        fill={isActive ? "#3b6e63" : "rgba(255,255,255,0.14)"}
                        stroke="#2f3834"
                        strokeOpacity={isActive ? "0.92" : "0.82"}
                        strokeWidth={isActive ? "2.15" : "1.4"}
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
              </svg>
            </>
          ) : (
            <div className="flex min-h-[220px] items-center justify-center rounded-md bg-white text-sm text-ink/60">
              Loading Tennessee layers...
            </div>
          )}
        </div>

        <aside className="space-y-3">
          <div className="rounded-lg border border-ink/10 bg-white p-4">
            <p className="text-xs font-semibold uppercase tracking-normal text-river">Selected county</p>
            <h3 className="mt-2 text-lg font-semibold text-ink">
              {activeCountyName ?? "Statewide view"}
            </h3>
            {activeCountyDetail ? (
              <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                <div>
                  <dt className="text-ink/55">Region</dt>
                  <dd className="font-medium text-ink">{activeCountyDetail.region}</dd>
                </div>
                <div>
                  <dt className="text-ink/55">Impaired miles</dt>
                  <dd className="font-medium text-ink">{activeCountyDetail.streamMiles.impaired.toFixed(1)}</dd>
                </div>
                <div>
                  <dt className="text-ink/55">Monitoring</dt>
                  <dd className="font-medium text-ink">{activeCountyDetail.monitoringSummary.stations}</dd>
                </div>
                <div>
                  <dt className="text-ink/55">Active permits</dt>
                  <dd className="font-medium text-ink">{activeCountyDetail.permittingSummary.activePermits}</dd>
                </div>
              </dl>
            ) : null}
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

          <div className="rounded-lg bg-ink p-4 text-white">
            <p className="text-xs font-semibold uppercase tracking-normal text-white/70">Legend</p>
            <ul className="mt-3 space-y-2 text-sm">
              <li className="flex items-center gap-3"><span className="h-4 w-4 rounded-sm bg-mist" /> Watershed background</li>
              <li className="flex items-center gap-3"><span className="h-0 w-6 border-t-2 border-ink" /> County boundary</li>
              <li className="flex items-center gap-3"><span className="h-4 w-4 rounded-sm bg-river" /> Active county highlight</li>
            </ul>
          </div>

          <div className="rounded-lg border border-ink/10 bg-white p-4">
            <p className="text-xs font-semibold uppercase tracking-normal text-river">Featured counties</p>
            <ul className="mt-3 space-y-2 text-sm">
              {featuredCounties.map((county) => (
                <li key={county.slug}>
                  <button
                    type="button"
                    className="w-full rounded-md border border-ink/10 bg-sand px-4 py-3 text-left transition hover:border-gold/45"
                    onClick={() => router.push(`/counties/${county.slug}`)}
                  >
                    <span className="block font-medium text-ink">{county.name} County</span>
                    <span className="block text-xs text-ink/60">{county.region}</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </aside>
      </div>
    </section>
  );
}
