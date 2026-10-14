import type { CountyRecord, StateRank } from "@/lib/data";

type CountyIndicator = CountyRecord["indicators"][number];

export type RankingMetric = {
  slug: string;
  rankKey: string;
  label: string;
  group: string;
  valueLabel: string;
  getValue: (county: CountyRecord) => string;
};

export type CountyRankingRow = {
  county: CountyRecord;
  rank?: StateRank;
  value: string;
};

function formatInteger(value: number) {
  return value.toLocaleString();
}

function formatMiles(value: number) {
  return `${value.toFixed(1)} mi`;
}

function findIndicator(county: CountyRecord, key: string): CountyIndicator | undefined {
  return county.indicators.find((indicator) => indicator.key === key);
}

function indicatorValue(county: CountyRecord, key: string) {
  return findIndicator(county, key)?.value ?? "n/a";
}

export const rankingMetrics = [
  {
    slug: "population",
    rankKey: "population",
    label: "Population",
    group: "People and screening context",
    valueLabel: "People",
    getValue: (county) => formatInteger(county.population)
  },
  {
    slug: "poverty-rate",
    rankKey: "povertyRate",
    label: "Poverty rate",
    group: "People and screening context",
    valueLabel: "Rate",
    getValue: (county) => indicatorValue(county, "acs-poverty")
  },
  {
    slug: "disadvantaged-tract-share",
    rankKey: "disadvantagedTractShare",
    label: "Disadvantaged tracts",
    group: "People and screening context",
    valueLabel: "Share",
    getValue: (county) => indicatorValue(county, "j40-disadvantaged")
  },
  {
    slug: "impaired-river-miles",
    rankKey: "impairedRiverMiles",
    label: "Impaired river miles",
    group: "Rivers",
    valueLabel: "Miles",
    getValue: (county) => formatMiles(county.streamMiles.impaired)
  },
  {
    slug: "monitoring-stations",
    rankKey: "monitoringStations",
    label: "Monitoring stations",
    group: "Rivers",
    valueLabel: "Stations",
    getValue: (county) => formatInteger(county.monitoringSummary.stations)
  },
  {
    slug: "full-attainment-river-miles",
    rankKey: "fullAttainmentRiverMiles",
    label: "Full attainment river miles",
    group: "Rivers",
    valueLabel: "Miles",
    getValue: (county) => formatMiles(county.streamMiles.fullAttainment)
  },
  {
    slug: "not-assessed-river-miles",
    rankKey: "notAssessedRiverMiles",
    label: "Not currently assessed river miles",
    group: "Rivers",
    valueLabel: "Miles",
    getValue: (county) => formatMiles(county.streamMiles.notAssessed)
  },
  {
    slug: "scenic-river-miles",
    rankKey: "scenicRiverMiles",
    label: "Scenic river miles",
    group: "Rivers",
    valueLabel: "Miles",
    getValue: (county) => formatMiles(county.scenicRiverSummary.miles)
  },
  {
    slug: "active-water-permits",
    rankKey: "activePermits",
    label: "Active water permits",
    group: "Permits and service areas",
    valueLabel: "Permits",
    getValue: (county) => formatInteger(county.permittingSummary.activePermits)
  },
  {
    slug: "water-service-areas",
    rankKey: "waterServiceAreas",
    label: "Public water service areas",
    group: "Permits and service areas",
    valueLabel: "Service areas",
    getValue: (county) => formatInteger(county.waterServiceSummary.serviceAreas)
  },
  {
    slug: "water-stress-tract-share",
    rankKey: "waterStressTractShare",
    label: "Water stressed tracts",
    group: "Justice40 / CEJST",
    valueLabel: "Share",
    getValue: (county) => `${county.stressSummary.water.percent.toFixed(1)}%`
  },
  {
    slug: "climate-stress-tract-share",
    rankKey: "climateStressTractShare",
    label: "Climate stressed tracts",
    group: "Justice40 / CEJST",
    valueLabel: "Share",
    getValue: (county) => `${county.stressSummary.climate.percent.toFixed(1)}%`
  }
] satisfies RankingMetric[];

export function getRankingMetric(slug: string) {
  return rankingMetrics.find((metric) => metric.slug === slug);
}

export function getRank(county: CountyRecord, metric: RankingMetric) {
  return county.rankings[metric.rankKey];
}

export function getCountyRankingRows(counties: CountyRecord[], metric: RankingMetric) {
  return counties
    .map((county) => ({
      county,
      rank: getRank(county, metric),
      value: metric.getValue(county)
    }))
    .sort((a, b) => {
      if (!a.rank && !b.rank) {
        return a.county.name.localeCompare(b.county.name);
      }

      if (!a.rank) {
        return 1;
      }

      if (!b.rank) {
        return -1;
      }

      return a.rank.rank - b.rank.rank || a.county.name.localeCompare(b.county.name);
    });
}
