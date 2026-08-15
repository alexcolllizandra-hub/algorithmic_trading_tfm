import Link from "next/link";

import { REPO_URL } from "@/components/landing/content";
import { Reveal } from "@/components/landing/Reveal";
import { LANDING_CHART } from "@/components/landing/charts/palette";

export function FinalCta() {
  return (
    <section id="seguir" className="relative isolate overflow-hidden border-t border-border/70">
      <div
        className="pointer-events-none absolute left-1/2 top-0 h-[28rem] w-[52rem] -translate-x-1/2 rounded-full opacity-[0.12] blur-3xl"
        style={{
          background: `radial-gradient(closest-side, ${LANDING_CHART.accent}, transparent)`,
        }}
        aria-hidden
      />

      <div className="relative mx-auto w-full max-w-6xl px-6 py-24 text-center md:py-32">
        <Reveal>
          <h2 className="mx-auto max-w-3xl text-balance text-3xl font-semibold tracking-tight md:text-4xl">
            El código, los datos y los resultados negativos están abiertos
          </h2>
        </Reveal>

        <Reveal delay={0.05}>
          <p className="mx-auto mt-5 max-w-2xl text-pretty text-lg leading-relaxed text-muted">
            Puedes clonar el repositorio, regenerar cada cifra de esta página y comprobar que el
            holdout sigue cerrado. Si encuentras un error metodológico, abrir una issue es la forma
            más útil de contribuir.
          </p>
        </Reveal>

        <Reveal delay={0.1}>
          <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <a
              href={REPO_URL}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center justify-center gap-2 rounded-md bg-accent px-5 py-3 text-sm font-semibold text-accent-fg transition-transform hover:-translate-y-0.5"
            >
              Ver el repositorio
              <span aria-hidden>{"\u2197"}</span>
            </a>
            <Link
              href="/panel"
              className="inline-flex items-center justify-center gap-2 rounded-md border border-border bg-surface px-5 py-3 text-sm font-medium transition-colors hover:border-accent/50 hover:text-accent"
            >
              Entrar al panel de investigación
            </Link>
          </div>
        </Reveal>

        <Reveal delay={0.15}>
          <p className="mx-auto mt-12 max-w-2xl text-sm leading-relaxed text-muted/80">
            Proyecto académico. No es asesoramiento financiero, no gestiona dinero real y no está
            conectado a ningún exchange.
          </p>
        </Reveal>
      </div>
    </section>
  );
}
