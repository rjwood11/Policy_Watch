export const GLOSSARY = [
  { term: "ACS", name: "American Community Survey", meaning: "Census Bureau survey used here for county population and poverty estimates. Five-year estimates combine five years of responses." },
  { term: "API", name: "Application programming interface", meaning: "A service that lets this application request data from another organization." },
  { term: "ATTAINS", name: "Assessment, Total Maximum Daily Load Tracking and Implementation System", meaning: "EPA's system for state-reported surface-water assessments, impairment information, and cleanup planning.", source: "https://www.epa.gov/waterdata/attains" },
  { term: "ATP", name: "Ability to Pay", meaning: "Tennessee affordability screening information included in the local ATP and Justice40 GIS collection. The county screening summaries use the Justice40 tract flags in that collection." },
  { term: "CEJST", name: "Climate and Economic Justice Screening Tool", meaning: "A census-tract screening tool for community burdens. This app uses a versioned local snapshot, rather than a current designation of individual properties." },
  { term: "CWA", name: "Clean Water Act", meaning: "The federal water-pollution law associated with the permit compliance records shown here." },
  { term: "DMR", name: "Discharge Monitoring Report", meaning: "A permit holder's report of discharge monitoring results. Missing reports can trigger compliance flags." },
  { term: "DWR", name: "Division of Water Resources", meaning: "The water-resources division of the Tennessee Department of Environment and Conservation." },
  { term: "ECHO", name: "Enforcement and Compliance History Online", meaning: "EPA's public service for facility compliance and enforcement records.", source: "https://echo.epa.gov/help/facility-search/water-search-results-help" },
  { term: "EPA", name: "U.S. Environmental Protection Agency", meaning: "The federal agency providing the assessment, compliance, and Superfund data used here." },
  { term: "ETL", name: "Extract, transform, load", meaning: "The process of downloading source data, preparing it, and saving it for use in the application." },
  { term: "GAP", name: "Gap Analysis Project", meaning: "The USGS conservation program associated with protected-area management status codes. A GAP status is not a public-access rating.", source: "https://www.usgs.gov/programs/gap-analysis-project/science/pad-us-data-overview" },
  { term: "GIS", name: "Geographic information system", meaning: "Tools and datasets used to store, analyze, and display information tied to locations." },
  { term: "GRR", name: "Galvanized requiring replacement", meaning: "A service-line inventory category for galvanized pipes requiring replacement because of potential lead exposure.", source: "https://www.epa.gov/ground-water-and-drinking-water/planning-and-developing-service-line-inventory" },
  { term: "GWUDI", name: "Groundwater under the direct influence of surface water", meaning: "A drinking-water source classification for groundwater influenced by nearby surface water.", source: "https://www.epa.gov/dwreginfo/sanitary-survey-guidance-manuals" },
  { term: "HUC6", name: "Six-digit Hydrologic Unit Code", meaning: "The code for a basin-scale drainage area used on the statewide map. These areas can cross county and state boundaries." },
  { term: "HUC8", name: "Eight-digit Hydrologic Unit Code", meaning: "The code for a subbasin-scale drainage area used for watershed context on county maps." },
  { term: "JSON", name: "JavaScript Object Notation", meaning: "A file format used to store the app's prepared data. GeoJSON adds geographic shapes and locations." },
  { term: "NC", name: "Noncompliance", meaning: "A reported failure to meet a permit requirement. Quarter counts measure affected periods, not individual incidents." },
  { term: "NLCD", name: "National Land Cover Database", meaning: "USGS imagery classifications of the land surface, such as forest, agriculture, or developed land. These are not zoning categories.", source: "https://www.usgs.gov/centers/eros/science/annual-nlcd-data-access" },
  { term: "NPDES", name: "National Pollutant Discharge Elimination System", meaning: "The Clean Water Act permit program for regulated pollutant discharges." },
  { term: "NPL", name: "National Priorities List", meaning: "The Superfund program's list of priority sites. A deleted listing does not necessarily mean no contamination remains.", source: "https://www.epa.gov/superfund/superfund-national-priorities-list-npl" },
  { term: "PAD-US", name: "Protected Areas Database of the United States", meaning: "The USGS inventory of protected lands and conservation easements. Inclusion does not necessarily mean the public can enter the property.", source: "https://www.usgs.gov/programs/gap-analysis-project/science/pad-us-data-overview" },
  { term: "PL_PSRC", name: "Primary source-water type field", meaning: "TDEC's source-type field: GW is groundwater, GWP purchased groundwater, SW surface water, SWP purchased surface water, GU groundwater influenced by surface water, and GUP its purchased equivalent." },
  { term: "PWSID", name: "Public Water System Identification Number", meaning: "The identifier used to connect drinking-water utility records across datasets." },
  { term: "SNC", name: "Significant noncompliance", meaning: "EPA's classification for certain more serious or persistent permit compliance problems." },
  { term: "SWM", name: "Solid Waste Management", meaning: "The TDEC program associated with landfill permit records." },
  { term: "TDEC", name: "Tennessee Department of Environment and Conservation", meaning: "The state agency providing water permits, drinking-water information, and landfill records." },
  { term: "TIGER", name: "Topologically Integrated Geographic Encoding and Referencing", meaning: "The Census Bureau's geographic database. TIGER/Line files supply the county boundaries used here.", source: "https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html" },
  { term: "TMDL", name: "Total Maximum Daily Load", meaning: "A water-quality planning calculation of how much of a pollutant a waterbody can receive while meeting its water-quality standards." },
  { term: "USGS", name: "U.S. Geological Survey", meaning: "The federal science agency providing watershed boundaries, protected-area data, and land-cover imagery." },
  { term: "WBD", name: "Watershed Boundary Dataset", meaning: "The national drainage-area boundary dataset used for the basin and watershed maps.", source: "https://www.usgs.gov/national-hydrography/watershed-boundary-dataset" }
] as const;

export function glossaryId(term: string) {
  return term.toLowerCase().replaceAll("_", "-");
}
