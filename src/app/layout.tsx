import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { assetPath } from "@/lib/assetPath";
import "maplibre-gl/dist/maplibre-gl.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "PolicyWatch",
  description:
    "Tennessee environmental health, water, and policy context by county."
};

function HarpethCredit({ compact = false }: { compact?: boolean }) {
  return (
    <div
      className={`flex items-center gap-3 rounded-md border border-ink/10 bg-foam/80 px-3 py-2 ${
        compact ? "max-w-fit" : ""
      }`}
    >
      <Image
        src={assetPath("/brand/HC-Logo.png")}
        alt=""
        width={523}
        height={771}
        className={compact ? "h-12 w-auto object-contain" : "h-16 w-auto object-contain"}
      />
      <div className="leading-tight">
        <p className="text-xs uppercase tracking-normal text-ink/55">Developed by</p>
        <p className="text-sm font-semibold text-ink">Harpeth Conservancy</p>
      </div>
    </div>
  );
}

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <header className="border-b border-ink/10 bg-white/95">
          <div className="shell flex flex-col gap-4 py-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex items-center gap-3">
              <Link
                href="/"
                aria-label="PolicyWatch home"
                className="relative h-10 w-10 shrink-0 overflow-hidden rounded-md bg-river no-underline"
              >
                <span className="absolute left-0 top-2 h-2 w-full bg-gold" />
                <span className="absolute bottom-2 left-0 h-2 w-full bg-white/35" />
              </Link>
              <div>
                <Link href="/" className="text-lg font-semibold text-ink no-underline hover:text-river">
                  PolicyWatch
                </Link>
                <p className="text-xs uppercase tracking-normal text-ink/55">
                  Tennessee county intelligence
                </p>
              </div>
            </div>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between lg:gap-6">
              <nav className="flex flex-wrap gap-4 text-sm font-medium">
                <Link className="text-ink/75 no-underline hover:text-gold" href="/">
                  Home
                </Link>
                <Link className="text-ink/75 no-underline hover:text-gold" href="/counties">
                  Counties
                </Link>
                <Link className="text-ink/75 no-underline hover:text-gold" href="/rankings">
                  Rankings
                </Link>
                <Link className="text-ink/75 no-underline hover:text-gold" href="/sources">
                  Data sources
                </Link>
                <Link className="text-ink/75 no-underline hover:text-gold" href="/glossary">
                  Glossary
                </Link>
              </nav>
              <HarpethCredit compact />
            </div>
          </div>
        </header>
        <main>{children}</main>
        <footer className="mt-10 border-t border-ink/10 bg-white/80">
          <div className="shell flex flex-col gap-4 py-6 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-semibold text-ink">PolicyWatch</p>
              <p className="mt-1 text-xs leading-5 text-ink/60">
                Tennessee river health, water, and policy context by county.
              </p>
            </div>
            <HarpethCredit />
          </div>
        </footer>
      </body>
    </html>
  );
}
