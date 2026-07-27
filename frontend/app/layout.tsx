import type { Metadata } from "next";
import { AppHeader } from "@/components/app-header";
import "./globals.css";

export const metadata: Metadata = {
  title: "LLM Decision Reliability Lab",
  description:
    "Compare prompt and model variants on schema validity, quality, consistency, cost, and latency.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full">
      <body className="flex min-h-full flex-col antialiased">
        <AppHeader />
        <main className="mx-auto w-full max-w-[var(--content-max-width)] flex-1 px-[var(--page-padding-x)] py-[var(--page-padding-y)]">
          {children}
        </main>
      </body>
    </html>
  );
}
