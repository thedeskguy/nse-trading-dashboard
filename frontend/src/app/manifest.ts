import type { MetadataRoute } from "next";

// Web App Manifest (Next 16 metadata route). Makes TradeDash installable as a
// standalone PWA. Colors match the dark-first theme (globals.css `.dark`).
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "TradeDash — Trading Analytics",
    short_name: "TradeDash",
    description:
      "Real-time signals, options analysis, and ML predictions for Indian markets.",
    start_url: "/dashboard",
    scope: "/",
    display: "standalone",
    orientation: "portrait",
    background_color: "#000000",
    theme_color: "#000000",
    categories: ["finance", "business"],
    icons: [
      { src: "/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icon-192.png", sizes: "192x192", type: "image/png", purpose: "maskable" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
