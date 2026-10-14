import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}"
  ],
  theme: {
    extend: {
      colors: {
        ink: "#2f3834",
        river: "#3b6e63",
        moss: "#6f8f5f",
        sand: "#e7ece4",
        foam: "#edf3ee",
        mist: "#cbd9d0",
        gold: "#af8401",
        sunlight: "#f5bf54",
        rust: "#9f4f2a"
      },
      fontFamily: {
        sans: [
          "futura-pt",
          "Aptos",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "sans-serif"
        ]
      },
      boxShadow: {
        card: "0 12px 26px rgba(47, 56, 52, 0.08)"
      }
    }
  },
  plugins: []
};

export default config;
