/** Central Spanish copy for the perp-lab research platform (default language). */

export const es = {
  app: {
    name: "perp-lab",
    tagline: "plataforma de investigación",
    apiOnline: "API en línea",
    apiOffline: "API desconectada",
    runs: "runs",
  },

  nav: {
    overview: { label: "Visión general", description: "Fases, evidencia y advertencias" },
    datosEda: { label: "Datos y EDA", description: "Cobertura, cronología y hallazgos" },
    metodologia: { label: "Metodología", description: "Features, estrategias y validación" },
    experimentos: { label: "Experimentos", description: "Búsqueda RS vs GA" },
    resultados: { label: "Resultados", description: "Equity, drawdown y operaciones" },
    diagnostico: { label: "Diagnóstico", description: "Artefactos y sistema" },
  },

  phases: {
    data: { id: "data", label: "Datos y calidad", short: "Fase 1" },
    eda: { id: "eda", label: "EDA descriptivo", short: "Fase 1b" },
    features: { id: "features", label: "Features causales", short: "Fase 2" },
    strategies: { id: "strategies", label: "Estrategias interpretables", short: "Fase 3" },
    search: { id: "search", label: "Búsqueda RS/GA", short: "Fase 4" },
    validation: { id: "validation", label: "Walk-forward", short: "Fase 5" },
    holdout: { id: "holdout", label: "Holdout final (bloqueado)", short: "Fase 6" },
  },

  sections: {
    overview: {
      title: "Visión general de la investigación",
      subtitle:
        "Estado del pipeline reproducible para descubrir estrategias interpretables en futuros perpetuos BTC/ETH.",
      que: "¿Qué es esta plataforma?",
      queAnswer:
        "Un panel de solo lectura que expone artefactos verificables de cada experimento: datos, features, búsqueda y métricas fuera de muestra en desarrollo.",
      porQue: "¿Por qué importa?",
      porQueAnswer:
        "La tesis exige trazabilidad y aislamiento del holdout. Cada cifra debe poder rastrearse hasta un run, un fold y un candidato concretos.",
      comoInterpretar: "¿Cómo interpretar lo que ves?",
      comoInterpretarAnswer:
        "Las métricas mostradas provienen de ventanas walk-forward en la partición de desarrollo. No son el resultado final del holdout congelado.",
      queConcluir: "¿Qué concluir por ahora?",
      queConcluirAnswer:
        "Conclusión provisional: el pipeline está operativo y auditable; los resultados numéricos siguen siendo exploratorios hasta la evaluación final.",
    },
    datosEda: {
      title: "Datos y análisis exploratorio",
      subtitle:
        "Autenticidad de los datasets, línea temporal del desarrollo y hallazgos EDA clave.",
      que: "¿Qué datos se usan?",
      queAnswer:
        "Velas USDT-M de Binance (BTC/ETH), validadas con manifiestos SHA-256. La partición de desarrollo termina estrictamente antes del holdout.",
      porQue: "¿Por qué revisar la cobertura?",
      porQueAnswer:
        "Huecos, duplicados o filas que crucen el holdout invalidarían cualquier conclusión posterior sobre leakage o reproducibilidad.",
      comoInterpretar: "¿Cómo leer la cronología?",
      comoInterpretarAnswer:
        "El gráfico muestra el periodo de desarrollo, el subconjunto piloto usado en búsqueda, los folds train/val/test y el holdout bloqueado.",
      queConcluir: "¿Qué concluir del EDA?",
      queConcluirAnswer:
        "Los hallazgos EDA orientan el diseño (regímenes, costes, dependencia en colas) pero no seleccionan parámetros ni estrategias.",
    },
    metodologia: {
      title: "Metodología experimental",
      subtitle:
        "Flujo de datos, catálogo de features causales, familias de estrategia y validación walk-forward.",
      que: "¿Qué pipeline se sigue?",
      queAnswer:
        "Datos → features causales → regímenes (solo train) → señales interpretables → backtest con costes → búsqueda RS/GA con presupuesto equitativo.",
      porQue: "¿Por qué features causales?",
      porQueAnswer:
        "Cada predictor debe computarse solo con información pasada (rolling/expanding) para evitar look-ahead en selección y evaluación.",
      comoInterpretar: "¿Cómo leer la tabla de features?",
      comoInterpretarAnswer:
        "Observe la fórmula, inputs, lag y barras de warm-up. Un feature no causal invalida todo el candidato que lo use.",
      queConcluir: "¿Qué garantiza el walk-forward?",
      queConcluirAnswer:
        "Particiones cronológicas con purge y embargo; el ganador por fold se elige en validación y se puntúa una sola vez en test.",
    },
    experimentos: {
      title: "Experimentos de búsqueda",
      subtitle: "Comparación Random Search vs Algoritmo Genético bajo presupuesto compartido.",
      que: "¿Qué es un run?",
      queAnswer:
        "Un directorio de artefactos con configuración congelada, candidatos evaluados, folds, ganadores y equity de test por método.",
      porQue: "¿Por qué comparar RS y GA?",
      porQueAnswer:
        "Ambos optimizadores comparten el mismo presupuesto de evaluaciones; la comparación debe ser justa antes de inferir superioridad.",
      comoInterpretar: "¿Cómo leer convergencia y diversidad?",
      comoInterpretarAnswer:
        "La convergencia muestra el mejor fitness acumulado; la diversidad GA indica exploración del espacio. Ninguno sustituye métricas OOS.",
      queConcluir: "¿Qué concluir de un experimento?",
      queConcluirAnswer:
        "Priorice métricas agregadas OOS del ganador por fold y verifique checks de validez antes de cualquier narrativa.",
    },
    resultados: {
      title: "Resultados de rendimiento",
      subtitle: "Equity, drawdown y operaciones del candidato ganador en ventana de test.",
      que: "¿Qué métricas se muestran?",
      queAnswer:
        "Equity final, drawdown máximo, número de barras y operaciones para el fold y método seleccionados en la URL.",
      porQue: "¿Por qué usar summary y no puntos paginados?",
      porQueAnswer:
        "El endpoint de equity incluye un resumen de serie completa; las tarjetas deben usar ese summary para evitar errores de paginación.",
      comoInterpretar: "¿Cómo leer la tabla de folds?",
      comoInterpretarAnswer:
        "Cada fila es una ventana test OOS del ganador elegido en validación. Compare métodos solo con la misma definición de costes.",
      queConcluir: "¿Qué concluir de los resultados?",
      queConcluirAnswer:
        "Resultados exploratorios en desarrollo; no reportar como rendimiento final de tesis hasta abrir el holdout una sola vez.",
    },
    diagnostico: {
      title: "Diagnóstico y trazabilidad",
      subtitle: "Inspección de artefactos, manifiestos y estado del sistema.",
      que: "¿Qué artefactos existen?",
      queAnswer:
        "Manifiestos de datos, features, espacio de búsqueda, objetivo, entorno, git state y listado de archivos por run.",
      porQue: "¿Por qué inspeccionarlos?",
      porQueAnswer:
        "Permiten auditar reproducibilidad: hashes, seeds, configuración y candidatos fallidos sin acceder al código en vivo.",
      comoInterpretar: "¿Cómo leer el estado del sistema?",
      comoInterpretarAnswer:
        "Componentes marcados como implementados están en el repo; planned/reservados no implican despliegue en esta fase.",
      queConcluir: "¿Qué concluir del diagnóstico?",
      queConcluirAnswer:
        "Use esta sección para verificar integridad antes de citar cualquier número en la memoria de la tesis.",
    },
  },

  glossary: {
    holdout: {
      term: "Holdout congelado",
      definition:
        "Partición final ([holdout_start, cutoff)) abierta una sola vez para el informe definitivo. Hasta entonces, ningún código de desarrollo la carga.",
    },
    walkForward: {
      term: "Walk-forward",
      definition:
        "Validación cronológica con folds train/validation/test, purge y embargo entre ventanas.",
    },
    oos: {
      term: "Fuera de muestra (OOS)",
      definition:
        "Métricas en ventana test del fold, tras seleccionar el candidato solo con validación.",
    },
    pilot: {
      term: "Subconjunto piloto",
      definition:
        "Fracción del desarrollo usada en búsqueda piloto; el resto queda reservado para validación estructural.",
    },
    fairBudget: {
      term: "Presupuesto equitativo",
      definition:
        "RS y GA deben consumir el mismo número efectivo de evaluaciones únicas dentro del budget configurado.",
    },
    causalFeature: {
      term: "Feature causal",
      definition:
        "Predictor calculado exclusivamente con datos pasados (rolling/expanding), sin estadísticas de muestra completa.",
    },
    nextBar: {
      term: "Ejecución next-bar",
      definition:
        "La señal en barra t se ejecuta en la apertura de la barra t+1, con costes explícitos.",
    },
  },

  warnings: {
    exploratory:
      "Resultados exploratorios: métricas de validación/test en desarrollo únicamente. NO son rendimiento del holdout final y no deben citarse como resultado OOS definitivo de la tesis.",
    holdoutLocked:
      "El holdout congelado (ene–jun 2026) nunca se sirve por la plataforma ni informa decisiones de diseño.",
    devPartitionOnly:
      "Solo partición de desarrollo — observaciones del holdout congelado excluidas.",
    integrityMismatch:
      "Error de integridad: las métricas calculadas desde puntos paginados no coinciden con el summary de serie completa.",
    provisionalConclusion:
      "Conclusión provisional sujeta a la batería de robustez y a la evaluación final del holdout.",
    noHoldoutRuns:
      "No existen runs de holdout final en esta fase; cualquier métrica positiva sigue siendo preliminar.",
  },

  validity: {
    title: "Checks de validez del experimento",
    subtitle: "Verificaciones RS vs GA y reglas de integridad metodológica.",
    statusPass: "OK",
    statusWarn: "Aviso",
    statusFail: "Fallo",
    equalEvaluations: "Evaluaciones efectivas iguales",
    withinBudget: "Dentro del presupuesto",
    noHoldoutLeakage: "Sin leakage de holdout",
  },

  contextBar: {
    run: "Run",
    method: "Método",
    fold: "Fold",
    candidate: "Candidato",
    interval: "Intervalo",
    period: "Periodo test",
  },

  timeline: {
    title: "Línea temporal del experimento",
    development: "Desarrollo",
    pilotUsed: "Piloto usado",
    pilotUnused: "Piloto no usado",
    train: "Train",
    validation: "Validación",
    test: "Test",
    holdout: "Holdout (bloqueado)",
    purge: "Purge",
    embargo: "Embargo",
  },

  trades: {
    long: "Largo",
    short: "Corto",
    flat: "Plano",
    exportCsv: "Exportar CSV",
  },

  common: {
    loading: "Cargando…",
    noData: "Sin datos",
    selectRun: "Seleccione un run",
    viewAll: "Ver galería completa",
    keyFindings: "Hallazgos clave",
    fullGallery: "Galería completa EDA",
    howToRead: "Cómo leer esta sección",
    expand: "Expandir",
    collapse: "Contraer",
  },
} as const;

export type EsCopy = typeof es;
