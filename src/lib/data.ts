import fs from "node:fs";
import path from "node:path";

export type StateRank = {
  rank: number;
  total: number;
  tieCount: number;
  display: string;
  basis: string;
};

export type CountyRecord = {
  slug: string;
  name: string;
  region: string;
  population: number;
  buildDate: string;
  prototypeStatus: {
    label: string;
    coverageNote: string;
    availableFeatures: string[];
  };
  isFeatured: boolean;
  watersheds: string[];
  legislativeDistricts: string[];
  congressionalDistricts: string[];
  streamMiles: {
    impaired: number;
    fullAttainment: number;
    notAssessed: number;
    otherAssessed: number;
    total: number;
  };
  attainmentCategories: Array<{
    category: string;
    label: string;
    miles: number;
  }>;
  rankings: Record<string, StateRank>;
  impairmentSummary: string;
  impairmentCauses: Array<{
    cause: string;
    label: string;
    miles: number;
    assessmentUnits: number;
  }>;
  sampleImpairments: Array<{
    waterbody: string;
    status: string;
    causes: string[];
  }>;
  sampleWaterbodies: string[];
  cejstSummary: string;
  stressSummary: {
    sourceDataset: string;
    updatedAt: string;
    caveat: string;
    water: {
      label: string;
      tracts: number;
      tractCount: number;
      percent: number;
      stateRank: StateRank;
      description: string;
    };
    climate: {
      label: string;
      tracts: number;
      tractCount: number;
      percent: number;
      stateRank: StateRank;
      description: string;
    };
  };
  overview: string;
  getInvolved: string[];
  indicators: Array<{
    key: string;
    label: string;
    value: string;
    definition: string;
    caveat: string;
    sourceDataset: string;
    updatedAt: string;
    stateRank?: StateRank;
  }>;
  monitoringSummary: {
    stations: number;
    riverStations: number;
  };
  permittingSummary: {
    activePermits: number;
    uniquePermittees: number;
    permittedFlow: number;
  };
  scenicRiverSummary: {
    miles: number;
    segments: number;
    names: string[];
  };
  waterServiceSummary: {
    serviceAreas: number;
    names: string[];
  };
};

export type CountyIndexRecord = {
  slug: string;
  name: string;
  region: string;
  summary: string;
  hasPage: boolean;
  isFeatured: boolean;
};

export type DataSourceRecord = {
  dataset: string;
  purpose: string;
  sourceName: string;
  sourceUrl: string;
  refreshFrequency: string;
  lastUpdated: string;
  lastChecked?: string;
  refreshStatus?: string;
  notes: string;
};

export type CountyMapFeature = {
  type: "Feature";
  properties: Record<string, string | number | null>;
  geometry: {
    type: "Polygon" | "MultiPolygon" | "LineString" | "MultiLineString" | "Point" | "MultiPoint";
    coordinates:
      | number[]
      | number[][]
      | number[][][]
      | number[][][][]
      | number[][][][][];
  };
};

export type CountyMapCollection = {
  type: "FeatureCollection";
  features: CountyMapFeature[];
};

export type CountyMapRecord = {
  slug: string;
  name: string;
  county: CountyMapCollection;
  rivers: CountyMapCollection;
  impairment: CountyMapCollection;
  roads: CountyMapCollection;
  places: CountyMapCollection;
  watersheds: CountyMapCollection;
  waterUtilities: CountyMapCollection;
  protectedAreas: CountyMapCollection;
  landfills: CountyMapCollection;
  superfundSites: CountyMapCollection;
  superfundUpdatedAt: string;
  districts: {
    senate: CountyMapCollection;
    house: CountyMapCollection;
    congressional: CountyMapCollection;
  };
};

const publicDir = path.join(process.cwd(), "public", "data");

function readJson<T>(parts: string[]): T {
  const filePath = path.join(publicDir, ...parts);
  return JSON.parse(fs.readFileSync(filePath, "utf8")) as T;
}

export function getCountyIndex() {
  return readJson<CountyIndexRecord[]>(["counties", "index.json"]);
}

export function getCounty(slug: string) {
  return readJson<CountyRecord>(["counties", `${slug}.json`]);
}

export function getDataSources() {
  return readJson<DataSourceRecord[]>(["metadata", "data-sources.json"]);
}

export function getLastUpdated() {
  return readJson<Record<string, string>>(["metadata", "last-updated.json"]);
}

export function getCountyMap(slug: string) {
  return readJson<CountyMapRecord>(["county-maps", `${slug}.json`]);
}
