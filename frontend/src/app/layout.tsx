import type { Metadata } from "next";
import { Space_Grotesk, DM_Sans } from "next/font/google";
import "./globals.css";

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
        {/* Navigation Bar (Floating Style) */}
        <nav className="fixed top-4 left-4 right-4 bg-white/90 backdrop-blur-md border border-border rounded-2xl shadow-sm z-50 flex items-center justify-between px-6 py-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <span className="font-heading font-bold text-xl tracking-tight text-foreground">GridMind AI</span>
          </div>
          <div className="flex items-center gap-4 text-sm font-medium">
            <a href="/dashboard" className="text-primary hover:text-primary/80 transition-colors">Dashboard</a>
            <a href="#" className="text-slate-500 hover:text-foreground transition-colors">Transformers</a>
            <a href="#" className="text-slate-500 hover:text-foreground transition-colors">Reports</a>
            <div className="w-8 h-8 rounded-full bg-slate-200 border border-slate-300"></div>
          </div>
        </nav>
        
        {/* Main Content Area */}
        <main className="pt-24 pb-10 px-4 md:px-8 max-w-[1600px] mx-auto">
          {children}
        </main>
      </body>
    </html>
  );
}
