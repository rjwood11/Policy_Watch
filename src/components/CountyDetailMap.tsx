"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import maplibregl, {
  type GeoJSONSource,
  type LngLatBoundsLike,
  type Map as MapLibreMap,
  type StyleSpecification
} from "maplibre-gl";
import type {
  Feature,
  FeatureCollection,
  GeoJsonProperties,
  Geometry,
  Position
} from "geojson";
import type { CountyMapRecord } from "@/lib/data";
import { TENNESSEE_LEGISLATORS, tennesseeLegislatorUrl } from "@/lib/tennesseeLegislators";

type Bounds = {
  minLon: number;
  minLat: number;
  maxLon: number;
  maxLat: number;
};

type LayerKey = "watershed" | "districts" | "impaired" | "permits" | "echo";
type MapFilter = Parameters<MapLibreMap["setFilter"]>[1];

type AddressCandidate = {
  address: string;
  score: number;
  location: {
    x: number;
    y: number;
  };
  attributes?: Record<string, string | number | null>;
};

type GeocodeResponse = {
  candidates?: AddressCandidate[];
};

const EMPTY_COLLECTION: FeatureCollection = {
  type: "FeatureCollection",
  features: []
};

const EPA_ATTAINS_LINES_URL =
  "https://gispub.epa.gov/arcgis/rest/services/OW/ATTAINS_Assessment/MapServer/1/query";
const TDEC_PERMITS_URL =
  "https://tdeconline.tn.gov/arcgis/rest/services/DWR_Public/MapServer/1/query";
const ECHO_CWA_SERVICES_URL = "https://echodata.epa.gov/echo/cwa_rest_services";
const ATTAINS_CAUSE_FIELDS = [
  { key: "algal_growth", label: "Algal growth" },
  { key: "ammonia", label: "Ammonia" },
  { key: "biotoxins", label: "Biotoxins" },
  { key: "cause_unknown", label: "Cause unknown" },
  { key: "cause_unknown_fish_kills", label: "Cause unknown, fish kills" },
  { key: "cause_unknown_impaired_biota", label: "Cause unknown, impaired biota" },
  { key: "chlorine", label: "Chlorine" },
  { key: "dioxins", label: "Dioxins" },
  { key: "fish_consumption_advisory", label: "Fish consumption advisory" },
  { key: "flow_alterations", label: "Flow alterations" },
  { key: "habitat_alterations", label: "Habitat alterations" },
  { key: "hydrologic_alteration", label: "Hydrologic alteration" },
  { key: "mercury", label: "Mercury" },
  { key: "metals_other_than_mercury", label: "Metals other than mercury" },
  { key: "noxious_aquatic_plants", label: "Noxious aquatic plants" },
  { key: "nuisance_exotic_species", label: "Nuisance exotic species" },
  { key: "nuisance_native_species", label: "Nuisance native species" },
  { key: "nutrients", label: "Nutrients" },
  { key: "oil_and_grease", label: "Oil and grease" },
  { key: "oxygen_depletion", label: "Oxygen depletion" },
  { key: "other_cause", label: "Other cause" },
  { key: "pathogens", label: "Pathogens / bacteria" },
  { key: "pesticides", label: "Pesticides" },
  { key: "pfas", label: "PFAS" },
  { key: "ph_acidity_caustic_conditions", label: "pH / acidity" },
  { key: "polychlorinated_biphenyls_pcbs", label: "PCBs" },
  { key: "radiation", label: "Radiation" },
  { key: "solids_chlorides_sulfates", label: "Solids / chlorides / sulfates" },
  { key: "sediment", label: "Sediment" },
  { key: "taste_color_and_odor", label: "Taste, color, and odor" },
  { key: "temperature", label: "Temperature" },
  { key: "total_toxics", label: "Total toxics" },
  { key: "toxic_inorganics", label: "Toxic inorganics" },
  { key: "toxic_organics", label: "Toxic organics" },
  { key: "trash", label: "Trash" },
  { key: "turbidity", label: "Turbidity" }
];
const ECHO_RESPONSE_SET = 1000;
const ECHO_QUERY_COLUMNS = [
  1, // CWPName
  2, // SourceID
  9, // RegistryID
  24, // FacLat
  25, // FacLong
  46, // PermitName
  98, // CWPSNCStatus
  99, // CWPVioStatus
  100, // CWPSNCStatusDate
  101, // CWPQtrsWithNC
  102, // CWPViolStatus
  103, // CWPQtrsWithSNC
  192, // CWPSNCEventDesc
  195, // CWP13qtrsComplHistory
  204, // ViolFlag
  205, // CurrVioFlag
  215, // EffExceeds
  230 // VioLastYear
].join(",");
const TNMAP_LOCATOR_URL =
  "https://tnmap.tn.gov/arcgis/rest/services/LOCATORS/TN_COMPOSITE/GeocodeServer/findAddressCandidates";

const LAYER_GROUPS: Record<LayerKey, string[]> = {
  watershed: ["watershed-fill", "watershed-line", "watershed-hover-fill", "watershed-hover-line"],
  districts: [
    "congressional-line",
    "senate-line",
    "house-line",
    "congressional-hit-fill",
    "senate-hit-fill",
    "house-hit-fill",
    "congressional-hover-line",
    "senate-hover-line",
    "house-hover-line"
  ],
  impaired: ["epa-impairment-line"],
  permits: ["permit-active", "permit-pending"],
  echo: ["echo-current-violation", "echo-recent-violation"]
};

const INTERACTIVE_LAYERS = [
  "echo-current-violation",
  "echo-recent-violation",
  "permit-active",
  "permit-pending",
  "epa-impairment-line",
  "house-hit-fill",
  "senate-hit-fill",
  "congressional-hit-fill",
  "watershed-fill"
];

const DISTRICT_HOVER_LAYERS = [
  "house-hit-fill",
  "senate-hit-fill",
  "congressional-hit-fill"
];

const HOVER_LAYERS = [
  ...DISTRICT_HOVER_LAYERS,
  "watershed-fill"
];

const MAP_STYLE: StyleSpecification = {
  version: 8,
  glyphs: "https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf",
  sources: {
    osm: {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution: "OpenStreetMap contributors"
    }
  },
  layers: [
    {
      id: "osm",
      type: "raster",
      source: "osm",
      paint: {
        "raster-opacity": 0.88
      }
    }
  ]
};

function featureCollection(collection?: FeatureCollection | null): FeatureCollection {
  return collection ?? EMPTY_COLLECTION;
}

function toFeatureCollection(value: unknown): FeatureCollection {
  if (
    value &&
    typeof value === "object" &&
    (value as FeatureCollection).type === "FeatureCollection" &&
    Array.isArray((value as FeatureCollection).features)
  ) {
    return value as FeatureCollection;
  }
  return EMPTY_COLLECTION;
}

function walkPositions(value: unknown, positions: Position[]) {
  if (!Array.isArray(value)) {
    return;
  }

  if (
    value.length >= 2 &&
    typeof value[0] === "number" &&
    typeof value[1] === "number"
  ) {
    positions.push(value as Position);
    return;
  }

  value.forEach((entry) => walkPositions(entry, positions));
}

function geometryPositions(geometry: Geometry | null | undefined) {
  const positions: Position[] = [];
  if (!geometry || geometry.type === "GeometryCollection") {
    if (geometry?.type === "GeometryCollection") {
      geometry.geometries.forEach((item) => {
        positions.push(...geometryPositions(item));
      });
    }
    return positions;
  }

  walkPositions(geometry.coordinates, positions);
  return positions;
}

function collectionBounds(collections: Array<FeatureCollection | null | undefined>): Bounds | null {
  const positions = collections.flatMap((collection) =>
    featureCollection(collection).features.flatMap((feature) => geometryPositions(feature.geometry))
  );

  if (positions.length === 0) {
    return null;
  }

  const lons = positions.map((position) => Number(position[0]));
  const lats = positions.map((position) => Number(position[1]));
  return {
    minLon: Math.min(...lons),
    minLat: Math.min(...lats),
    maxLon: Math.max(...lons),
    maxLat: Math.max(...lats)
  };
}

function paddedBounds(bounds: Bounds, ratio = 0.08): LngLatBoundsLike {
  const lonPadding = Math.max((bounds.maxLon - bounds.minLon) * ratio, 0.015);
  const latPadding = Math.max((bounds.maxLat - bounds.minLat) * ratio, 0.015);
  return [
    [bounds.minLon - lonPadding, bounds.minLat - latPadding],
    [bounds.maxLon + lonPadding, bounds.maxLat + latPadding]
  ];
}

