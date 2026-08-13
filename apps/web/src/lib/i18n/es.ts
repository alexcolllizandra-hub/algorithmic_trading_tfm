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
    estudio: {
      label: "Cierre del estudio",
      description: "13 familias, corrección múltiple y holdout",
    },
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
    estudio: {
      title: "Cierre del estudio",
      subtitle:
        "Las 13 familias juzgadas juntas: todos los backtests, la corrección por comparaciones múltiples y el estado del holdout congelado.",
      que: "¿Qué muestra esta sección?",
      queAnswer:
        "Todos los resultados fuera de muestra del estudio (familia × activo) y la corrección aplicada al conjunto. El holdout aparece solo como estado: está bloqueado y sin auditar, así que no se publica ninguna de sus cifras.",
      porQue: "¿Por qué juzgarlas juntas?",
      porQueAnswer:
        "Cada familia probada añade una oportunidad de acertar por azar. Evaluar 13 hipótesis y quedarse con la mejor exige corregir el nivel de significación; si no, el mejor backtest siempre parecerá bueno.",
      comoInterpretar: "¿Cómo interpretar lo que ves?",
      comoInterpretarAnswer:
        "El retorno total ordena la tabla, pero el veredicto lo decide el p-valor ajustado. La dispersión entre semillas y la probabilidad de sobreajuste (PBO) indican cuánto de la cifra es ruido de selección.",
      queConcluir: "¿Qué se concluye?",
      queConcluirAnswer:
        "La conclusión textual del estudio se muestra literalmente en el panel de comparaciones múltiples, tal como la escribió el informe de cierre. Un resultado negativo riguroso es un resultado válido.",
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

  study: {
    unavailable: {
      title: "El artefacto consolidado del estudio no está disponible",
      detail:
        "La API responde 503 porque reports/study_closure/study_dashboard.json no existe. Constrúyalo con: uv run python scripts/build_study_dashboard.py",
      generic: "No se pudo cargar el cierre del estudio",
    },
    headline: {
      title: "Resultado del estudio",
      subtitle: "Cifras leídas del artefacto de cierre; ninguna está escrita en el frontend.",
      families: "Familias probadas",
      familiesSub: "Hipótesis independientes evaluadas",
      configurations: "Configuraciones evaluadas",
      configurationsSub: "Backtests ejecutados para producirlas",
      survivors: "Supervivientes tras corrección",
      survivorsSub: "Rechazos de Holm–Bonferroni a α = {alpha}",
      pbo: "Probabilidad de sobreajuste (PBO)",
      pboSub: "Bajo puro ruido se espera 0,5",
      units: "Unidades familia × activo × semilla",
      rowsLabel: "Filas familia × activo",
      generatedAt: "Artefacto generado",
      commit: "Commit de origen",
      bestFamily: "Familia con el p-valor crudo más bajo",
      bestFamilyNote:
        "Ser la mejor de trece no es evidencia de ventaja: es el resultado de haber elegido el máximo entre trece intentos. Por eso se corrige.",
    },
    table: {
      title: "Todos los backtests del estudio",
      subtitle:
        "Una fila por familia y activo, ordenable y filtrable. Seleccione una fila para abrir su detalle.",
      family: "Familia",
      gate: "Ronda",
      symbol: "Activo",
      totalReturn: "Retorno total",
      sharpe: "Sharpe",
      maxDrawdown: "Drawdown máximo",
      pValue: "p-valor crudo",
      holm: "p-valor Holm",
      bh: "p-valor BH",
      verdict: "Veredicto",
      seeds: "Semillas",
      filterGate: "Ronda",
      filterSymbol: "Activo",
      filterVerdict: "Veredicto",
      all: "Todas",
      open: "ver",
      empty: "Ninguna fila cumple estos filtros",
      shown: "{n} de {total} filas",
      sortAsc: "ascendente",
      sortDesc: "descendente",
      nullNote: "Un p-valor ajustado vacío significa que la corrección no cubría esa unidad.",
    },
    detail: {
      hypothesis: "Qué apuesta esta familia",
      loading: "Cargando el detalle de la familia…",
      empty: "Seleccione una familia en la tabla para ver su detalle",
      equityTitle: "Curva de equity: media de semillas y cada semilla",
      equitySubtitle:
        "La línea gruesa es lo que se sometió a prueba; las finas son la misma hipótesis con otra semilla de búsqueda.",
      seedTableTitle: "Resultado por semilla",
      seedSpread: "Dispersión entre semillas: de {min} a {max}",
      seedColumn: "Semilla",
      fanTitle: "Abanico de remuestreo",
      criteriaTitle: "Criterios de promoción",
      criteriaEmpty:
        "Esta familia no se puntuó en la rejilla de seis criterios: su ronda preguntaba otra cosa. Inventar una fila la representaría mal.",
      crossAssetTitle: "BTC frente a ETH",
      crossAssetNote:
        "Un efecto real no debería cambiar de signo entre dos activos tan acoplados. Si lo hace, lo más probable es que el signo lo fijara el ajuste, no el mercado.",
      crossAssetSingle: "Esta familia solo se evaluó sobre un activo.",
      buyAndHold: "Comprar y mantener (mediana)",
      gateNote: "Nota de la ronda",
      bars: "Barras fuera de muestra",
    },
    chart: {
      averageSeries: "Media de las semillas",
      seedSeries: "Semillas individuales ({n})",
      seedCaption:
        "Las curvas se decimaron para el dibujo; cada punto es la equity exacta en ese instante, así que el valor final es el valor final real.",
    },
    fan: {
      observedSeries: "Trayectoria observada",
      medianSeries: "Mediana remuestreada (p50)",
      innerBand: "Banda p25–p75",
      outerBand: "Banda p05–p95",
      barLabel: "Barra",
      method: "{method} · {paths} trayectorias · bloques de {block} barras · semilla {seed}",
      caption:
        "El abanico mide RIESGO DE TRAYECTORIA, no significancia estadística. Se construye remuestreando los propios retornos de la familia, así que arrastra consigo la media observada: muestra cuán distinto podría haber salido este mismo resultado, no si la ventaja es real. De eso responden el p-valor y la probabilidad de sobreajuste (PBO).",
      measuresLabel: "Lo que mide el abanico (campo measures)",
      terminalTitle: "Distribución del retorno final",
      terminalObserved: "Observado",
      probabilityPositive: "Trayectorias remuestreadas con retorno positivo",
    },
    criteria: {
      required: "requiere",
      vetoLabel: "Veto: mínimo de operaciones fuera de muestra",
      vetoTriggered: "activado",
      vetoClear: "no activado",
      vetoNote:
        "El veto no es un séptimo criterio: descarta la unidad por falta de operaciones, con independencia de su rendimiento.",
      gloss: {
        positive_total_return: "Retorno neto fuera de muestra positivo.",
        bootstrap_sharpe_ci_excludes_zero:
          "El intervalo de confianza bootstrap del Sharpe no incluye el cero.",
        survives_double_costs: "Sigue en positivo al duplicar comisiones y slippage.",
        beats_buy_and_hold: "Supera a comprar y mantener el activo.",
        survives_drop_top_trades: "Sigue en positivo si se eliminan las cinco mejores operaciones.",
        not_confined_to_one_fold: "El resultado no proviene de un único fold.",
      },
    },
    corrections: {
      title: "Corrección por comparaciones múltiples",
      subtitle: "Trece hipótesis juzgadas a la vez, no trece pruebas independientes.",
      conclusionTitle: "Conclusión del estudio (texto literal del informe de cierre)",
      holmTitle: "Holm–Bonferroni",
      bhTitle: "Benjamini–Hochberg",
      rejected: "Hipótesis rechazadas",
      adjustedTitle: "p-valores ajustados por familia",
      familyColumn: "Familia",
      pboTitle: "Probabilidad de sobreajuste (PBO)",
      pboNoiseLine: "Línea de ruido: 0,5",
      pboCaption:
        "PBO estima con qué frecuencia la configuración mejor en una partición queda por debajo de la mediana en la complementaria. Un valor próximo a 0,5 es lo esperable si la selección solo capta ruido.",
      pboUnavailable: "PBO no disponible en este artefacto",
      pboSplits: "Divisiones combinatorias",
      pboConfigurations: "Configuraciones comparadas",
      deflatedTitle: "Sharpe deflactado",
      deflatedCaption:
        "Descuenta del Sharpe observado lo que cabría esperar del mejor de N intentos. El número de intentos cambia la conclusión, así que se muestra para cada regla de conteo.",
      trials: "Intentos (N)",
      deflated: "Sharpe deflactado",
      spurious: "Probabilidad de que el mejor sea espurio",
      benchmark: "Sharpe de referencia por observación",
      observedSharpe: "Sharpe observado por observación",
      sensitivityTitle: "Sensibilidad al conteo de pruebas",
      sensitivityCaption:
        "Cuántas pruebas se declaran cambia el umbral de Bonferroni. La conclusión se mantiene con las cuatro reglas.",
      rule: "Regla de conteo",
      nTests: "Pruebas",
      threshold: "Umbral de Bonferroni",
      smallestP: "p-valor crudo más bajo",
      anySurvive: "¿Alguna sobrevive?",
      yes: "Sí",
      no: "No",
      criteriaByGate: "Criterio aplicado en cada ronda",
    },
    regimes: {
      title: "Análisis por régimen de mercado",
      subtitle:
        "¿Esconden las familias rechazadas un efecto confinado a un estado de mercado concreto?",
      banner:
        "Bloque EXPLORATORIO: estas celdas generan hipótesis, no validan resultados. Nada de aquí se promocionó ni puede citarse como hallazgo confirmado.",
      dimension: "Dimensión",
      regime: "Régimen",
      cells: "Celdas evaluadas",
      testable: "Celdas contrastables",
      excluded: "Celdas excluidas por tamaño",
      minBars: "Mínimo de barras por celda",
      survivors: "Celdas que sobreviven a la corrección",
      shareOfBars: "Peso en barras",
      filterFamily: "Familia",
      filterDimension: "Dimensión",
      empty: "Ninguna celda cumple estos filtros",
      noCandidate: "El bloque exploratorio no propuso ningún candidato condicionado por régimen.",
      candidateTitle: "Candidato propuesto por el bloque exploratorio",
    },
    holdout: {
      title: "Holdout final",
      subtitle:
        "Estado de la partición congelada. Esta sección informa del estado del holdout; no muestra ninguna lectura de él.",
      lockedTitle: "Holdout bloqueado: resultado no auditado",
      lockedBody:
        "La evaluación de la partición congelada está SIN AUDITAR, por lo que ninguna de sus cifras se publica aquí: ni retorno, ni Sharpe, ni drawdown, ni dispersión por semilla, ni comparación con comprar y mantener. La API puede seguir transportando esos campos; la interfaz no los renderiza.",
      period: "Ventana reservada",
      reason: "Motivo del aislamiento",
      requirementsTitle: "Requisitos para poder abrirlo y publicarlo",
      requirementsSubtitle:
        "Cada punto debe verificarse y quedar registrado antes de que cualquier cifra del holdout pueda citarse.",
      requirementsEmpty: "El payload no trae la lista de requisitos",
      requirementsEmptyHint:
        "Mientras el endpoint no envíe el campo requirements, no se muestra ninguna lista: no se inventan requisitos.",
      deliberateAbsence:
        "La ausencia de métricas es deliberada, no un error de carga ni un fallo de la API. Un holdout sin auditar no es un resultado, y mostrarlo como si lo fuera comprometería la conclusión de la tesis.",
    },
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
