import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Terminal Trading — Institutional Gold Intelligence",
  description: "Institutional Gold Trading Terminal",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-[#0a0e1a] text-white antialiased font-mono">
        {children}
      </body>
    </html>
  );
}
