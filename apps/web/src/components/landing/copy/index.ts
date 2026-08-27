"use client";

// Landing copy: one dictionary per locale, selected by the shared i18n
// context. The Widen mapped type erases the `as const` literal types from the
// Spanish source so the English dictionary type-checks against the same
// shape without literal-equality noise.

import { useLocale } from "@/lib/i18n";

import { es } from "./es";
import { en } from "./en";

type Widen<T> = T extends string
  ? string
  : T extends number
    ? number
    : T extends boolean
      ? boolean
      : { [K in keyof T]: Widen<T[K]> };

export type LandingCopy = Widen<typeof es>;

const DICTIONARIES: Record<"es" | "en", LandingCopy> = { es, en };

export function useLandingCopy(): LandingCopy {
  const { locale } = useLocale();
  return DICTIONARIES[locale] ?? es;
}

/** Resolve {token} placeholders in a copy string with runtime values. */
export function tpl(text: string, vars: Record<string, string | number>): string {
  return text.replace(/\{(\w+)\}/g, (match, key: string) =>
    key in vars ? String(vars[key]) : match
  );
}
