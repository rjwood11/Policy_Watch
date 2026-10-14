from __future__ import annotations

from scripts.common.prototype_config import (
    LAYERS_DIR,
    PROCESSED_DIR,
    ensure_dirs,
    get_build_context,
)
from scripts.download.data_fetchers import (
    load_acs,
    load_active_permits,
    load_county_map_cities,
    load_county_map_major_roads,
    load_county_map_rivers,
    load_county_map_towns,
    load_huc6,
    load_huc8,
    load_impairment_2026,
    load_justice40,
    load_legislative_layer,
    load_monitoring_stations,
    load_protected_areas,
    load_region_counties,
    load_scenic_rivers,
    load_service_line_inventory,
    load_solid_waste_landfills,
    load_tennessee_counties,
    load_water_service_areas,
)
from scripts.normalize.spatial_processing import simplify_for_web, spatial_labels, write_geojson
from scripts.refresh.superfund import apply_cached_superfund
from scripts.refresh.landuse import apply_cached_landuse_metadata
from scripts.summaries.county_contracts import write_county_map_payloads, write_metadata, write_processed_summary
from scripts.validate.validate_prototype_outputs import validate_outputs


def main() -> None:
    ensure_dirs()
    context = get_build_context()

    counties = load_tennessee_counties()
    huc6 = load_huc6()
    huc8 = load_huc8()
    senate = load_legislative_layer(0)
    house = load_legislative_layer(1)
    congress = load_legislative_layer(2)
    acs = load_acs(counties)
    justice40 = load_justice40()
    impairment = load_impairment_2026()
    monitoring_stations = load_monitoring_stations()
    active_permits = load_active_permits()
    scenic_rivers = load_scenic_rivers()
    water_service_areas = load_water_service_areas()
    service_line_inventory = load_service_line_inventory()
    solid_waste_landfills = load_solid_waste_landfills()
    protected_areas = load_protected_areas()
    region_counties = load_region_counties()
    county_map_rivers = load_county_map_rivers()
    county_map_roads = load_county_map_major_roads()
    county_map_cities = load_county_map_cities()
    county_map_towns = load_county_map_towns()

    (PROCESSED_DIR / "justice40-tennessee-tracts.csv").write_text(
        justice40.drop(columns="geometry", errors="ignore").to_csv(index=False),
        encoding="utf8",
    )
    region_lookup = region_counties.set_index("GEOID")["Region"].to_dict()

    write_geojson(simplify_for_web(counties.copy(), 300), LAYERS_DIR / "counties.geojson")
    write_geojson(simplify_for_web(huc6.copy(), 300), LAYERS_DIR / "huc6.geojson")
    write_geojson(simplify_for_web(huc8.copy(), 250), LAYERS_DIR / "huc8.geojson")
    write_geojson(simplify_for_web(senate.copy(), 250), LAYERS_DIR / "senate-districts.geojson")
    write_geojson(simplify_for_web(house.copy(), 250), LAYERS_DIR / "house-districts.geojson")
    write_geojson(simplify_for_web(congress.copy(), 250), LAYERS_DIR / "congressional-districts.geojson")

    watershed_labels = spatial_labels(
        counties,
        huc8,
        county_label="GEOID",
        other_label="name",
        display_builder=lambda row: str(row["name"]),
        min_share=0.01,
    )
    senate_labels = spatial_labels(
        counties,
        senate.rename(columns={"DISTRICT": "district"}),
        county_label="GEOID",
        other_label="district",
        display_builder=lambda row: f"Senate {row['district']}",
        min_share=0.005,
    )
    house_labels = spatial_labels(
        counties,
        house.rename(columns={"DISTRICT": "district"}),
        county_label="GEOID",
        other_label="district",
        display_builder=lambda row: f"House {row['district']}",
        min_share=0.005,
    )
    congressional_labels = spatial_labels(
        counties,
        congress.rename(columns={"DISTRICT": "district"}),
        county_label="GEOID",
        other_label="district",
        display_builder=lambda row: f"TN-{int(row['district']):02d}",
        min_share=0.005,
    )

    write_processed_summary(
        counties,
        acs,
        justice40,
        impairment,
        monitoring_stations,
        active_permits,
        scenic_rivers,
        water_service_areas,
        region_lookup,
        watershed_labels,
        senate_labels,
        house_labels,
        congressional_labels,
        build_date=context.build_date,
    )
    write_county_map_payloads(
        counties,
        huc8,
        house,
        senate,
        congress,
        county_map_rivers,
        county_map_roads,
        county_map_cities,
        county_map_towns,
        impairment,
        water_service_areas,
        service_line_inventory,
        solid_waste_landfills,
        protected_areas,
    )
    write_metadata(build_date=context.build_date)
    apply_cached_superfund()
    apply_cached_landuse_metadata()

    errors = validate_outputs()
    if errors:
        raise SystemExit("\n".join(errors))


if __name__ == "__main__":
    main()