function boundsEnvelope(bounds: Bounds) {
  return {
    xmin: bounds.minLon,
    ymin: bounds.minLat,
    xmax: bounds.maxLon,
    ymax: bounds.maxLat,
    spatialReference: { wkid: 4326 }
  };
}

function pointIsInBounds(lon: number, lat: number, bounds: Bounds) {
  return lon >= bounds.minLon && lon <= bounds.maxLon && lat >= bounds.minLat && lat <= bounds.maxLat;
}

function escapeSqlLiteral(value: string) {
  return value.replaceAll("'", "''");
}

function escapeHtml(value: unknown) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatArcGisDate(value: unknown) {
  if (typeof value !== "number") {
    return "";
  }
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric"
  }).format(new Date(value));
}

function epaStatus(properties: GeoJsonProperties | null | undefined) {
  if (properties?.isimpaired === "Y") {
    return "Polluted";
  }
  if (properties?.isassessed === "Y") {
    return "Good";
  }
  return "Unassessed";
}

function permitStatus(properties: GeoJsonProperties | null | undefined) {
  const action = String(properties?.PERMITTING_ACTION ?? "");
  return action === "Active" ? "Active" : "Pending";
}

function propertyText(properties: GeoJsonProperties | null | undefined, key: string) {
  const value = properties?.[key];
  if (value === null || value === undefined) {
    return "";
  }
  return String(value).trim();
}

function propertyNumber(properties: GeoJsonProperties | null | undefined, key: string) {
  const value = properties?.[key];
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }

  const parsed = Number.parseFloat(String(value ?? "").replaceAll(",", ""));
  return Number.isFinite(parsed) ? parsed : 0;
}

function flagIsYes(value: unknown) {
  if (typeof value === "number") {
    return value > 0;
  }

  const text = String(value ?? "").trim().toLowerCase();
  return ["1", "y", "yes", "true"].includes(text);
}

function isCauseFlag(value: unknown) {
  const text = String(value ?? "").trim().toLowerCase();
  return text.length > 0 && !["0", "n", "no", "false", "not a cause"].includes(text);
}

function impairmentCauseLabels(properties: GeoJsonProperties | null | undefined) {
  const localCauses = propertyText(properties, "impairment_causes");
  if (localCauses) {
    return localCauses
      .split(";")
      .map((cause) => cause.trim())
      .filter(Boolean);
  }

  return ATTAINS_CAUSE_FIELDS
    .filter((field) => isCauseFlag(properties?.[field.key]))
    .map((field) => field.label);
}

function complianceHistory(properties: GeoJsonProperties | null | undefined) {
  return propertyText(properties, "CWP13qtrsComplHistory").replace(/\s/g, "");
}

function countComplianceViolations(history: string) {
  return [...history].filter((char) => char === "V" || char === "S").length;
}

function echoViolationCount(properties: GeoJsonProperties | null | undefined) {
  const reportedQuarters = propertyNumber(properties, "CWPQtrsWithNC");
  if (reportedQuarters > 0) {
    return reportedQuarters;
  }

  const historyCount = countComplianceViolations(complianceHistory(properties));
  if (historyCount > 0) {
    return historyCount;
  }

  return propertyNumber(properties, "EffExceeds");
}

function echoCurrentViolation(properties: GeoJsonProperties | null | undefined) {
  const status = propertyText(properties, "CWPViolStatus").toLowerCase();
  const cwpStatus = propertyText(properties, "CWPStatus").toLowerCase();
  return (
    flagIsYes(properties?.CurrVioFlag) ||
    status === "yes" ||
    (cwpStatus.length > 0 && !cwpStatus.includes("no violation"))
  );
}

function echoSignificantViolation(properties: GeoJsonProperties | null | undefined) {
  const status = `${propertyText(properties, "CWPStatus")} ${propertyText(properties, "CWPSNCStatus")}`.toLowerCase();
  return flagIsYes(properties?.CurrSvFlag) || status.includes("significant") || status.includes("snc");
}

function echoLatestViolationLabel(properties: GeoJsonProperties | null | undefined) {
  const currentStatus = propertyText(properties, "CWPStatus");
  const currentViolationStatus = propertyText(properties, "CWPViolStatus");
  const sncEvent = propertyText(properties, "CWPSNCEventDesc");
  const sncDate = propertyText(properties, "CWPSNCStatusDate");

  if (echoCurrentViolation(properties)) {
    if (sncEvent && sncDate) {
      return `${sncEvent} (${sncDate})`;
    }
    if (sncEvent) {
      return sncEvent;
    }
    if (currentStatus && !currentStatus.toLowerCase().includes("no violation")) {
      return currentStatus;
    }
    if (currentViolationStatus && currentViolationStatus.toLowerCase() !== "no") {
      return currentViolationStatus;
    }
    return "Current violation flagged by ECHO";
  }

  const history = complianceHistory(properties);
  for (let index = history.length - 1; index >= 0; index -= 1) {
    const marker = history[index];
    if (marker !== "V" && marker !== "S") {
      continue;
    }

    const quartersAgo = history.length - index - 1;
    const kind = marker === "S" ? "Significant noncompliance" : "Violation";
    if (quartersAgo === 0) {
      return `${kind} in the most recent ECHO quarter`;
    }
    if (quartersAgo === 1) {
      return `${kind} 1 quarter ago`;
    }
    return `${kind} ${quartersAgo} quarters ago`;
  }

  if (flagIsYes(properties?.VioLastYear)) {
    return "Violation in the last 4 quarters";
  }
  if (flagIsYes(properties?.ViolFlag)) {
    return "Violation within the last 3 years";
  }

  return "Violation history reported by ECHO";
}

function echoDetailUrl(properties: GeoJsonProperties | null | undefined) {
  const registryId = propertyText(properties, "RegistryID");
  if (registryId) {
    return `https://echo.epa.gov/detailed-facility-report?fid=${encodeURIComponent(registryId)}`;
  }

  const sourceId = propertyText(properties, "SourceID");
  return sourceId
    ? `https://echo.epa.gov/facilities/facility-search/results?search=permit&keyword=${encodeURIComponent(sourceId)}`
    : "";
}

function echoFeatureDisplayName(properties: GeoJsonProperties | null | undefined) {
  return propertyText(properties, "CWPName") || propertyText(properties, "PermitName") || "ECHO permit";
}

function pointCoordinates(feature: Feature) {
  if (feature.geometry?.type !== "Point") {
    return null;
  }

  const [lon, lat] = feature.geometry.coordinates;
  if (typeof lon !== "number" || typeof lat !== "number") {
    return null;
  }

  return [lon, lat] as [number, number];
}

function normalizeEchoFeature(feature: Feature): Feature {
  const properties = feature.properties ?? {};
  const violationCount = echoViolationCount(properties);
  const currentViolation = echoCurrentViolation(properties);
  const significantViolation = echoSignificantViolation(properties);
  const latestViolation = echoLatestViolationLabel(properties);
  const sourceId = propertyText(properties, "SourceID");

  return {
    ...feature,
    properties: {
      ...properties,
      echo_source_id: sourceId,
      echo_display_name: echoFeatureDisplayName(properties),
      echo_violation_count: violationCount,
      echo_current_violation: currentViolation,
      echo_significant_violation: significantViolation,
      echo_latest_violation: latestViolation,
      echo_detail_url: echoDetailUrl(properties),
      echo_status_label: currentViolation ? "Current violation" : "Recent violation"
    }
  };
}

function normalizeEchoCollection(collection: FeatureCollection): FeatureCollection {
  return {
    type: "FeatureCollection",
    features: collection.features
      .map(normalizeEchoFeature)
      .filter((feature) => pointCoordinates(feature) && propertyNumber(feature.properties, "echo_violation_count") > 0)
  };
}

function facilitiesToFeatureCollection(payload: unknown): FeatureCollection {
  const root = payload as {
    Results?: { Facilities?: Array<Record<string, unknown>> };
    Facilities?: Array<Record<string, unknown>>;
  };
  const facilities = root.Results?.Facilities ?? root.Facilities ?? [];

  return {
    type: "FeatureCollection",
    features: facilities.flatMap((facility): Feature[] => {
      const lon = Number.parseFloat(String(facility.FacLong ?? ""));
      const lat = Number.parseFloat(String(facility.FacLat ?? ""));
      if (!Number.isFinite(lon) || !Number.isFinite(lat)) {
        return [];
      }

      return [
        {
          type: "Feature",
          properties: facility as GeoJsonProperties,
          geometry: {
            type: "Point",
            coordinates: [lon, lat]
          }
        }
      ];
    })
  };
}

