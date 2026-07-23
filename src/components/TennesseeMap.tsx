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

type WatershedMode = "huc4" | "huc6" | "huc8";

type ViewBox = {
  minLon: number;
  maxLon: number;
  minLat: number;
  maxLat: number;
};

const WIDTH = 960;
const HEIGHT = 315;
const PADDING = 18;
const WATERSHED_MODES: Array<{ key: WatershedMode; label: string; detail: string }> = [
  { key: "huc4", label: "HUC4", detail: "regional basins" },
  { key: "huc6", label: "HUC6", detail: "subbasins" },
  { key: "huc8", label: "HUC8", detail: "catalog units" }
];

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

function watershedCode(feature: GeoJsonFeature, mode: WatershedMode) {
  const huc8 = String(feature.properties.huc8 ?? "");
  const length = mode === "huc4" ? 4 : mode === "huc6" ? 6 : 8;
  return huc8.slice(0, length) || "unknown";
}

function watershedName(feature: GeoJsonFeature) {
  return String(feature.properties.name ?? "Watershed").trim() || "Watershed";
}

function watershedArea(feature: GeoJsonFeature) {
  const parsed = Number(feature.properties.areasqkm ?? 0);
  return Number.isFinite(parsed) ? parsed : 0;
}

function representativeWatershedName(names: Map<string, number>) {
  const sorted = Array.from(names.entries()).sort((a, b) => b[1] - a[1]);
  return sorted[0]?.[0] ?? "Watershed";
}

function splitWatershedLabel(label: string, maxLength: number) {
  const words = label.replaceAll("-", " - ").split(/\s+/).filter(Boolean);
  const lines: string[] = [];

  words.forEach((word) => {
    const current = lines[lines.length - 1] ?? "";
    const next = current ? `${current} ${word}` : word;

    if (next.length <= maxLength || current.length === 0) {
      lines[lines.length - 1] = next;
      return;
    }

    lines.push(word);
  });

  return lines.slice(0, 3);
}

function watershedLabelPositions(
  collection: GeoJsonCollection | null,
  mode: WatershedMode,
  viewBox: ViewBox | null
) {
  if (!collection || !viewBox) {
    return [];
  }

  const groups = new Map<string, { points: number[][]; names: Map<string, number> }>();
  collection.features.forEach((feature) => {
    const code = watershedCode(feature, mode);
    const current = groups.get(code) ?? { points: [], names: new Map<string, number>() };
    const name = watershedName(feature);

    current.points.push(...flattenCoordinates(feature));
    current.names.set(name, (current.names.get(name) ?? 0) + watershedArea(feature));
    groups.set(code, current);
  });

  return Array.from(groups.entries())
    .map(([code, group]) => {
      const points = group.points;
      const usablePoints = points.filter((point) => Number.isFinite(point[0]) && Number.isFinite(point[1]));
      const lon = usablePoints.reduce((total, point) => total + point[0], 0) / usablePoints.length;
      const lat = usablePoints.reduce((total, point) => total + point[1], 0) / usablePoints.length;
      const projected = projectPoint(lon, lat, viewBox);
      return {
        code,
        label: representativeWatershedName(group.names),
        x: projected.x,
        y: projected.y
      };
    })
    .filter((label) => Number.isFinite(label.x) && Number.isFinite(label.y))
    .sort((a, b) => a.code.localeCompare(b.code));
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
  const [watershedMode, setWatershedMode] = useState<WatershedMode>("huc6");

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
  const watershedLabels = useMemo(
    () => watershedLabelPositions(huc8Layer, watershedMode, viewBox),
    [huc8Layer, viewBox, watershedMode]
  );

  return (
    <section id="map" className="card scroll-mt-6 overflow-hidden">
      <div className="border-b border-ink/10 p-5">
        <div>
          <p className="text-xs font-semibold uppercase tracking-normal text-river">Statewide map</p>
          <h2 className="mt-1 text-2xl font-semibold">County water-health view</h2>
        </div>
      </div>
      <div className="grid gap-4 p-4 lg:grid-cols-[minmax(0,1fr)_18rem]">
        <div className="relative rounded-lg border border-ink/15 bg-[#dbe7de] p-2">
          {countyLayer && huc8Layer && viewBox ? (
            <>
              <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="h-auto w-full rounded-md bg-[#eef2e4]">
                {huc8Layer.features.map((feature, index) => (
                  <path
                    key={`huc8-${index}`}
                    d={featurePath(feature, viewBox)}
                    fill="#d5e4d8"
                    fillOpacity={watershedMode === "huc8" ? "0.78" : "0.6"}
                    stroke="#547a5b"
                    strokeOpacity={watershedMode === "huc8" ? "0.82" : "0.58"}
                    strokeWidth={watershedMode === "huc8" ? "1.45" : "1.1"}
                  />
                ))}
                {watershedLabels.map((label) => {
                  const lines = splitWatershedLabel(label.label, watershedMode === "huc8" ? 15 : 20);

                  return (
                    <text
                      key={label.code}
                      x={label.x}
                      y={label.y}
                      textAnchor="middle"
                      dominantBaseline="middle"
                      fill="#28443c"
                      fillOpacity="0.58"
                      stroke="#eef2e4"
                      strokeWidth="3"
                      paintOrder="stroke"
                      fontSize={watershedMode === "huc4" ? "14" : watershedMode === "huc6" ? "11" : "7.5"}
                      fontWeight="700"
                      style={{ pointerEvents: "none" }}
                    >
                      {lines.map((line, index) => (
                        <tspan
                          key={`${label.code}-${line}-${index}`}
                          x={label.x}
                          dy={index === 0 ? `${(1 - lines.length) * 0.55}em` : "1.08em"}
                        >
                          {line}
                        </tspan>
                      ))}
                    </text>
                  );
                })}
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
                        strokeOpacity={isActive ? "0.96" : "0.78"}
                        strokeWidth={isActive ? "2.3" : "1.25"}
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
            <div className="flex min-h-[260px] items-center justify-center rounded-md bg-white text-sm text-ink/60">
              Loading Tennessee layers...
            </div>
          )}
        </div>

        <aside className="space-y-3">
          <div className="rounded-lg border border-ink/10 bg-white p-4">
            <p className="text-xs font-semibold uppercase tracking-normal text-river">Watershed view</p>
            <div className="mt-3 grid grid-cols-3 gap-1 rounded-md bg-sand p-1">
              {WATERSHED_MODES.map((mode) => {
                const isActive = watershedMode === mode.key;
                return (
                  <button
                    key={mode.key}
                    type="button"
                    className={`rounded px-2 py-2 text-center text-xs font-semibold transition ${
                      isActive ? "bg-river text-white" : "text-ink/70 hover:bg-white"
                    }`}
                    onClick={() => setWatershedMode(mode.key)}
                  >
                    {mode.label}
                  </button>
                );
              })}
            </div>
            <p className="mt-2 text-xs leading-5 text-ink/60">
              Showing {WATERSHED_MODES.find((mode) => mode.key === watershedMode)?.detail}.
            </p>
          </div>

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

          <div className="rounded-lg border border-ink/10 bg-white p-4">
            <p className="text-xs font-semibold uppercase tracking-normal text-river">Legend</p>
            <ul className="mt-3 space-y-2 text-sm">
              <li className="flex items-center gap-3">
                <span className="h-4 w-4 rounded-sm border border-[#547a5b] bg-[#d5e4d8]" /> Watershed background
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
