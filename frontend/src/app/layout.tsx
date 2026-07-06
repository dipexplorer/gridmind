import type { Metadata } from "next";
import { Space_Grotesk, DM_Sans } from "next/font/google";
import "./globals.css";
import ClientLayout from "@/components/ClientLayout";

const spaceGrotesk = Space_Grotesk({ 
  subsets: ["latin"], 
  variable: "--font-space-grotesk",
  weight: ['400', '500', '600', '700']
});

const dmSans = DM_Sans({ 
  subsets: ["latin"],
  variable: "--font-dm-sans", 
  weight: ['400', '500', '700']
});

export const metadata: Metadata = {
  title: "GridMind AI - Predictive Maintenance",
  description: "Next-gen Power Grid Intelligence",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${spaceGrotesk.variable} ${dmSans.variable}`}>
      <body className="bg-background text-foreground font-body min-h-screen">
        <ClientLayout>{children}</ClientLayout>
      </body>
    </html>
  );
}
