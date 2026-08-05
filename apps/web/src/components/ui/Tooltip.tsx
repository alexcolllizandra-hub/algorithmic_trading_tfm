"use client";

import { useState } from "react";

/** Accessible hover/focus tooltip for explaining quantitative metrics. */
export function InfoTip({ text, label }: { text: string; label?: string }) {
  const [open, setOpen] = useState(false);
  return (
    <span className="relative inline-flex">
      <button
        type="button"
        aria-label={label ? `Explain ${label}` : "More information"}
        className="ml-1 inline-flex h-4 w-4 items-center justify-center rounded-full border border-border text-[10px] text-muted hover:text-fg"
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
      >
        i
      </button>
      {open && (
        <span
          role="tooltip"
          className="absolute left-1/2 top-6 z-20 w-64 -translate-x-1/2 rounded-md border border-border bg-surface-2 px-3 py-2 text-xs font-normal normal-case text-fg shadow-lg"
        >
          {text}
        </span>
      )}
    </span>
  );
}