function echoResults(payload: unknown) {
  if (!payload || typeof payload !== "object") {
    return null;
  }

  const results = (payload as { Results?: unknown }).Results;
  return results && typeof results === "object" ? (results as Record<string, unknown>) : null;
}

function echoErrorMessage(payload: unknown) {
  const results = echoResults(payload);
  const error = results?.Error;
  if (!error || typeof error !== "object") {
    return "";
  }

  const message = (error as { ErrorMessage?: unknown }).ErrorMessage;
  return typeof message === "string" ? message : "";
}

function echoQueryId(payload: unknown) {
  const queryId = echoResults(payload)?.QueryID;
  return typeof queryId === "string" || typeof queryId === "number" ? String(queryId) : "";
}

function echoQueryRows(payload: unknown) {
  const queryRows = echoResults(payload)?.QueryRows;
  const parsed = Number.parseInt(String(queryRows ?? ""), 10);
  return Number.isFinite(parsed) ? parsed : 0;
}

function echoFacilityCollection(payload: unknown): FeatureCollection {
  const geoJson = toFeatureCollection(payload);
  if (geoJson.features.length > 0) {
    return geoJson;
  }
  return facilitiesToFeatureCollection(payload);
}

function setGeoJsonSource(map: MapLibreMap, id: string, data: FeatureCollection) {
  const existing = map.getSource(id) as GeoJSONSource | undefined;
  if (existing) {
    existing.setData(data);
    return;
  }
  map.addSource(id, {
    type: "geojson",
    data
  });
}

function ensureLayer(map: MapLibreMap, layer: maplibregl.LayerSpecification) {
  if (!map.getLayer(layer.id)) {
    map.addLayer(layer);
  }
}

function normalizeEpaFeature(feature: Feature): Feature {
  const properties = feature.properties ?? {};
  const causes = impairmentCauseLabels(properties);
  return {
    ...feature,
    properties: {
      ...properties,
      status_label: epaStatus(properties),
      impairment_causes: causes.join("; ")
    }
  };
}

function localImpairmentFallback(map: CountyMapRecord): FeatureCollection {
  return {
    type: "FeatureCollection",
    features: map.impairment.features.map((feature) => {
      const status = String(feature.properties.status ?? "Unknown");
      return {
        ...feature,
        properties: {
          ...feature.properties,
          assessmentunitname: feature.properties.waterbody ?? "Unnamed waterbody",
          overallstatus: status,
          isassessed: status === "Not Assessed" ? "N" : "Y",
          isimpaired: status.includes("Not Supporting") ? "Y" : "N",
          isthreatened: status === "Threatened" ? "Y" : "N",
          reportingcycle: "2026",
          status_label: status.includes("Not Supporting")
            ? "Polluted"
            : status === "Not Assessed"
              ? "Unassessed"
              : "Good",
          source_label: "Local 2026 303(d) fallback"
        }
      } as Feature;
    })
  };
}

async function fetchGeoJson(url: string, params: URLSearchParams) {
  const response = await fetch(`${url}?${params.toString()}`);
  if (!response.ok) {
    throw new Error(`Request failed with ${response.status}`);
  }
  return toFeatureCollection(await response.json());
}

async function loadCachedWeeklyLayer(slug: string, filename: string) {
  const response = await fetch(`/data/weekly/${slug}/${filename}`);
  if (!response.ok) {
    return null;
  }
  return toFeatureCollection(await response.json());
}

async function fetchPagedGeoJson(
  url: string,
  baseParams: URLSearchParams,
  pageSize = 1000,
  maxPages = 8
): Promise<FeatureCollection> {
  const features: Feature[] = [];

  for (let page = 0; page < maxPages; page += 1) {
    const params = new URLSearchParams(baseParams);
    params.set("resultOffset", String(page * pageSize));
    params.set("resultRecordCount", String(pageSize));

    const collection = await fetchGeoJson(url, params);
    features.push(...collection.features);

    if (collection.features.length < pageSize || !(collection as { exceededTransferLimit?: boolean }).exceededTransferLimit) {
      break;
    }
  }

  return {
    type: "FeatureCollection",
    features
  };
}

async function loadEpaImpairment(bounds: Bounds) {
  const params = new URLSearchParams({
    where: "state = 'TN'",
    outFields:
      [
        "assessmentunitname",
        "overallstatus",
        "isassessed",
        "isimpaired",
        "isthreatened",
        "on303dlist",
        "ircategory",
        "reportingcycle",
        "waterbodyreportlink",
        "organizationname",
        "state",
        ...ATTAINS_CAUSE_FIELDS.map((field) => field.key)
      ].join(","),
    returnGeometry: "true",
    geometry: JSON.stringify(boundsEnvelope(bounds)),
    geometryType: "esriGeometryEnvelope",
    inSR: "4326",
    outSR: "4326",
    spatialRel: "esriSpatialRelIntersects",
    f: "geojson"
  });

  const collection = await fetchPagedGeoJson(EPA_ATTAINS_LINES_URL, params, 10000, 2);
  return {
    type: "FeatureCollection",
    features: collection.features.map(normalizeEpaFeature)
  } satisfies FeatureCollection;
}

async function loadTdecPermits(countyName: string) {
  const county = escapeSqlLiteral(countyName);
  const params = new URLSearchParams({
    where:
      `COUNTY = '${county}' AND PERMITTING_ACTION IN (` +
      "'Active','Pending','Incomplete')",
    outFields:
      "PERMIT_NUMBER,PERMITTEE_NAME,PERMITTING_ACTION,PERMIT_TYPE,ISSUANCE_DATE,EFFECTIVE_DATE,EXPIRATION_DATE,TERMINATION_DATE,COUNTY,SITE_LOCATION,URL,LATITUDE,LONGITUDE",
    returnGeometry: "true",
    outSR: "4326",
    f: "geojson"
  });

  const collection = await fetchPagedGeoJson(TDEC_PERMITS_URL, params);
  return {
    type: "FeatureCollection",
    features: collection.features.map((feature) => {
      const properties = feature.properties ?? {};
      return {
        ...feature,
        properties: {
          ...properties,
          permit_status: permitStatus(properties)
        }
      };
    })
  } satisfies FeatureCollection;
}

async function loadEchoViolations(countyName: string) {
  const params = new URLSearchParams({
    output: "JSON",
    p_st: "TN",
    p_co: countyName,
    p_act: "Y",
    responseset: String(ECHO_RESPONSE_SET)
  });

  const queryResponse = await fetch(`${ECHO_CWA_SERVICES_URL}.get_facilities?${params.toString()}`, {
    headers: {
      Accept: "application/json"
    }
  });
  if (!queryResponse.ok) {
    throw new Error(`ECHO query request failed with ${queryResponse.status}`);
  }

  const queryPayload = await queryResponse.json();
  const queryError = echoErrorMessage(queryPayload);
  if (queryError) {
    throw new Error(`ECHO query failed: ${queryError}`);
  }

  const queryId = echoQueryId(queryPayload);
  if (!queryId) {
    return normalizeEchoCollection(echoFacilityCollection(queryPayload));
  }

  const pages = Math.max(1, Math.ceil(echoQueryRows(queryPayload) / ECHO_RESPONSE_SET));
  const features: Feature[] = [];

  for (let page = 1; page <= pages; page += 1) {
    const pageParams = new URLSearchParams({
      output: "JSON",
      qid: queryId,
      pageno: String(page),
      responseset: String(ECHO_RESPONSE_SET),
      qcolumns: ECHO_QUERY_COLUMNS
    });

    const pageResponse = await fetch(`${ECHO_CWA_SERVICES_URL}.get_qid?${pageParams.toString()}`, {
      headers: {
        Accept: "application/json"
      }
    });
    if (!pageResponse.ok) {
      throw new Error(`ECHO page request failed with ${pageResponse.status}`);
    }

    const pagePayload = await pageResponse.json();
    const pageError = echoErrorMessage(pagePayload);
    if (pageError) {
      throw new Error(`ECHO page request failed: ${pageError}`);
    }

    const pageFeatures = echoFacilityCollection(pagePayload).features;
    features.push(...pageFeatures);

    if (pageFeatures.length < ECHO_RESPONSE_SET) {
      break;
    }
  }

  return normalizeEchoCollection({
    type: "FeatureCollection",
    features
  });
}

