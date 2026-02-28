import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "NTU Logbook Generator",
  description: "Transform your raw daily notes into formal NTU industrial attachment logbook entries using AI.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
