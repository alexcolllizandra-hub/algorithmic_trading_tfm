"use client";

import { useState } from "react";

import { Card } from "@/components/ui/Card";
import { useI18n } from "@/lib/i18n";
import { cn } from "@/lib/cn";

export function HowToRead({ children, title }: { children: React.ReactNode; title?: string }) {
  const t = useI18n();
  const [open, setOpen] = useState(false);

  return (
    <Card className="border-dashed">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-3 text-left"
        aria-expanded={open}
      >
        <span className="text-sm font-medium text-fg">{title ?? t.common.howToRead}</span>
        <span className="text-xs text-accent">{open ? t.common.collapse : t.common.expand}</span>
      </button>
      <div
        className={cn(
          "overflow-hidden transition-all duration-200",
          open ? "mt-4 max-h-[2000px] opacity-100" : "max-h-0 opacity-0"
        )}
      >
        <div className="space-y-3 text-sm text-muted">{children}</div>
      </div>
    </Card>
  );
}