function addCountyMapLayers(map: MapLibreMap) {
  ensureLayer(map, {
    id: "watershed-fill",
    type: "fill",
    source: "watersheds",
    paint: {
      "fill-color": "#6f8f5f",
      "fill-opacity": 0.34
    }
  });
  ensureLayer(map, {
    id: "watershed-line",
    type: "line",
    source: "watersheds",
    paint: {
      "line-color": "#3b6e63",
      "line-opacity": 0.88,
      "line-width": 2.2
    }
  });
  ensureLayer(map, {
    id: "county-fill",
    type: "fill",
    source: "county",
    paint: {
      "fill-color": "#ffffff",
      "fill-opacity": 0.06
    }
  });
  ensureLayer(map, {
    id: "watershed-hover-fill",
    type: "fill",
    source: "watersheds",
    filter: ["==", ["get", "huc8"], "__none__"],
    paint: {
      "fill-color": "#3b6e63",
      "fill-opacity": 0.3
    }
  });
  ensureLayer(map, {
    id: "watershed-hover-line",
    type: "line",
    source: "watersheds",
    filter: ["==", ["get", "huc8"], "__none__"],
    paint: {
      "line-color": "#2f3834",
      "line-opacity": 0.95,
      "line-width": 4.2
    }
  });
  ensureLayer(map, {
    id: "congressional-line",
    type: "line",
    source: "congressional",
    paint: {
      "line-color": "#547a76",
      "line-dasharray": [3, 2],
      "line-opacity": 0.86,
      "line-width": 2.1
    }
  });
  ensureLayer(map, {
    id: "senate-line",
    type: "line",
    source: "senate",
    paint: {
      "line-color": "#af8401",
      "line-dasharray": [2, 2],
      "line-opacity": 0.82,
      "line-width": 1.7
    }
  });
  ensureLayer(map, {
    id: "house-line",
    type: "line",
    source: "house",
    paint: {
      "line-color": "#8b742f",
      "line-dasharray": [1, 2],
      "line-opacity": 0.75,
      "line-width": 1.2
    }
  });
  ensureLayer(map, {
    id: "congressional-hit-fill",
    type: "fill",
    source: "congressional",
    paint: {
      "fill-color": "#547a76",
      "fill-opacity": 0.01
    }
  });
  ensureLayer(map, {
    id: "senate-hit-fill",
    type: "fill",
    source: "senate",
    paint: {
      "fill-color": "#af8401",
      "fill-opacity": 0.01
    }
  });
  ensureLayer(map, {
    id: "house-hit-fill",
    type: "fill",
    source: "house",
    paint: {
      "fill-color": "#8b742f",
      "fill-opacity": 0.01
    }
  });
  ensureLayer(map, {
    id: "congressional-hover-line",
    type: "line",
    source: "congressional",
    filter: ["==", ["get", "district"], "__none__"],
    paint: {
      "line-color": "#2f3834",
      "line-opacity": 0.98,
      "line-width": 4.6
    }
  });
  ensureLayer(map, {
    id: "senate-hover-line",
    type: "line",
    source: "senate",
    filter: ["==", ["get", "district"], "__none__"],
    paint: {
      "line-color": "#9f4f2a",
      "line-opacity": 0.98,
      "line-width": 4.4
    }
  });
  ensureLayer(map, {
    id: "house-hover-line",
    type: "line",
    source: "house",
    filter: ["==", ["get", "district"], "__none__"],
    paint: {
      "line-color": "#6f5c24",
      "line-opacity": 0.98,
      "line-width": 4.2
    }
  });
  ensureLayer(map, {
    id: "epa-impairment-line",
    type: "line",
    source: "epa-impairment",
    paint: {
      "line-color": [
        "case",
        ["==", ["get", "isimpaired"], "Y"],
        "#c6283e",
        ["==", ["get", "isassessed"], "Y"],
        "#2e7d4f",
        "#7554a1"
      ],
      "line-opacity": 0.92,
      "line-width": [
        "case",
        ["==", ["get", "isimpaired"], "Y"],
        4.1,
        3
      ]
    }
  });
  ensureLayer(map, {
    id: "county-outline",
    type: "line",
    source: "county",
    paint: {
      "line-color": "#2f3834",
      "line-opacity": 0.95,
      "line-width": 2.3
    }
  });
  ensureLayer(map, {
    id: "permit-active",
    type: "circle",
    source: "permits",
    filter: ["==", ["get", "permit_status"], "Active"],
    paint: {
      "circle-color": "#3b6e63",
      "circle-radius": ["interpolate", ["linear"], ["zoom"], 7, 4.5, 12, 7.5],
      "circle-stroke-color": "#ffffff",
      "circle-stroke-width": 1.4,
      "circle-opacity": 0.9
    }
  });
  ensureLayer(map, {
    id: "permit-pending",
    type: "circle",
    source: "permits",
    filter: ["==", ["get", "permit_status"], "Pending"],
    paint: {
      "circle-color": "#f5bf54",
      "circle-radius": ["interpolate", ["linear"], ["zoom"], 7, 5, 12, 8],
      "circle-stroke-color": "#ffffff",
      "circle-stroke-width": 1.6,
      "circle-opacity": 0.94
    }
  });
  ensureLayer(map, {
    id: "echo-recent-violation",
    type: "circle",
    source: "echo-violations",
    filter: ["==", ["get", "echo_current_violation"], false],
    paint: {
      "circle-color": "#6b4bb1",
      "circle-radius": ["interpolate", ["linear"], ["zoom"], 7, 6.5, 12, 11],
      "circle-stroke-color": "#ffffff",
      "circle-stroke-width": 2,
      "circle-opacity": 0.9
    }
  });
  ensureLayer(map, {
    id: "echo-current-violation",
    type: "circle",
    source: "echo-violations",
    filter: ["==", ["get", "echo_current_violation"], true],
    paint: {
      "circle-color": [
        "case",
        ["==", ["get", "echo_significant_violation"], true],
        "#b91c1c",
        "#df5b2f"
      ],
      "circle-radius": ["interpolate", ["linear"], ["zoom"], 7, 7, 12, 12.5],
      "circle-stroke-color": "#ffffff",
      "circle-stroke-width": 2.4,
      "circle-opacity": 0.95
    }
  });
}

function echoPopupHtml(properties: GeoJsonProperties | null | undefined) {
  const detailUrl = propertyText(properties, "echo_detail_url");
  const status = propertyText(properties, "CWPStatus") || propertyText(properties, "CWPViolStatus");
  const permitId = propertyText(properties, "echo_source_id") || propertyText(properties, "SourceID");
  const count = propertyNumber(properties, "echo_violation_count");
  const sourceLink = detailUrl.startsWith("http")
    ? `<a href="${escapeHtml(detailUrl)}" target="_blank" rel="noreferrer">EPA ECHO detailed report</a>`
    : "";

  return `
    <div class="space-y-1 text-sm">
      <p class="font-semibold">${escapeHtml(permitId || "ECHO CWA permit")}</p>
      <p>${escapeHtml(propertyText(properties, "echo_display_name"))}</p>
      <p>${escapeHtml(count)} noncompliance quarter${count === 1 ? "" : "s"} in the last 12-quarter ECHO window</p>
      <p>Most recent: ${escapeHtml(propertyText(properties, "echo_latest_violation"))}</p>
      ${status ? `<p>Current status: ${escapeHtml(status)}</p>` : ""}
      ${sourceLink}
    </div>
  `;
}

function districtInfo(layerId: string) {
  if (layerId.startsWith("house")) {
    return { chamber: "House", prefix: "H" };
  }
  if (layerId.startsWith("senate")) {
    return { chamber: "Senate", prefix: "S" };
  }
  if (layerId.startsWith("congressional")) {
    return { chamber: "Congressional", prefix: "" };
  }
  return null;
}

function districtPopupHtml(layerId: string, properties: GeoJsonProperties | null | undefined) {
  const district = propertyText(properties, "district");
  const info = districtInfo(layerId);

  if (!info || !district) {
    return "";
  }

  if (info.prefix === "") {
    return `
      <div class="space-y-1 text-sm">
        <p class="font-semibold">Congressional District ${escapeHtml(district)}</p>
      </div>
    `;
  }

  const code = `${info.prefix}${district}`;
  const legislator = TENNESSEE_LEGISLATORS[code];
  const party = legislator?.party ? ` (${legislator.party})` : "";

  return `
    <div class="space-y-1 text-sm">
      <p class="font-semibold">${escapeHtml(info.chamber)} District ${escapeHtml(district)}</p>
      ${
        legislator
          ? `<p>${escapeHtml(legislator.name)}${escapeHtml(party)}</p>`
          : `<p>Current member not found in the local legislator lookup.</p>`
      }
      <a href="${escapeHtml(tennesseeLegislatorUrl(code))}" target="_blank" rel="noreferrer">Tennessee General Assembly profile</a>
    </div>
  `;
}

