import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Santa Claws Dashboard",
  description: "NemoClaw dashboard for Santa Claws",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
