import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Novel-to-Webtoon Studio",
  description: "Creator-controlled AI studio transforming novel manuscripts into vertical scrolling webtoons.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-studio-900 text-studio-100 antialiased selection:bg-studio-accent selection:text-white">
        {children}
      </body>
    </html>
  );
}