function districtFeatureCode(feature: maplibregl.MapGeoJSONFeature) {
  const district = propertyText(feature.properties, "district");
  const info = districtInfo(feature.layer.id);

  if (!info || !district) {
    return "";
  }

  return info.prefix ? `${info.prefix}${district}` : `C${district}`;
}

function uniqueDistrictFeatures(features: maplibregl.MapGeoJSONFeature[]) {
  const byCode = new Map<string, maplibregl.MapGeoJSONFeature>();

  features.forEach((feature) => {
    if (!DISTRICT_HOVER_LAYERS.includes(feature.layer.id)) {
      return;
    }

    const code = districtFeatureCode(feature);
    if (code && !byCode.has(code)) {
      byCode.set(code, feature);
    }
  });

  const sortOrder = new Map([
    ["H", 0],
    ["S", 1],
    ["C", 2]
  ]);

  return [...byCode.entries()]
    .sort(([left], [right]) => {
      const chamberDiff = (sortOrder.get(left[0]) ?? 9) - (sortOrder.get(right[0]) ?? 9);
      return chamberDiff || Number.parseInt(left.slice(1), 10) - Number.parseInt(right.slice(1), 10);
    })
    .map(([, feature]) => feature);
}

function districtStackKey(features: maplibregl.MapGeoJSONFeature[]) {
  return uniqueDistrictFeatures(features)
    .map(districtFeatureCode)
    .join("|");
}

function districtStackPopupHtml(features: maplibregl.MapGeoJSONFeature[]) {
  const districtFeatures = uniqueDistrictFeatures(features);

  if (districtFeatures.length === 0) {
    return "";
  }

  const rows = districtFeatures.map((feature) => {
    const district = propertyText(feature.properties, "district");
    const info = districtInfo(feature.layer.id);

    if (!info || !district) {
      return "";
    }

    if (info.prefix === "") {
      return `<p><span class="font-semibold">Congressional District ${escapeHtml(district)}</span></p>`;
    }

    const code = `${info.prefix}${district}`;
    const legislator = TENNESSEE_LEGISLATORS[code];
    const party = legislator?.party ? ` (${legislator.party})` : "";
    const label = legislator ? `${legislator.name}${party}` : "Member not found";

    return `
      <p>
        <span class="font-semibold">${escapeHtml(info.chamber)} District ${escapeHtml(district)}</span><br />
        <a href="${escapeHtml(tennesseeLegislatorUrl(code))}" target="_blank" rel="noreferrer">${escapeHtml(label)}</a>
      </p>
    `;
  });

  return `
    <div class="space-y-2 text-sm">
      <p class="font-semibold">Districts at this point</p>
      ${rows.join("")}
    </div>
  `;
}

function watershedPopupHtml(properties: GeoJsonProperties | null | undefined) {
  const name = propertyText(properties, "name") || "Watershed";
  const huc8 = propertyText(properties, "huc8");
  const area = propertyNumber(properties, "areasqkm");

  return `
    <div class="space-y-1 text-sm">
      <p class="font-semibold">${escapeHtml(name)}</p>
      ${huc8 ? `<p>HUC8 ${escapeHtml(huc8)}</p>` : ""}
      ${area > 0 ? `<p>${escapeHtml(area.toLocaleString(undefined, { maximumFractionDigits: 1 }))} sq km</p>` : ""}
    </div>
  `;
}

function hoverPopupHtml(feature: maplibregl.MapGeoJSONFeature) {
  if (feature.layer.id.startsWith("watershed")) {
    return watershedPopupHtml(feature.properties);
  }
  if (
    feature.layer.id.startsWith("house") ||
    feature.layer.id.startsWith("senate") ||
    feature.layer.id.startsWith("congressional")
  ) {
    return districtPopupHtml(feature.layer.id, feature.properties);
  }
  return "";
}

function popupHtml(feature: maplibregl.MapGeoJSONFeature) {
  const properties = feature.properties ?? {};

  if (feature.layer.id.startsWith("echo-")) {
    return echoPopupHtml(properties);
  }

  if (feature.layer.id.startsWith("permit")) {
    const effective = formatArcGisDate(properties.EFFECTIVE_DATE);
    const expires = formatArcGisDate(properties.EXPIRATION_DATE);
    const url = String(properties.URL ?? "");
    const link = url.startsWith("http")
      ? `<a href="${escapeHtml(url)}" target="_blank" rel="noreferrer">Permit record</a>`
      : "";

    return `
      <div class="space-y-1 text-sm">
        <p class="font-semibold">${escapeHtml(properties.PERMIT_NUMBER ?? "TDEC permit")}</p>
        <p>${escapeHtml(properties.PERMITTEE_NAME ?? "")}</p>
        <p>${escapeHtml(properties.permit_status)} · ${escapeHtml(properties.PERMIT_TYPE ?? "")}</p>
        <p>${escapeHtml(properties.SITE_LOCATION ?? "")}</p>
        ${effective ? `<p>Effective ${escapeHtml(effective)}</p>` : ""}
        ${expires ? `<p>Expires ${escapeHtml(expires)}</p>` : ""}
        ${link}
      </div>
    `;
  }

  if (
    feature.layer.id.startsWith("watershed") ||
    feature.layer.id.startsWith("house") ||
    feature.layer.id.startsWith("senate") ||
    feature.layer.id.startsWith("congressional")
  ) {
    return hoverPopupHtml(feature);
  }

  const causes = impairmentCauseLabels(properties);
  return `
    <div class="space-y-1 text-sm">
      <p class="font-semibold">${escapeHtml(properties.assessmentunitname ?? "Assessment unit")}</p>
      <p>${escapeHtml(properties.status_label ?? properties.overallstatus ?? "")}</p>
      ${
        causes.length > 0
          ? `<p>Impairment cause${causes.length === 1 ? "" : "s"}: ${escapeHtml(causes.join(", "))}</p>`
          : ""
      }
      <p>Cycle ${escapeHtml(properties.reportingcycle ?? "")} · IR ${escapeHtml(properties.ircategory ?? "n/a")}</p>
      ${
        String(properties.waterbodyreportlink ?? "").startsWith("http")
          ? `<a href="${escapeHtml(properties.waterbodyreportlink)}" target="_blank" rel="noreferrer">EPA waterbody report</a>`
          : ""
      }
    </div>
  `;
}

function setLayerFilter(map: MapLibreMap, layerId: string, filter: MapFilter) {
  if (map.getLayer(layerId)) {
    map.setFilter(layerId, filter);
  }
}

function clearHoverHighlight(map: MapLibreMap) {
  setLayerFilter(map, "watershed-hover-fill", ["==", ["get", "huc8"], "__none__"]);
  setLayerFilter(map, "watershed-hover-line", ["==", ["get", "huc8"], "__none__"]);
  setLayerFilter(map, "house-hover-line", ["==", ["get", "district"], "__none__"]);
  setLayerFilter(map, "senate-hover-line", ["==", ["get", "district"], "__none__"]);
  setLayerFilter(map, "congressional-hover-line", ["==", ["get", "district"], "__none__"]);
}

function hoverFeatureKey(feature: maplibregl.MapGeoJSONFeature) {
  if (feature.layer.id.startsWith("watershed")) {
    const huc8 = propertyText(feature.properties, "huc8");
    return huc8 ? `watershed:${huc8}` : "";
  }

  const district = propertyText(feature.properties, "district");
  if (!district) {
    return "";
  }

  if (feature.layer.id.startsWith("house")) {
    return `house:${district}`;
  }
  if (feature.layer.id.startsWith("senate")) {
    return `senate:${district}`;
  }
  if (feature.layer.id.startsWith("congressional")) {
    return `congressional:${district}`;
  }

  return "";
}

