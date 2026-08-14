export interface NavItem {
  href: string;
  label: string;
  icon: string;
  description: string;
}

export const NAV: NavItem[] = [
  {
    href: "/",
    label: "Visión general",
    icon: "\u25C9",
    description: "Fases, evidencia y advertencias",
  },
  {
    href: "/guia",
    label: "Guía",
    icon: "\u25D4",
    description: "Recorrido didáctico en 13 paneles",
  },
  {
    href: "/datos-eda",
    label: "Datos y EDA",
    icon: "\u2637",
    description: "Cobertura, cronología y hallazgos",
  },
  {
    href: "/metodologia",
    label: "Metodología",
    icon: "\u2699",
    description: "Features, estrategias y validación",
  },
  {
    href: "/experimentos",
    label: "Experimentos",
    icon: "\u2263",
    description: "Búsqueda RS vs GA",
  },
  {
    href: "/resultados",
    label: "Resultados",
    icon: "\u2197",
    description: "Equity, drawdown y operaciones",
  },
  {
    href: "/estudio",
    label: "Cierre del estudio",
    icon: "\u2696",
    description: "13 familias, corrección múltiple y holdout",
  },
  {
    href: "/diagnostico",
    label: "Diagnóstico",
    icon: "\u25A6",
    description: "Artefactos y sistema",
  },
];
