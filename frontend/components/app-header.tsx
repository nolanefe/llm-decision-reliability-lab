"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_LINKS = [
  { href: "/", label: "Overview", match: (path: string) => path === "/" },
  {
    href: "/datasets",
    label: "Datasets",
    match: (path: string) => path.startsWith("/datasets"),
  },
  {
    href: "/experiments",
    label: "Experiments",
    match: (path: string) => path.startsWith("/experiments"),
  },
];

export function AppHeader() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 border-b border-[var(--color-border)] bg-[var(--color-bg-surface)] shadow-[var(--shadow-sm)]">
      <div className="mx-auto flex max-w-[var(--content-max-width)] flex-wrap items-center justify-between gap-3 px-[var(--page-padding-x)] py-3">
        <Link
          href="/"
          className="text-sm font-semibold tracking-tight text-[var(--color-text-primary)] no-underline sm:text-base"
        >
          LLM Decision Reliability Lab
        </Link>
        <nav aria-label="Primary" className="flex flex-wrap gap-1">
          {NAV_LINKS.map((link) => {
            const active = link.match(pathname);
            return (
              <Link
                key={link.href}
                href={link.href}
                aria-current={active ? "page" : undefined}
                className={`rounded-[var(--radius-md)] px-3 py-1.5 text-sm font-medium no-underline transition-colors ${
                  active
                    ? "bg-[var(--color-accent-subtle)] text-[var(--color-accent)]"
                    : "text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-muted)] hover:text-[var(--color-text-primary)]"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
