/** Public files need the same repository prefix as Next.js routes on GitHub Pages. */
export function assetPath(path: string): string {
  return `${process.env.NEXT_PUBLIC_BASE_PATH || ""}${path}`;
}
