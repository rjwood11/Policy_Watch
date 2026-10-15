import introductions from "../../content/counties/introductions.json";

type CountyIntroduction = {
  summary: string;
  sourceUrl: string;
};

export function getCountyIntroduction(slug: string): CountyIntroduction {
  const introduction = (introductions as Record<string, CountyIntroduction>)[slug];

  if (!introduction) {
    throw new Error(`Missing editorial introduction for county: ${slug}`);
  }

  return introduction;
}