function setHoverHighlight(map: MapLibreMap, feature: maplibregl.MapGeoJSONFeature) {
  clearHoverHighlight(map);

  if (feature.layer.id.startsWith("watershed")) {
    const huc8 = propertyText(feature.properties, "huc8");
    if (huc8) {
      setLayerFilter(map, "watershed-hover-fill", ["==", ["get", "huc8"], huc8]);
      setLayerFilter(map, "watershed-hover-line", ["==", ["get", "huc8"], huc8]);
    }
    return;
  }

  const district = propertyText(feature.properties, "district");
  if (!district) {
    return;
  }

  if (feature.layer.id.startsWith("house")) {
    setLayerFilter(map, "house-hover-line", ["==", ["get", "district"], district]);
  } else if (feature.layer.id.startsWith("senate")) {
    setLayerFilter(map, "senate-hover-line", ["==", ["get", "district"], district]);
  } else if (feature.layer.id.startsWith("congressional")) {
    setLayerFilter(map, "congressional-hover-line", ["==", ["get", "district"], district]);
  }
}

function setDistrictHoverHighlights(map: MapLibreMap, features: maplibregl.MapGeoJSONFeature[]) {
  clearHoverHighlight(map);

  uniqueDistrictFeatures(features).forEach((feature) => {
    const district = propertyText(feature.properties, "district");
    if (!district) {
      return;
    }

    if (feature.layer.id.startsWith("house")) {
      setLayerFilter(map, "house-hover-line", ["==", ["get", "district"], district]);
    } else if (feature.layer.id.startsWith("senate")) {
      setLayerFilter(map, "senate-hover-line", ["==", ["get", "district"], district]);
    } else if (feature.layer.id.startsWith("congressional")) {
      setLayerFilter(map, "congressional-hover-line", ["==", ["get", "district"], district]);
    }
  });
}

function LayerToggle({
  checked,
  label,
  onChange
}: {
  checked: boolean;
  label: string;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="flex cursor-pointer items-center justify-between gap-4 rounded-lg border border-ink/10 bg-white px-3 py-2 text-sm">
      <span className="font-medium text-ink">{label}</span>
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="h-4 w-4 accent-river"
      />
    </label>
  );
}

