import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Ad Prompt Intelligence",
  description: "Analyze ad creatives and generate reusable prompts",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-50 text-slate-900">{children}</body>
    </html>
  );
}
