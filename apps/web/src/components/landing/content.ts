// Editorial content for the public site.
//
// Kept out of the components so the prose can be reviewed as prose. Every
// factual claim here is traceable to a document in the repository, named in
// `source`. Market numbers are never hard-coded: those come from /data.

export const REPO_URL = "https://github.com/alexcolllizandra-hub/algorithmic_trading_tfm";

export type PhaseStatus = "done" | "in-review" | "blocked" | "planned";

export const STATUS_LABEL: Record<PhaseStatus, string> = {
  done: "Construido",
  "in-review": "En revisión",
  blocked: "Bloqueado",
  planned: "Roadmap",
};

export interface PipelineStep {
  id: string;
  title: string;
  what: string;
  status: PhaseStatus;
  detail: string;
}

export const PIPELINE: PipelineStep[] = [
  {
    id: "datos",
    title: "Datos",
    what: "Descarga de velas de BTC y ETH perpetuo en Binance Futures.",
    status: "done",
    detail:
      "Seis años y medio de historia, desde enero de 2020. El archivo descargado no se " +
      "toca nunca más: cualquier corrección se hace en una copia derivada.",
  },
  {
    id: "validacion",
    title: "Validación",
    what: "Se comprueba que los datos sean lo que dicen ser.",
    status: "done",
    detail:
      "Huecos, duplicados, velas imposibles (un mínimo por encima del máximo), volúmenes " +
      "negativos. Lo anómalo se marca y se informa; nunca se borra en silencio.",
  },
  {
    id: "eda",
    title: "Análisis exploratorio",
    what: "Entender el mercado antes de intentar ganarle.",
    status: "done",
    detail:
      "Volatilidad, colas de la distribución, regímenes, estacionalidad, funding y " +
      "dependencia entre activos. Es la fase que decide qué merece la pena intentar.",
  },
  {
    id: "features",
    title: "Indicadores",
    what: "Se calculan señales que solo miran al pasado.",
    status: "done",
    detail:
      "Cada indicador se somete a una prueba de causalidad: si recortas el futuro del " +
      "conjunto de datos, el valor de ayer no puede cambiar.",
  },
  {
    id: "estrategias",
    title: "Estrategias",
    what: "Reglas explícitas y legibles, no cajas negras.",
    status: "done",
    detail:
      "Cruce de medias, ruptura de rango, reversión a la media, consenso multi-marco. " +
      "Si una regla funciona, tiene que poder explicarse en una frase.",
  },
  {
    id: "backtest",
    title: "Backtest con costes",
    what: "Simular la regla sobre el pasado, pagando lo que se paga.",
    status: "done",
    detail:
      "Comisiones, deslizamiento y funding. La orden se decide con la vela cerrada y se " +
      "ejecuta en la apertura de la siguiente, nunca al precio que ya se conoce.",
  },
  {
    id: "validacion-temporal",
    title: "Validación temporal",
    what: "Entrenar en el pasado, evaluar en el futuro. Muchas veces.",
    status: "done",
    detail:
      "Walk-forward con purga y embargo, más búsqueda aleatoria y algoritmo genético con " +
      "presupuesto idéntico, y contabilidad del número de pruebas realizadas.",
  },
  {
    id: "meta",
    title: "Filtro de aprendizaje automático",
    what: "Un modelo que decide cuándo no operar.",
    status: "in-review",
    detail:
      "Etiquetado por triple barrera y un clasificador que filtra las señales de la " +
      "estrategia base. Validado sobre mercados sintéticos con respuesta conocida, " +
      "porque todavía no hay una estrategia base que merezca filtrarse.",
  },
  {
    id: "holdout",
    title: "Evaluación final",
    what: "Abrir los seis meses reservados. Una sola vez.",
    status: "in-review",
    detail:
      "Se abrió una vez, sobre un candidato declarado de antemano, y su lectura existe en " +
      "disco. Quedó pendiente la auditoría de procedencia que comprueba que el candidato " +
      "estaba congelado antes de mirar, así que la cifra no se publica.",
  },
  {
    id: "riesgo",
    title: "Riesgo y cartera",
    what: "Dimensionar posiciones y combinar estrategias.",
    status: "planned",
    detail:
      "Sin sentido hasta que exista al menos una estrategia que sobreviva a todo lo " +
      "anterior. Está especificado, no implementado.",
  },
];

