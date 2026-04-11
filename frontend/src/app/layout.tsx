import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

import { Navigation } from "@/components/Navigation";

export const metadata: Metadata = {
  title: "CurateAI | Intelligence Console",
  description: "Real-time content intelligence and agentic curation",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full bg-background text-foreground selection:bg-primary/30">
        <Navigation />
        <main className="pl-64 min-h-screen">
          <div className="max-w-[1600px] mx-auto p-8 lg:p-12">
            {children}
          </div>
        </main>
      </body>
    </html>
  );
}
