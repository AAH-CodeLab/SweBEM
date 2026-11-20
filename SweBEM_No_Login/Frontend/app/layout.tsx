import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Swedish Building Energy Simulator (Demo)",
  description: "Energy simulation for Swedish buildings — demo build, no login required.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
