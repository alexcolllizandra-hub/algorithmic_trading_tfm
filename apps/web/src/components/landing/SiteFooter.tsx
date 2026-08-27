"use client";

import Link from "next/link";

import { REPO_URL } from "@/components/landing/content";
import { useLandingCopy } from "@/components/landing/copy";
import { useProvenance } from "@/lib/site-data";

export function SiteFooter() {
  const { data } = useProvenance();
  const c = useLandingCopy();

  return (
    <footer className="border-t border-border bg-surface/30">
      <div className="mx-auto grid w-full max-w-6xl gap-8 px-6 py-12 md:grid-cols-[1fr_auto] md:items-end">
        <div>
          <p className="flex items-center gap-2.5 font-semibold tracking-tight">
            <span className="text-accent" aria-hidden>
              {"◈"}
            </span>
            Alx Systems
          </p>
          <p className="mt-3 max-w-md text-sm leading-relaxed text-muted">{c.footer.tagline}</p>
          <p className="mt-4 max-w-md text-xs leading-relaxed text-muted/80">
            {c.footer.disclaimer}
          </p>
          {data && (
            <p className="mt-4 font-mono text-xs text-muted/70">
              {c.footer.generated} {data.generated_at.slice(0, 10)} · commit{" "}
              {data.code_commit?.slice(0, 7) ?? "—"} · {c.footer.contract} v{data.contract_version}
            </p>
          )}
        </div>

        <nav className="flex flex-wrap gap-x-6 gap-y-2 text-sm" aria-label={c.footer.footAria}>
          <Link href="/panel" className="text-muted transition-colors hover:text-fg">
            {c.footer.nav.panel}
          </Link>
          <Link href="/datos-eda" className="text-muted transition-colors hover:text-fg">
            {c.footer.nav.data}
          </Link>
          <Link href="/metodologia" className="text-muted transition-colors hover:text-fg">
            {c.footer.nav.methodology}
          </Link>
          <Link href="/privacidad" className="text-muted transition-colors hover:text-fg">
            {c.footer.nav.privacy}
          </Link>
          <Link href="/aviso-legal" className="text-muted transition-colors hover:text-fg">
            {c.footer.nav.legal}
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
