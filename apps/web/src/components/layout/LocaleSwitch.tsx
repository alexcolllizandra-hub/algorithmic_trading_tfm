"use client";

import { LOCALE_LABEL, LOCALES, useLocale } from "@/lib/i18n";
import { cn } from "@/lib/cn";

/**
 * Two-state language toggle.
 *
 * Renders a placeholder of the same size until the stored preference has been
 * read, so the control never flashes the wrong language selected and never
 * shifts the layout around it.
 */
export function LocaleSwitch({ className }: { className?: string }) {
  const { locale, setLocale, ready } = useLocale();

  if (!ready) {
    return <div className={cn("h-7 w-[5.5rem] rounded-md bg-surface-2", className)} aria-hidden />;
  }

  return (
    <div
      role="group"
      aria-label={locale === "es" ? "Idioma" : "Language"}
      className={cn(
        "inline-flex items-center gap-0.5 rounded-md border border-border bg-surface p-0.5",
        className
      )}
    >
      {LOCALES.map((code) => {
        const active = code === locale;
        return (
          <button
            key={code}
            type="button"
            onClick={() => setLocale(code)}
            aria-pressed={active}
            title={LOCALE_LABEL[code]}
            className={cn(
              "rounded px-2 py-0.5 text-xs font-medium uppercase tracking-wide transition-colors",
              active ? "bg-accent text-accent-fg" : "text-muted hover:bg-surface-2 hover:text-fg"
            )}
          >
            {code}
          </button>
        );
      })}
    </div>
  );
}
