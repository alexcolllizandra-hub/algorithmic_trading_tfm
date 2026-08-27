"use client";

/**
 * Bilingual copy for the perp-lab research platform.
 *
 * `es` is the source dictionary and defines the shape every other locale must
 * satisfy: `en` is typed as `Dictionary`, so a missing or misspelled key is a
 * compile error rather than a blank string in production. There is no runtime
 * fallback by design -- a silent fallback would let an untranslated section
 * ship unnoticed.
 *
 * The locale lives in React state, is persisted to localStorage, and is
 * mirrored onto `<html lang>` so screen readers and search engines see the
 * language actually being rendered. Server-side and first paint use the
 * default locale; the stored preference is applied in an effect, which is why
 * `LocaleSwitch` renders nothing until mounted (see its comment).
 */

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { en } from "@/lib/i18n/en";
import { es } from "@/lib/i18n/es";

/**
 * The dictionary shape, with string literals widened.
 *
 * `es` is declared `as const`, which types every value as its own literal --
 * useful for the source but useless as a contract: `"research platform"` is
 * not assignable to `"plataforma de investigación"`. Widening keeps the
 * structural check (a missing or misspelled key is still a compile error)
 * while letting each locale supply its own text.
 */
type Widen<T> = T extends string
  ? string
  : T extends number
    ? number
    : T extends boolean
      ? boolean
      : { [K in keyof T]: Widen<T[K]> };

export type Dictionary = Widen<typeof es>;
export type Locale = "es" | "en";

export const LOCALES: Locale[] = ["es", "en"];
export const DEFAULT_LOCALE: Locale = "es";

const DICTIONARIES: Record<Locale, Dictionary> = { es, en };
const STORAGE_KEY = "perp-lab.locale";

/** Human label for each locale, in its own language. */
export const LOCALE_LABEL: Record<Locale, string> = {
  es: "Español",
  en: "English",
};

interface I18nValue {
  locale: Locale;
  setLocale: (next: Locale) => void;
  t: Dictionary;
  /** False until the stored preference has been read, to avoid a flash. */
  ready: boolean;
}

const I18nContext = createContext<I18nValue | null>(null);

function isLocale(value: string | null): value is Locale {
  return value === "es" || value === "en";
}

export function I18nProvider({
  children,
  forceLocale,
}: {
  children: React.ReactNode;
  /**
   * Pin the locale and skip both storage and browser detection.
   *
   * Tests assert against one language, and jsdom reports `navigator.language`
   * as en-US, which would otherwise flip the copy under them. Also the hook a
   * server-rendered locale would use if the app ever routes by language.
   */
  forceLocale?: Locale;
}) {
  const [locale, setLocaleState] = useState<Locale>(forceLocale ?? DEFAULT_LOCALE);
  const [ready, setReady] = useState(forceLocale !== undefined);

  useEffect(() => {
    if (forceLocale !== undefined) return;
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (isLocale(stored)) {
      setLocaleState(stored);
    } else if (window.navigator.language.toLowerCase().startsWith("en")) {
      // Only consulted when the visitor has never chosen: an explicit choice
      // always wins over the browser's guess.
      setLocaleState("en");
    }
    setReady(true);
  }, [forceLocale]);

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  const setLocale = useCallback(
    (next: Locale) => {
      if (forceLocale !== undefined) return;
      setLocaleState(next);
      window.localStorage.setItem(STORAGE_KEY, next);
    },
    [forceLocale]
  );

  const value = useMemo<I18nValue>(
    () => ({ locale, setLocale, t: DICTIONARIES[locale], ready }),
    [locale, setLocale, ready]
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

/** The active dictionary. Throws outside the provider rather than guessing. */
export function useI18n(): Dictionary {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used inside <I18nProvider>");
  return ctx.t;
}

/** The locale itself, for components that switch formatting rather than copy. */
export function useLocale() {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useLocale must be used inside <I18nProvider>");
  return { locale: ctx.locale, setLocale: ctx.setLocale, ready: ctx.ready };
}

/**
 * BCP-47 tag for `Intl` formatters.
 *
 * Spanish uses es-ES (comma decimal, dot thousands) and English en-GB rather
 * than en-US, because the thesis reports metric conventions throughout.
 */
export function useIntlLocale(): string {
  const { locale } = useLocale();
  return locale === "es" ? "es-ES" : "en-GB";
}
