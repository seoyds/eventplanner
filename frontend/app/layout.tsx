import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Event Orchestrator",
  description: "AI-powered event planning with 10 specialist agents",
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
