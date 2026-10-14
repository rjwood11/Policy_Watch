import { assetPath } from "@/lib/assetPath";

export type LandUseClass = {
  id: number;
  label: string;
  color: string;
  codes: number[];
  description: string;
};

export type CountyLandUse = {
  classCounts?: Record<string, number>;
  imageUrl: string;
  width: number;
  height: number;
  bounds: [number, number, number, number];
  coordinates: [[number, number], [number, number], [number, number], [number, number]];
};

type LandUseManifest = {
  year: number;
  groundResolutionMeters: number;
  classes: LandUseClass[];
  counties: Record<string, CountyLandUse>;
};

export type LoadedLandUse = {
  county: CountyLandUse;
  year: number;
  resolution: number;
  pixels: Uint8ClampedArray;
  classesByColor: Map<number, LandUseClass>;
};

export async function loadCountyLandUse(slug: string, signal: AbortSignal): Promise<LoadedLandUse> {
  const response = await fetch(assetPath("/data/landuse/manifest.json"), { signal });
  if (!response.ok) {
    throw new Error("Land-cover data unavailable");
  }
  const manifest = (await response.json()) as LandUseManifest;
  const entry = manifest.counties[slug];
  if (!entry) {
    throw new Error("No land-cover data for this county");
  }
  const county = { ...entry, imageUrl: assetPath(entry.imageUrl) };

  const image = new Image();
  image.src = county.imageUrl;
  await image.decode();
  signal.throwIfAborted();
  if (image.naturalWidth !== county.width || image.naturalHeight !== county.height) {
    throw new Error("Land-cover image dimensions do not match metadata");
  }
  const canvas = document.createElement("canvas");
  canvas.width = county.width;
  canvas.height = county.height;
  const context = canvas.getContext("2d", { willReadFrequently: true });
  if (!context) {
    throw new Error("Could not read land-cover image");
  }
  context.drawImage(image, 0, 0);
  return {
    county,
    year: manifest.year,
    resolution: manifest.groundResolutionMeters,
    pixels: context.getImageData(0, 0, canvas.width, canvas.height).data,
    classesByColor: new Map(manifest.classes.map((item) => [Number.parseInt(item.color.slice(1), 16), item]))
  };
}

export function sampleLandUse(data: LoadedLandUse, longitude: number, latitude: number): LandUseClass | undefined {
  // The image and its sampling grid both use Web Mercator, matching MapLibre.
  const radius = 6378137;
  const x = radius * longitude * Math.PI / 180;
  const clampedLatitude = Math.max(-85.051129, Math.min(85.051129, latitude));
  const y = radius * Math.log(Math.tan(Math.PI / 4 + clampedLatitude * Math.PI / 360));
  const [west, south, east, north] = data.county.bounds;
  if (x < west || x >= east || y <= south || y > north) {
    return undefined;
  }
  const column = Math.floor((x - west) / (east - west) * data.county.width);
  const row = Math.floor((north - y) / (north - south) * data.county.height);
  const offset = (row * data.county.width + column) * 4;
  if (!data.pixels[offset + 3]) {
    return undefined;
  }
  const color = (data.pixels[offset] << 16) | (data.pixels[offset + 1] << 8) | data.pixels[offset + 2];
  return data.classesByColor.get(color);
}