function CountyDetailMapView({ map }: { map: CountyMapRecord }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const popupRef = useRef<maplibregl.Popup | null>(null);
  const hoverPopupRef = useRef<maplibregl.Popup | null>(null);
  const hoveredFeatureKeyRef = useRef("");
  const markerRef = useRef<maplibregl.Marker | null>(null);

  const [mapReady, setMapReady] = useState(false);
  const [epaImpairment, setEpaImpairment] = useState<FeatureCollection>(EMPTY_COLLECTION);
  const [permits, setPermits] = useState<FeatureCollection>(EMPTY_COLLECTION);
  const [echoViolations, setEchoViolations] = useState<FeatureCollection>(EMPTY_COLLECTION);
  const [epaStatusLabel, setEpaStatusLabel] = useState("Loading EPA status...");
  const [permitStatusLabel, setPermitStatusLabel] = useState("Loading TDEC permits...");
  const [echoStatusLabel, setEchoStatusLabel] = useState("Loading EPA ECHO violations...");
  const [addressQuery, setAddressQuery] = useState("");
  const [addressStatus, setAddressStatus] = useState("");
  const [addressResults, setAddressResults] = useState<AddressCandidate[]>([]);
  const [visibleLayers, setVisibleLayers] = useState<Record<LayerKey, boolean>>({
    watershed: false,
    districts: false,
    impaired: true,
    permits: false,
    echo: false
  });

  const countyBounds = useMemo(() => collectionBounds([map.county as FeatureCollection]), [map]);
  const epaStats = useMemo(() => {
    const features = epaImpairment.features;
    return {
      polluted: features.filter((feature) => feature.properties?.isimpaired === "Y").length,
      good: features.filter(
        (feature) => feature.properties?.isassessed === "Y" && feature.properties?.isimpaired !== "Y"
      ).length,
      unassessed: features.filter((feature) => feature.properties?.isassessed !== "Y").length
    };
  }, [epaImpairment]);

  const permitStats = useMemo(() => {
    const active = permits.features.filter((feature) => feature.properties?.permit_status === "Active").length;
    const pending = permits.features.filter((feature) => feature.properties?.permit_status === "Pending").length;
    return { active, pending };
  }, [permits]);

  const echoStats = useMemo(() => {
    const current = echoViolations.features.filter((feature) => feature.properties?.echo_current_violation === true).length;
    return {
      current,
      recent: echoViolations.features.length - current
    };
  }, [echoViolations]);

  const echoViolationRecords = useMemo(() => {
    return [...echoViolations.features].sort((a, b) => {
      const aCurrent = a.properties?.echo_current_violation === true ? 1 : 0;
      const bCurrent = b.properties?.echo_current_violation === true ? 1 : 0;
      if (aCurrent !== bCurrent) {
        return bCurrent - aCurrent;
      }

      const countDiff =
        propertyNumber(b.properties, "echo_violation_count") - propertyNumber(a.properties, "echo_violation_count");
      if (countDiff !== 0) {
        return countDiff;
      }

      return propertyText(a.properties, "echo_display_name").localeCompare(
        propertyText(b.properties, "echo_display_name")
      );
    });
  }, [echoViolations]);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) {
      return;
    }

    const mapInstance = new maplibregl.Map({
      container: containerRef.current,
      style: MAP_STYLE,
      center: [-86.4, 35.85],
      zoom: 6.2,
      attributionControl: false
    });

    mapInstance.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    mapInstance.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-right");
    mapRef.current = mapInstance;

    mapInstance.on("load", () => setMapReady(true));

    return () => {
      popupRef.current?.remove();
      hoverPopupRef.current?.remove();
      markerRef.current?.remove();
      mapInstance.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!countyBounds) {
      return;
    }

    let cancelled = false;
    const activeCountyBounds = countyBounds;

    async function loadRemoteLayers() {
      setEpaStatusLabel("Loading EPA status...");
      setPermitStatusLabel("Loading TDEC permits...");
      setEchoStatusLabel("Loading EPA ECHO violations...");

      try {
        const epaCollection = await loadEpaImpairment(activeCountyBounds);
        if (!cancelled) {
          setEpaImpairment(epaCollection);
          setEpaStatusLabel(`${epaCollection.features.length.toLocaleString()} EPA assessment segments`);
        }
      } catch {
        if (!cancelled) {
          const fallback = localImpairmentFallback(map);
          setEpaImpairment(fallback);
          setEpaStatusLabel("EPA service unavailable; showing local 2026 303(d) fallback");
        }
      }

      try {
        const cachedPermits = await loadCachedWeeklyLayer(map.slug, "tdec-permits.geojson");
        const permitCollection = cachedPermits ?? (await loadTdecPermits(map.name));
        if (!cancelled) {
          setPermits(permitCollection);
          setPermitStatusLabel(
            `${permitCollection.features.length.toLocaleString()} active or pending permits` +
              (cachedPermits ? " from weekly cache" : " from live TDEC service")
          );
        }
      } catch {
        if (!cancelled) {
          setPermits(EMPTY_COLLECTION);
          setPermitStatusLabel("TDEC permit layer unavailable");
        }
      }

      try {
        const cachedEchoViolations = await loadCachedWeeklyLayer(map.slug, "echo-violations.geojson");
        const echoCollection = cachedEchoViolations ?? (await loadEchoViolations(map.name));
        if (!cancelled) {
          setEchoViolations(echoCollection);
          setEchoStatusLabel(
            echoCollection.features.length === 0
              ? `No active ECHO CWA permits with recent noncompliance returned${
                  cachedEchoViolations ? " from weekly cache" : " from live ECHO service"
                }`
              : `${echoCollection.features.length.toLocaleString()} ECHO CWA permits with recent noncompliance` +
                  (cachedEchoViolations ? " from weekly cache" : " from live ECHO service")
          );
        }
      } catch {
        if (!cancelled) {
          setEchoViolations(EMPTY_COLLECTION);
          setEchoStatusLabel("EPA ECHO violation layer unavailable");
        }
      }
    }

    void loadRemoteLayers();
    return () => {
      cancelled = true;
    };
  }, [countyBounds, map]);

  useEffect(() => {
    const mapInstance = mapRef.current;
    if (!mapReady || !mapInstance || !countyBounds) {
      return;
    }

    setGeoJsonSource(mapInstance, "watersheds", map.watersheds as FeatureCollection);
    setGeoJsonSource(mapInstance, "county", map.county as FeatureCollection);
    setGeoJsonSource(mapInstance, "senate", map.districts.senate as FeatureCollection);
    setGeoJsonSource(mapInstance, "house", map.districts.house as FeatureCollection);
    setGeoJsonSource(mapInstance, "congressional", map.districts.congressional as FeatureCollection);
    setGeoJsonSource(mapInstance, "epa-impairment", epaImpairment);
    setGeoJsonSource(mapInstance, "permits", permits);
    setGeoJsonSource(mapInstance, "echo-violations", echoViolations);
    addCountyMapLayers(mapInstance);

    mapInstance.fitBounds(paddedBounds(countyBounds), {
      padding: 44,
      duration: 0
    });
  }, [countyBounds, echoViolations, epaImpairment, map, mapReady, permits]);

  useEffect(() => {
    const mapInstance = mapRef.current;
    if (!mapReady || !mapInstance) {
      return;
    }

    Object.entries(LAYER_GROUPS).forEach(([key, layerIds]) => {
      layerIds.forEach((layerId) => {
        if (mapInstance.getLayer(layerId)) {
          mapInstance.setLayoutProperty(
            layerId,
            "visibility",
            visibleLayers[key as LayerKey] ? "visible" : "none"
          );
        }
      });
    });
  }, [mapReady, visibleLayers, echoViolations, epaImpairment, permits]);

  useEffect(() => {
    const mapInstance = mapRef.current;
    if (!mapReady || !mapInstance) {
      return;
    }

    const clearHover = () => {
      clearHoverHighlight(mapInstance);
      hoverPopupRef.current?.remove();
      hoverPopupRef.current = null;
      hoveredFeatureKeyRef.current = "";
      mapInstance.getCanvas().style.cursor = "";
    };

    const handleClick = (event: maplibregl.MapMouseEvent) => {
      const layers = INTERACTIVE_LAYERS.filter((layerId) => mapInstance.getLayer(layerId));
      const features = mapInstance.queryRenderedFeatures(event.point, { layers });
      const districtFeatures = uniqueDistrictFeatures(features);
      const feature = features[0];

      if (!feature) {
        popupRef.current?.remove();
        return;
      }

      popupRef.current?.remove();
      hoverPopupRef.current?.remove();

      if (districtFeatures.length > 0) {
        setDistrictHoverHighlights(mapInstance, districtFeatures);
        popupRef.current = new maplibregl.Popup({ maxWidth: "340px" })
          .setLngLat(event.lngLat)
          .setHTML(districtStackPopupHtml(districtFeatures))
          .addTo(mapInstance);
        return;
      }

      popupRef.current = new maplibregl.Popup({ maxWidth: "320px" })
        .setLngLat(event.lngLat)
        .setHTML(popupHtml(feature))
        .addTo(mapInstance);
    };

    const handleMove = (event: maplibregl.MapMouseEvent) => {
      const hoverLayers = HOVER_LAYERS.filter((layerId) => mapInstance.getLayer(layerId));
      const hoverFeatures = mapInstance.queryRenderedFeatures(event.point, { layers: hoverLayers });
      const districtFeatures = uniqueDistrictFeatures(hoverFeatures);

      if (districtFeatures.length > 0) {
        const key = `districts:${districtStackKey(districtFeatures)}`;
        const html = districtStackPopupHtml(districtFeatures);

        if (key !== hoveredFeatureKeyRef.current) {
          setDistrictHoverHighlights(mapInstance, districtFeatures);
          hoveredFeatureKeyRef.current = key;
        }

        if (html) {
          if (!hoverPopupRef.current) {
            hoverPopupRef.current = new maplibregl.Popup({
              closeButton: false,
              closeOnClick: false,
              maxWidth: "340px",
              offset: 12
            });
          }

          hoverPopupRef.current
            .setLngLat(event.lngLat)
            .setHTML(html)
            .addTo(mapInstance);
        }

        mapInstance.getCanvas().style.cursor = "pointer";
        return;
      }

      const hoverFeature = hoverFeatures.find((feature) => feature.layer.id.startsWith("watershed"));

      if (hoverFeature) {
        const key = hoverFeatureKey(hoverFeature);
        const html = hoverPopupHtml(hoverFeature);

        if (key && key !== hoveredFeatureKeyRef.current) {
          setHoverHighlight(mapInstance, hoverFeature);
          hoveredFeatureKeyRef.current = key;
        }

        if (html) {
          if (!hoverPopupRef.current) {
            hoverPopupRef.current = new maplibregl.Popup({
              closeButton: false,
              closeOnClick: false,
              maxWidth: "300px",
              offset: 12
            });
          }

          hoverPopupRef.current
            .setLngLat(event.lngLat)
            .setHTML(html)
            .addTo(mapInstance);
        }

        mapInstance.getCanvas().style.cursor = "pointer";
        return;
      }

      clearHover();

      const layers = INTERACTIVE_LAYERS.filter((layerId) => mapInstance.getLayer(layerId));
      const features = mapInstance.queryRenderedFeatures(event.point, { layers });
      mapInstance.getCanvas().style.cursor = features.length > 0 ? "pointer" : "";
    };

    mapInstance.on("click", handleClick);
    mapInstance.on("mousemove", handleMove);
    mapInstance.getCanvas().addEventListener("mouseleave", clearHover);
    return () => {
      mapInstance.off("click", handleClick);
      mapInstance.off("mousemove", handleMove);
      mapInstance.getCanvas().removeEventListener("mouseleave", clearHover);
    };
  }, [mapReady]);

  async function handleAddressSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const query = addressQuery.trim();
    if (!query || !countyBounds) {
      return;
    }

    setAddressStatus("Searching...");
    setAddressResults([]);

    try {
      const searchText = /\b(TN|Tennessee)\b/i.test(query)
        ? query
        : `${query}, ${map.name} County, TN`;
      const params = new URLSearchParams({
        SingleLine: searchText,
        outFields: "Match_addr,Score,Addr_type,Subregion,City,Postal",
        maxLocations: "6",
        outSR: "4326",
        f: "json"
      });

      const response = await fetch(`${TNMAP_LOCATOR_URL}?${params.toString()}`);
      if (!response.ok) {
        throw new Error(`Locator request failed with ${response.status}`);
      }
      const payload = (await response.json()) as GeocodeResponse;
      const candidates = (payload.candidates ?? []).filter((candidate) =>
        pointIsInBounds(candidate.location.x, candidate.location.y, countyBounds)
      );

      setAddressResults(candidates);
      if (candidates.length === 0) {
        setAddressStatus("No matches inside this county.");
        return;
      }

      setAddressStatus(`${candidates.length} match${candidates.length === 1 ? "" : "es"}`);
      zoomToAddress(candidates[0]);
    } catch {
      setAddressStatus("Address search unavailable.");
    }
  }

  function zoomToAddress(candidate: AddressCandidate) {
    const mapInstance = mapRef.current;
    if (!mapInstance) {
      return;
    }

    markerRef.current?.remove();
    markerRef.current = new maplibregl.Marker({ color: "#2f3834" })
      .setLngLat([candidate.location.x, candidate.location.y])
      .addTo(mapInstance);

    mapInstance.flyTo({
      center: [candidate.location.x, candidate.location.y],
      zoom: Math.max(mapInstance.getZoom(), 12.5),
      essential: true
    });
  }

  function zoomToEchoFeature(feature: Feature) {
    const mapInstance = mapRef.current;
    const coordinates = pointCoordinates(feature);
    if (!mapInstance || !coordinates) {
      return;
    }

    popupRef.current?.remove();
    popupRef.current = new maplibregl.Popup({ maxWidth: "320px" })
      .setLngLat(coordinates)
      .setHTML(echoPopupHtml(feature.properties))
      .addTo(mapInstance);

    mapInstance.flyTo({
      center: coordinates,
      zoom: Math.max(mapInstance.getZoom(), 12.5),
      essential: true
    });
  }

  return (
    <section id="county-map" className="card scroll-mt-6 overflow-hidden">
      <div className="border-b border-ink/10 p-6">
        <p className="text-xs uppercase tracking-normal text-river">County map</p>
        <h2 className="mt-2 text-2xl font-semibold">{map.name} County interactive map</h2>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-ink/75">
          Address search, EPA assessment status, legislative districts, TDEC permit records, EPA ECHO compliance signals, and HUC8 watershed areas are now layered on an interactive map.
        </p>
      </div>

      <div className="grid gap-6 p-6 lg:grid-cols-[1.45fr_0.75fr]">
        <div className="space-y-4">
          <form onSubmit={handleAddressSearch} className="rounded-lg border border-ink/10 bg-white/90 p-5">
            <label htmlFor={`address-search-${map.slug}`} className="text-xs uppercase tracking-normal text-river">
              Address search
            </label>
            <div className="mt-4 flex gap-2">
              <input
                id={`address-search-${map.slug}`}
                type="search"
                value={addressQuery}
                onChange={(event) => setAddressQuery(event.target.value)}
                placeholder={`Search ${map.name} County`}
                className="min-w-0 flex-1 rounded-lg border border-ink/15 bg-sand px-3 py-2 text-sm text-ink outline-none ring-0"
              />
              <button
                type="submit"
                className="rounded-lg bg-river px-4 py-2 text-sm font-medium text-white transition hover:bg-ink"
              >
                Search
              </button>
            </div>
            {addressStatus ? <p className="mt-3 text-sm text-ink/65">{addressStatus}</p> : null}
            {addressResults.length > 0 ? (
              <ul className="mt-3 space-y-2">
                {addressResults.map((candidate) => (
                  <li key={`${candidate.address}-${candidate.score}`}>
                    <button
                      type="button"
                      onClick={() => zoomToAddress(candidate)}
                      className="w-full rounded-lg border border-ink/10 bg-sand px-3 py-2 text-left text-sm text-ink transition hover:border-gold/45"
                    >
                      <span className="block font-medium">{candidate.address}</span>
                      <span className="text-xs text-ink/55">Score {candidate.score.toFixed(1)}</span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : null}
          </form>

          <div className="overflow-hidden rounded-lg border border-ink/10 bg-mist">
            <div ref={containerRef} className="h-[560px] min-h-[420px] w-full" />
          </div>
        </div>

        <aside className="space-y-4">

          <div className="rounded-lg border border-ink/10 bg-white/90 p-5">
            <p className="text-xs uppercase tracking-normal text-river">Layers</p>
            <div className="mt-4 space-y-2">
              <LayerToggle
                checked={visibleLayers.impaired}
                label="EPA impaired status"
                onChange={(checked) => setVisibleLayers((current) => ({ ...current, impaired: checked }))}
              />
              <LayerToggle
                checked={visibleLayers.districts}
                label="Legislative districts"
                onChange={(checked) => setVisibleLayers((current) => ({ ...current, districts: checked }))}
              />
              <LayerToggle
                checked={visibleLayers.permits}
                label="TDEC permits"
                onChange={(checked) => setVisibleLayers((current) => ({ ...current, permits: checked }))}
              />
              <LayerToggle
                checked={visibleLayers.echo}
                label="ECHO violations"
                onChange={(checked) => setVisibleLayers((current) => ({ ...current, echo: checked }))}
              />
              <LayerToggle
                checked={visibleLayers.watershed}
                label="Watershed area"
                onChange={(checked) => setVisibleLayers((current) => ({ ...current, watershed: checked }))}
              />
            </div>
          </div>

          {echoViolationRecords.length > 0 ? (
            <div className="rounded-lg border border-ink/10 bg-white/90 p-5">
              <p className="text-xs uppercase tracking-normal text-river">ECHO permit violations</p>
              <div className="mt-4 max-h-72 space-y-2 overflow-auto pr-1">
                {echoViolationRecords.slice(0, 8).map((feature, index) => {
                  const properties = feature.properties;
                  const permitId = propertyText(properties, "echo_source_id") || propertyText(properties, "SourceID");
                  const count = propertyNumber(properties, "echo_violation_count");

                  return (
                    <button
                      type="button"
                      key={`${permitId}-${propertyText(properties, "RegistryID")}-${index}`}
                      onClick={() => zoomToEchoFeature(feature)}
                      className="w-full rounded-lg border border-ink/10 bg-sand px-3 py-2 text-left text-sm text-ink transition hover:border-gold/45"
                    >
                      <span className="block truncate font-medium">
                        {permitId || propertyText(properties, "echo_display_name")}
                      </span>
                      <span className="mt-1 block text-xs leading-5 text-ink/65">
                        {count} NC quarter{count === 1 ? "" : "s"} - {propertyText(properties, "echo_latest_violation")}
                      </span>
                    </button>
                  );
                })}
              </div>
              {echoViolationRecords.length > 8 ? (
                <p className="mt-3 text-xs leading-5 text-ink/60">
                  Showing 8 of {echoViolationRecords.length.toLocaleString()} ECHO records. Use the map markers for
                  the full county layer.
                </p>
              ) : null}
            </div>
          ) : null}

          <div className="rounded-lg border border-ink/10 bg-white/90 p-5 text-sm leading-6 text-ink/70">
            <p>{epaStatusLabel}</p>
            <p className="mt-2">{permitStatusLabel}</p>
            <p className="mt-2">{echoStatusLabel}</p>
          </div>

          <div className="rounded-lg bg-ink p-5 text-white">
            <p className="text-xs uppercase tracking-normal text-white/70">Legend</p>
            <ul className="mt-4 space-y-3 text-sm">
              <li className="flex items-center justify-between gap-3">
                <span className="flex items-center gap-3"><span className="h-0 w-7 border-t-[4px] border-[#c6283e]" /> Polluted</span>
                <span>{epaStats.polluted}</span>
              </li>
              <li className="flex items-center justify-between gap-3">
                <span className="flex items-center gap-3"><span className="h-0 w-7 border-t-[4px] border-[#2e7d4f]" /> Good</span>
                <span>{epaStats.good}</span>
              </li>
              <li className="flex items-center justify-between gap-3">
                <span className="flex items-center gap-3"><span className="h-0 w-7 border-t-[4px] border-[#7554a1]" /> Unassessed</span>
                <span>{epaStats.unassessed}</span>
              </li>
              <li className="flex items-center justify-between gap-3">
                <span className="flex items-center gap-3"><span className="h-3 w-3 rounded-full bg-river ring-2 ring-white" /> Active permit</span>
                <span>{permitStats.active}</span>
              </li>
              <li className="flex items-center justify-between gap-3">
                <span className="flex items-center gap-3"><span className="h-3 w-3 rounded-full bg-sunlight ring-2 ring-white" /> Pending permit</span>
                <span>{permitStats.pending}</span>
              </li>
              <li className="flex items-center justify-between gap-3">
                <span className="flex items-center gap-3"><span className="h-3 w-3 rounded-full bg-[#df5b2f] ring-2 ring-white" /> Current ECHO violation</span>
                <span>{echoStats.current}</span>
              </li>
              <li className="flex items-center justify-between gap-3">
                <span className="flex items-center gap-3"><span className="h-3 w-3 rounded-full bg-[#6b4bb1] ring-2 ring-white" /> Recent ECHO violation</span>
                <span>{echoStats.recent}</span>
              </li>
              <li className="flex items-center gap-3"><span className="h-4 w-4 rounded-sm bg-moss/70" /> HUC8 watershed area</li>
              <li className="flex items-center gap-3"><span className="h-0 w-7 border-t-2 border-dashed border-[#547a76]" /> Congressional boundary</li>
              <li className="flex items-center gap-3"><span className="h-0 w-7 border-t-2 border-dashed border-gold" /> State legislative boundary</li>
            </ul>
          </div>
        </aside>
      </div>
    </section>
  );
}

export function CountyDetailMap({ slug, name }: { slug: string; name: string }) {
  const [map, setMap] = useState<CountyMapRecord | null>(null);
  const [loadFailed, setLoadFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadMap() {
      setLoadFailed(false);

      try {
        const response = await fetch(`/data/county-maps/${slug}.json`);
        if (!response.ok) {
          throw new Error(`Map request failed with ${response.status}`);
        }
        const countyMap = (await response.json()) as CountyMapRecord;
        if (!cancelled) {
          setMap(countyMap);
        }
      } catch {
        if (!cancelled) {
          setLoadFailed(true);
        }
      }
    }

    setMap(null);
    void loadMap();

    return () => {
      cancelled = true;
    };
  }, [slug]);

  if (map) {
    return <CountyDetailMapView map={map} />;
  }

  return (
    <section id="county-map" className="card scroll-mt-6 overflow-hidden">
      <div className="border-b border-ink/10 p-6">
        <p className="text-xs uppercase tracking-normal text-river">County map</p>
        <h2 className="mt-2 text-2xl font-semibold">{name} County interactive map</h2>
      </div>
      <div className="p-6">
        <div className="flex min-h-[420px] items-center justify-center rounded-lg border border-ink/10 bg-mist text-sm text-ink/60">
          {loadFailed ? "County map could not be loaded." : "Loading county map..."}
        </div>
      </div>
    </section>
  );
}
