import { es } from "@/lib/i18n/es";

export interface NavItem {
  href: string;
  label: string;
  icon: string;
  description: string;
}

export const NAV: NavItem[] = [
  {
    href: "/",
    label: es.nav.overview.label,
    icon: "\u25C9",
    description: es.nav.overview.description,
  },
  {
    href: "/datos-eda",
    label: es.nav.datosEda.label,
    icon: "\u2637",
    description: es.nav.datosEda.description,
  },
  {
    href: "/metodologia",
    label: es.nav.metodologia.label,
    icon: "\u2699",
    description: es.nav.metodologia.description,
  },
  {
    href: "/experimentos",
    label: es.nav.experimentos.label,
    icon: "\u2263",
    description: es.nav.experimentos.description,
  },
  {
    href: "/resultados",
    label: es.nav.resultados.label,
    icon: "\u2197",
    description: es.nav.resultados.description,
  },
  {
    href: "/diagnostico",
    label: es.nav.diagnostico.label,
    icon: "\u25A6",
    description: es.nav.diagnostico.description,
  },
];
