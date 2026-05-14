import type { Metadata, Viewport } from "next";

import { AppShell } from "@/components/layout/app-shell";
import { Providers } from "@/app/providers";

import "./globals.css";

export const metadata: Metadata = {
  title: "ALEXANDRIA-HERMES · AI Agent Capability Library",
  description:
    "A luxury dark AI agent skill and prompt library.",
};

export const viewport: Viewport = {
  themeColor: "#0b0b0b",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body>
        <Providers>
          <AppShell>{children}</AppShell>
        </Providers>
      </body>
    </html>
  );
}
