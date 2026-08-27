"use client";

import { LocaleSwitch } from "@/components/layout/LocaleSwitch";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { useI18n } from "@/lib/i18n";
import { useHealth } from "@/lib/hooks";

export function Topbar({ title }: { title: string }) {
  const t = useI18n();
  const { data, error } = useHealth();
  const online = !error && data?.status === "ok";

  return (
    <header className="sticky top-0 z-10 flex items-center justify-between border-b border-border bg-bg/80 px-6 py-3 backdrop-blur">
      <h1 className="text-lg font-semibold tracking-tight">{title}</h1>
      <div className="flex items-center gap-3">
        <span className="flex items-center gap-2 text-xs text-muted">
          <span
            className={`h-2 w-2 rounded-full ${online ? "bg-positive" : "bg-negative"}`}
            aria-hidden
          />
          {online ? t.app.apiOnline : t.app.apiOffline}
          {data ? ` \u00B7 ${data.runs_available} ${t.app.runs}` : ""}
        </span>
        <LocaleSwitch />
        <ThemeToggle />
      </div>
    </header>
  );
}