export interface Principle {
  id: string;
  title: string;
  plain: string;
  technical: string;
}

export const PRINCIPLES: Principle[] = [
  {
    id: "cronologico",
    title: "El tiempo no se baraja",
    plain:
      "Para saber si una regla sirve, se entrena con el pasado y se prueba con lo que vino " +
      "después. Mezclar las fechas al azar sería como estudiar el examen con las respuestas " +
      "delante.",
    technical:
      "Particiones estrictamente cronológicas, con purga y embargo entre entrenamiento y " +
      "prueba para que ninguna operación cruce la frontera.",
  },
  {
    id: "holdout",
    title: "Seis meses apartados",
    plain:
      "Los últimos seis meses de datos se apartaron desde el principio y no se miraron para " +
      "elegir nada. Se abrieron una sola vez, al final. Esa lectura quedó retenida a la " +
      "espera de una auditoría de procedencia, y la conclusión del estudio no depende de ella.",
    technical:
      "Partición reservada en [2026-01-01, 2026-07-01). El código de desarrollo falla si " +
      "alguien intenta cargarla; la apertura exigió una ruta explícita y auditada, y su " +
      "resultado permanece sin publicar mientras la auditoría siga pendiente.",
  },
  {
    id: "inmutable",
    title: "El dato crudo no se edita",
    plain:
      "Lo que se descargó del exchange se queda como está. Si hay que arreglar algo, se " +
      "arregla en una copia y queda registrado qué se cambió.",
    technical:
      "data/raw es de solo lectura. Las observaciones extremas se marcan, nunca se eliminan " +
      "automáticamente.",
  },
  {
    id: "reproducible",
    title: "Todo lleva su recibo",
    plain:
      "Cada número de esta página se puede regenerar: se sabe de qué fichero salió, con qué " +
      "versión del código y con qué semilla aleatoria.",
    technical:
      "Manifest por dataset con SHA-256, commit de git en cada artefacto y una única semilla " +
      "global de la que derivan todos los componentes estocásticos.",
  },
];

export interface Concept {
  id: string;
  title: string;
  technical: string;
  everyday: string;
  punchline: string;
  /** Anchor of the section that pays this concept off with measured data. */
  evidence?: { href: string; label: string };
}

export const CONCEPTS: Concept[] = [
  {
    id: "overfitting",
    title: "Sobreajuste",
    technical:
      "Un modelo con suficientes parámetros memoriza el ruido de la muestra y su error fuera " +
      "de muestra crece mientras el de entrenamiento baja.",
    everyday:
      "Es aprenderse de memoria las preguntas del examen del año pasado. Sacas un diez en " +
      "ese examen y suspendes el de este año.",
    punchline: "Un backtest perfecto casi siempre es esto.",
  },
  {
    id: "eficiencia",
    title: "Mercado eficiente",
    technical:
      "Si el precio ya incorpora la información disponible, ninguna regla basada en esa " +
      "información obtiene beneficio esperado positivo neto de costes.",
    everyday:
      "La cola más corta del supermercado deja de serlo en cuanto todos la ven. La ventaja " +
      "desaparece justo cuando la encuentras.",
    punchline: "Por eso el resultado por defecto es que no hay ventaja.",
    evidence: { href: "#costes", label: "Verlo medido" },
  },
  {
    id: "grandes-numeros",
    title: "Ley de los grandes números",
    technical:
      "La media muestral converge a la esperanza al crecer n. Con n pequeño, la varianza del " +
      "estimador hace que el azar parezca destreza.",
    everyday:
      "Diez caras seguidas pasan; con diez lanzamientos no distingues una moneda trucada de " +
      "una normal. Con diez mil, sí.",
    punchline: "Treinta operaciones no demuestran nada.",
  },
  {
    id: "kelly",
    title: "Criterio de Kelly",
    technical:
      "La fracción que maximiza el crecimiento logarítmico esperado del capital. Apostar por " +
      "encima reduce el crecimiento y aumenta la ruina; el óptimo es frágil al error de " +
      "estimación.",
    everyday:
      "Aunque el juego te favorezca, apostarlo todo en cada mano te arruina. El tamaño de la " +
      "apuesta importa tanto como acertar.",
    punchline: "Tener razón y arruinarse no son incompatibles.",
  },
  {
    id: "cisne-negro",
    title: "Cisne negro",
    technical:
      "Los retornos tienen colas mucho más pesadas que una normal: los sucesos extremos son " +
      "órdenes de magnitud más frecuentes de lo que predice el modelo gaussiano.",
    everyday:
      "Un dique diseñado para la peor riada de los últimos cien años no sirve de nada el año " +
      "que llega una peor.",
    punchline: "Lo verás medido más abajo, con los datos reales.",
  },
];

