"use client";

import Link from "next/link";

import { REPO_URL } from "@/components/landing/content";
import { useProvenance } from "@/lib/site-data";

export function SiteFooter() {
  const { data } = useProvenance();

  return (
    <footer className="border-t border-border bg-surface/30">
      <div className="mx-auto grid w-full max-w-6xl gap-8 px-6 py-12 md:grid-cols-[1fr_auto] md:items-end">
        <div>
          <p className="flex items-center gap-2.5 font-semibold tracking-tight">
            <span className="text-accent" aria-hidden>
              {"\u25C8"}
            </span>
            Alx Systems
          </p>
          <p className="mt-3 max-w-md text-sm leading-relaxed text-muted">
            Descubrimiento y validación reproducible de estrategias intradía sobre futuros perpetuos
            USDT-M de BTC y ETH.
          </p>
          {data && (
            <p className="mt-4 font-mono text-xs text-muted/70">
              datos generados {data.generated_at.slice(0, 10)} · commit{" "}
              {data.code_commit?.slice(0, 7) ?? "—"} · contrato v{data.contract_version}
            </p>
          )}
        </div>

        <nav className="flex flex-wrap gap-x-6 gap-y-2 text-sm" aria-label="Pie">
          <Link href="/panel" className="text-muted transition-colors hover:text-fg">
            Panel
          </Link>
          <Link href="/datos-eda" className="text-muted transition-colors hover:text-fg">
            Datos y EDA
          </Link>
          <Link href="/metodologia" className="text-muted transition-colors hover:text-fg">
            Metodología
          </Link>
          <a
            href={REPO_URL}
            target="_blank"
            rel="noreferrer"
            className="text-muted transition-colors hover:text-fg"
          >
            GitHub
          </a>
        </nav>
      </div>
    </footer>
  );
}
