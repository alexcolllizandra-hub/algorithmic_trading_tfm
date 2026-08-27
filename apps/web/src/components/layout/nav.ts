import type { Dictionary } from "@/lib/i18n";

export interface NavItem {
  href: string;
  label: string;
  icon: string;
  description: string;
}

export interface NavGroup {
  key: string;
  label: string;
  items: NavItem[];
}

/**
 * Sidebar entries grouped into the reading order of the site.
 *
 * The grouping is the narrative: start (what this is), learn (the theory,
 * kept apart from the evidence on purpose), the study itself in the order the
 * research ran (data → methodology → search → results → closure), then the
 * explorer for hands-on inspection and the system pages. Labels come from the
 * active dictionary; icons stay in code because they carry no language.
 */
export function navGroups(t: Dictionary): NavGroup[] {
  return [
    {
      key: "start",
      label: t.navGroups.start,
      items: [
        { href: "/", label: "Landing", icon: "◈", description: t.app.tagline },
        {
          href: "/panel",
          label: t.nav.overview.label,
          icon: "◉",
          description: t.nav.overview.description,
        },
      ],
    },
    {
      key: "learn",
      label: t.navGroups.learn,
      items: [
        { href: "/guia", label: t.nav.guia.label, icon: "◔", description: t.nav.guia.description },
      ],
    },
    {
      key: "study",
      label: t.navGroups.study,
      items: [
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
          icon: "⚖",
          description: t.nav.resultados.description,
        },
        {
          href: "/cuadernos",
          label: t.nav.cuadernos.label,
          icon: "≡",
          description: t.nav.cuadernos.description,
        },
      ],
    },
    {
      key: "explore",
      label: t.navGroups.explore,
      items: [
        {
          href: "/estrategias",
          label: t.nav.estrategias.label,
          icon: "∿",
          description: t.nav.estrategias.description,
        },
        {
          href: "/laboratorio",
          label: t.nav.laboratorio.label,
          icon: "⚗",
          description: t.nav.laboratorio.description,
        },
      ],
    },
    {
      key: "system",
      label: t.navGroups.system,
      items: [
        {
          href: "/diagnostico",
          label: t.nav.diagnostico.label,
          icon: "▦",
          description: t.nav.diagnostico.description,
        },
      ],
    },
  ];
}

/** Flat list, for consumers that only need the items. */
export function navItems(t: Dictionary): NavItem[] {
  return navGroups(t).flatMap((group) => group.items);
}
