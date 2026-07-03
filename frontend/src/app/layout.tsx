import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

// Load Inter font — the typeface used throughout GridMind
const inter = Inter({ subsets: ["latin"] });

// SEO metadata — applies to all pages (can be overridden per page)
export const metadata: Metadata = {
  title: "GridMind — Transformer Intelligence Platform",
  description:
    "Predictive maintenance platform for APDCL distribution transformers. " +
    "Risk scoring, anomaly detection, and GIS visualization.",
};

// RootLayout wraps every page in the app
// Think of it as the equivalent of HTML's <html> and <body> tags
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>{children}</body>
    </html>
  );
}
