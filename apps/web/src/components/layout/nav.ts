import type { Dictionary } from "@/lib/i18n";

export interface NavItem {
  href: string;
  label: string;
  icon: string;
  description: string;
}

/**
 * Sidebar entries, built from the active dictionary.
 *
 * The labels used to be duplicated here as Spanish literals while the same
 * strings already lived under `nav` in the dictionary; the two drifted apart
 * the moment a second locale existed. Icons stay in code because they carry no
 * language, and the landing entry is the one item with no dictionary key --
 * it points at the public site rather than a panel section.
 */
export function navItems(t: Dictionary): NavItem[] {
  return [
    {
      href: "/",
      label: "Landing",
      icon: "◈",
      description: t.app.tagline,
    },
    {
      href: "/panel",
      label: t.nav.overview.label,
      icon: "◉",
      description: t.nav.overview.description,
    },
    { href: "/guia", label: t.nav.guia.label, icon: "◔", description: t.nav.guia.description },
    {
      href: "/datos-eda",
      label: t.nav.datosEda.label,
      icon: "☷",
      description: t.nav.datosEda.description,
    },
    {
      href: "/metodologia",
      label: t.nav.metodologia.label,
      icon: "⚙",
      description: t.nav.metodologia.description,
    },
    {
      href: "/experimentos",
      label: t.nav.experimentos.label,
      icon: "≣",
      description: t.nav.experimentos.description,
    },
    {
      href: "/resultados",
      label: t.nav.resultados.label,
      icon: "↗",
      description: t.nav.resultados.description,
    },
    {
      href: "/estudio",
      label: t.nav.estudio.label,
      icon: "⚖",
      description: t.nav.estudio.description,
    },
    {
      href: "/diagnostico",
      label: t.nav.diagnostico.label,
      icon: "▦",
      description: t.nav.diagnostico.description,
    },
  ];
}