export interface RoadmapPhase {
  id: string;
  period: string;
  title: string;
  status: PhaseStatus;
  summary: string;
  /** Where the claim can be checked in the repository. */
  source?: string;
}

export const ROADMAP: RoadmapPhase[] = [
  {
    id: "fase-1",
    period: "Fase 1",
    title: "Datos y análisis exploratorio",
    status: "done",
    summary:
      "Descarga, validación y EDA completos sobre BTC y ETH perpetuo, con manifiestos y " +
      "hashes por dataset. Es la base de todo lo que viene después.",
    source: "docs/roadmap/current_state.md",
  },
  {
    id: "r2-r3",
    period: "Puertas R2–R3",
    title: "Primeras familias de estrategias",
    status: "done",
    summary:
      "Cinco familias evaluadas con walk-forward, costes y batería de robustez. Ninguna " +
      "promocionó: la puerta se cerró en negativo, que es un resultado y no un fallo.",
    source: "reports/r3_gate/…/thesis_report.md",
  },
  {
    id: "s1",
    period: "Puerta S1",
    title: "Expansión controlada",
    status: "done",
    summary:
      "Cuatro familias nuevas llevadas a piloto. Las cuatro terminaron con retorno total " +
      "compuesto negativo, así que ninguna activó el criterio para continuar.",
    source: "docs/roadmap/gate_s1b_outcome.md",
  },
  {
    id: "s2",
    period: "Puerta S2",
    title: "Segunda expansión",
    status: "in-review",
    summary:
      "Nuevas familias sobre datos de desarrollo, con la misma geometría temporal y los " +
      "mismos presupuestos. Ninguna disparó el criterio de señal parcial.",
    source: "rama feat/s2-evidence-and-strategy-lab",
  },
  {
    id: "m1",
    period: "Fase M1–M2",
    title: "Etiquetado y filtro de aprendizaje automático",
    status: "in-review",
    summary:
      "Triple barrera con costes incorporados y un filtro que aprende cuándo no operar. " +
      "Validado sobre mercados sintéticos: recupera una ventaja plantada y se abstiene " +
      "ante ruido puro. No es un candidato operativo.",
    source: "rama feat/m1m2-synthetic-validation",
  },
  {
    id: "holdout",
    period: "Evaluación final",
    title: "Apertura del holdout",
    status: "in-review",
    summary:
      "Un único disparo sobre los seis meses reservados, con la estrategia elegida de " +
      "antemano. Se ejecutó; la lectura quedó retenida a la espera de la auditoría de " +
      "procedencia que la haría citable.",
    source: "reports/study_closure/final_holdout.md",
  },
  {
    id: "cartera",
    period: "Fases P1–P3",
    title: "Cartera, riesgo y simulación",
    status: "planned",
    summary:
      "Dimensionado de posiciones, combinación de estrategias y simulación de ejecución. " +
      "Especificado en el roadmap, sin implementar.",
    source: "docs/roadmap/master_roadmap.md",
  },
];
