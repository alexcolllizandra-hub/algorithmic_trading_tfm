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
    guia: { label: "Guía", description: "Recorrido didáctico en 13 paneles" },
    datosEda: { label: "Datos y EDA", description: "Cobertura, cronología y hallazgos" },
    metodologia: { label: "Metodología", description: "Features, estrategias y validación" },
    experimentos: { label: "Experimentos", description: "Búsqueda RS vs GA" },
    resultados: {
      label: "Resultados y cierre",
      description: "13 familias, corrección múltiple y holdout",
    },
    estudio: {
      label: "Cierre del estudio",
      description: "13 familias, corrección múltiple y holdout",
    },
    estrategias: {
      label: "Estrategias",
      description: "Todas las familias: equity y métricas reales",
    },
    laboratorio: {
      label: "Laboratorio",
      description: "Construya y ejecute una estrategia sobre los datos reales",
    },
    cuadernos: {
      label: "Cuadernos",
      description: "Los 8 notebooks: figuras congeladas y mapa a la memoria",
    },
    diagnostico: { label: "Diagnóstico", description: "Artefactos y sistema" },
  },

  navGroups: {
    start: "Inicio",
    learn: "Aprende",
    study: "El estudio",
    explore: "Explora",
    system: "Sistema",
  },

  phases: {
    data: { id: "data", label: "Datos y calidad", short: "Fase 1" },
    eda: { id: "eda", label: "EDA descriptivo", short: "Fase 1b" },
    features: { id: "features", label: "Features causales", short: "Fase 2" },
    strategies: { id: "strategies", label: "Estrategias interpretables", short: "Fase 3" },
    search: { id: "search", label: "Búsqueda RS/GA", short: "Fase 4" },
    validation: { id: "validation", label: "Walk-forward", short: "Fase 5" },
    holdout: { id: "holdout", label: "Holdout final (lectura retenida)", short: "Fase 6" },
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
    guia: {
      title: "Guía del estudio, paso a paso",
      subtitle:
        "Trece paneles en orden, de la pregunta más simple a la técnica. No hace falta saber finanzas cuantitativas para seguirlos.",
      que: "¿Qué es este modo guiado?",
      queAnswer:
        "Un recorrido didáctico por la tesis: qué se preguntó, con qué datos, cómo se probó y por qué se concluyó lo que se concluyó. Cada panel explica un concepto y, cuando existe, muestra la cifra real que le corresponde.",
      porQue: "¿Por qué existe este modo?",
      porQueAnswer:
        "Un resultado negativo solo es convincente si se entiende el procedimiento que lo produjo. Esta guía hace visible ese procedimiento sin pedir vocabulario previo.",
      comoInterpretar: "¿Cómo distinguir dibujo de resultado?",
      comoInterpretarAnswer:
        "Todo gráfico didáctico lleva la etiqueta «ejemplo ilustrativo» y valores inventados. Las cifras del estudio llegan de la API y, si una no está disponible, se muestra un estado en su lugar, nunca un cero.",
      queConcluir: "¿Qué se puede concluir aquí?",
      queConcluirAnswer:
        "La conclusión textual del informe de cierre se cita literalmente en el panel 13. La partición reservada se abrió una vez y su lectura quedó retenida a la espera de auditoría: esta página explica qué es, pero no muestra ninguna cifra suya.",
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
        "El gráfico muestra el periodo de desarrollo, el subconjunto piloto usado en búsqueda, los folds train/val/test y la partición reservada.",
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
      title: "Resultados y cierre del estudio",
      subtitle:
        "Las 13 familias juzgadas juntas: todos los backtests, la corrección por comparaciones múltiples y el estado del holdout congelado.",
      que: "¿Qué muestra esta sección?",
      queAnswer:
        "Todos los resultados fuera de muestra del estudio (familia × activo) y la corrección aplicada al conjunto. El holdout aparece solo como estado: se abrió una vez y su lectura sigue sin auditar, así que no se publica ninguna de sus cifras.",
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
        "Partición final ([holdout_start, cutoff)) que se abre una sola vez para el informe definitivo y que ningún código de desarrollo carga. Se abrió sobre un candidato declarado de antemano; su lectura permanece retenida mientras la auditoría de procedencia siga pendiente.",
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
      "La plataforma nunca sirve observaciones del holdout (ene–jun 2026) ni deja que informe decisiones de diseño. Su única lectura quedó retenida a la espera de auditoría.",
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
    holdout: "Holdout (reservado)",
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
      lockedTitle: "Holdout abierto una vez: resultado no auditado",
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

  guia: {
    toc: {
      title: "Índice de la guía",
      navLabel: "Índice de los 13 paneles de la guía",
      progress: "Panel {n} de {total}",
      jump: "Ir al panel {n}: {title}",
      progressLabel: "Progreso de lectura de la guía",
    },

    parts: {
      viendo: "Qué estoy viendo",
      importa: "Por qué importa",
      interpreta: "Cómo se interpreta",
      conclusion: "Conclusión obtenida",
    },

    illustrative: {
      badge: "ejemplo ilustrativo",
      note: "Dibujo didáctico con valores inventados para explicar el concepto. No es un resultado del estudio ni una cifra de la API.",
    },

    data: {
      loading: "Cargando las cifras del estudio…",
      unavailableTitle: "Cifras del estudio no disponibles",
      unavailableHint:
        "El panel muestra un estado en lugar de un número: aquí no se inventa ningún valor ni se rellena con ceros.",
      notServedHint:
        "Este dato no lo publican los endpoints del estudio, así que se declara como estado en vez de mostrar una cifra aproximada.",
    },

    legend: {
      train: "Entrenamiento",
      val: "Validación",
      test: "Test fuera de muestra",
      holdout: "Holdout reservado (lectura retenida)",
      development: "Desarrollo (donde se investiga)",
      purge: "Purge: barras descartadas",
      embargo: "Embargo: espera adicional",
      signal: "Señal calculada en la barra t",
      exec: "Ejecución en t+1 con costes",
      future: "Información que aún no existía",
      neutral: "Resto de la serie",
      learned: "Parámetros ya aprendidos",
      refit: "Reajuste con datos nuevos",
      rule: "Regla fija, sin aprender nada",
      config: "Otra configuración de la misma regla",
      decision: "Decisión de diseño posterior",
      window: "Ventana de cálculo del indicador",
    },

    series: {
      price: "Precio",
      average: "Media móvil de las últimas barras",
      observations: "Observaciones",
      overfit: "Regla ajustada al ruido",
      trend: "Regla que ignora el ruido",
      inSample: "Error dentro de la muestra",
      outSample: "Error fuera de la muestra",
    },

    pdots: {
      axisStart: "p = 0",
      axisEnd: "p = 1",
      threshold: "Umbral α (línea vertical)",
      rejected: "Cruza el umbral",
      notRejected: "No cruza el umbral",
      smallest: "El más bajo del conjunto",
    },

    bars: {
      gross: "Retorno bruto de la regla",
      fees: "Tras comisiones, en cada lado",
      slippage: "Tras comisiones y slippage",
      net: "Retorno neto, también tras funding",
      valBest: "Mejor configuración en validación",
      oosSame: "La misma configuración, fuera de muestra",
      attemptsMax: "El mayor de los intentos",
      attemptsMean: "La media de los intentos",
      attemptsMin: "El menor de los intentos",
      pboA: "Posición en la mitad donde ganó",
      pboB: "Posición de la misma en la mitad complementaria",
      dsrObserved: "Sharpe observado del mejor",
      dsrExpected: "Máximo que el azar produce con N intentos",
      dsrDeflated: "Lo que queda al descontarlo",
    },

    panels: {
      pregunta: {
        title: "¿Qué pregunta intenta responder esto?",
        viendo:
          "El punto de partida del estudio: una sola pregunta científica y el recuento de intentos que se hicieron para responderla. Las dos cifras vienen del artefacto de cierre, no están escritas en esta página.",
        importa:
          "La pregunta no es «¿funciona esta estrategia?», sino «de todo lo que probamos, ¿funcionó algo?». Son preguntas distintas: la segunda incluye los intentos fallidos, y por eso exige un listón estadístico más alto.",
        interpreta:
          "Lea las dos cifras juntas: familias de estrategia probadas y configuraciones evaluadas. Cuantos más intentos, más fácil es que alguno parezca bueno por pura casualidad.",
        conclusion:
          "El estudio se compromete con la pregunta amplia y declara cuántos intentos hizo para contestarla. Ese recuento es la base de todo lo que viene después.",
      },
      datos: {
        title: "¿Qué datos usa?",
        viendo:
          "Los activos, la temporalidad y la longitud de la serie evaluada tal como los declara la API, junto con el estado de la partición congelada.",
        importa:
          "Si los datos no son reales, completos y verificables, nada de lo que venga después significa algo. Y si el periodo final se usa durante el desarrollo, el resultado deja de ser una prueba.",
        interpreta:
          "El histórico se parte en dos: desarrollo, donde se investiga, y holdout congelado, que no se toca. El diagrama es un dibujo con proporciones inventadas; las cifras reales son las tarjetas de arriba.",
        conclusion:
          "Los datos son velas de futuros perpetuos USDT-M sobre dos activos muy acoplados, y la partición final quedó fuera del desarrollo: todo lo que se juzga aquí ocurre en desarrollo.",
      },
      estrategia: {
        title: "¿Qué es una estrategia?",
        viendo:
          "La definición de estrategia que usa el estudio y una hipótesis real: el texto que la API guarda para una de las familias probadas.",
        importa:
          "Una estrategia no es una opinión sobre el mercado: es una regla que, ante los mismos datos, siempre toma la misma decisión. Lo que no se puede escribir como regla no se puede probar ni refutar.",
        interpreta:
          "Cada familia es una hipótesis con parámetros libres, por ejemplo cuántas barras mirar atrás. La regla es fija; los parámetros son lo que la búsqueda ajusta.",
        conclusion:
          "Todas las familias del estudio son interpretables: se pueden leer, discutir y refutar. Es un requisito de la tesis, no una limitación técnica.",
      },
      backtest: {
        title: "¿Qué es un backtest?",
        viendo:
          "Cómo una regla se convierte en una serie de resultados: la señal se calcula al cerrar una barra y la operación se ejecuta en la siguiente, pagando costes.",
        importa:
          "El backtest es la única forma de poner una regla a prueba sin arriesgar dinero, y también la forma más fácil de engañarse. La diferencia está en los detalles de ejecución.",
        interpreta:
          "Fíjese en el desplazamiento: decisión en la barra t, ejecución en la apertura de t+1. Si la ejecución ocurriese en la misma barra que la decisión, el backtest usaría un precio que todavía no se conocía.",
        conclusion:
          "El estudio ejecuta a la barra siguiente y con costes explícitos. Esa elección hace los números más pequeños y más creíbles.",
      },
      particiones: {
        title: "¿Qué son train, validación y fuera de muestra?",
        viendo:
          "El reparto del tiempo en cuatro tramos con papeles distintos: entrenamiento, validación, test fuera de muestra y holdout congelado.",
        importa:
          "Ajustar y evaluar con los mismos datos garantiza un buen resultado y no dice nada. Separar los tramos es lo que convierte una cifra en una prueba.",
        interpreta:
          "Los tramos van en orden cronológico, nunca al azar: el pasado entrena y el futuro juzga. Cada tramo sirve para una sola cosa: train ajusta, validación elige, test puntúa una única vez.",
        conclusion:
          "El reparto es cronológico y el holdout quedó al margen del desarrollo, así que las cifras de los paneles siguientes son de test dentro de la partición de desarrollo.",
      },
      walkForward: {
        title: "¿Qué es la validación walk-forward?",
        viendo:
          "El mismo reparto repetido varias veces avanzando en el tiempo. Cada repetición se llama fold.",
        importa:
          "Un único corte train/test puede salir bien o mal según dónde cayera la línea. Repetirlo hacia delante mide si la regla aguanta en varios periodos distintos, no solo en uno afortunado.",
        interpreta:
          "Cada fila del diagrama es un fold: entrena con el pasado, elige con su validación y puntúa con un test que no había visto. Los tramos de test de todos los folds se concatenan para juzgar la familia.",
        conclusion:
          "El estudio valida con walk-forward y busca los parámetros de forma independiente dentro de cada fold, para que la elección de un fold no pueda mirar el test de otro.",
      },
      purgeEmbargo: {
        title: "¿Qué son el purge y el embargo?",
        viendo:
          "Dos huecos deliberados alrededor de cada corte: el purge descarta las barras cuyo cálculo cruza la línea y el embargo añade una espera después de ella.",
        importa:
          "Los indicadores mezclan barras vecinas. Sin huecos, las últimas barras de entrenamiento comparten información con las primeras de test, y esa coincidencia se lee como acierto.",
        interpreta:
          "La banda descartada no se usa ni para entrenar ni para evaluar: se tira. Cuantas más barras mire hacia atrás un indicador, más ancho tiene que ser el hueco.",
        conclusion:
          "El protocolo aplica purge y embargo en cada corte. Sin ellos, cualquier resultado positivo sería sospechoso por construcción.",
      },
      semillasFolds: {
        title: "¿Qué son las semillas y los folds?",
        viendo:
          "El mismo experimento repetido con distintas semillas de búsqueda, para una familia real que puede elegir aquí: la curva media, cada semilla por separado y la dispersión entre ellas.",
        importa:
          "La búsqueda de parámetros arranca en un punto aleatorio. Si al cambiar ese punto arbitrario el resultado cambia de signo, lo que se medía era la suerte del arranque, no la idea.",
        interpreta:
          "La línea gruesa es la media de las semillas y las finas son la misma hipótesis con otro arranque. Cuanto más se abren las finas, menos informativa es la gruesa.",
        conclusion:
          "Las semillas se tratan como réplicas de una misma hipótesis y se promedian, en lugar de contarlas como pruebas independientes. Los folds sí son periodos distintos y se concatenan.",
      },
      costes: {
        title: "¿Qué costes se aplican?",
        viendo:
          "El camino del retorno bruto al neto: comisión y slippage en cada lado de la operación, y el funding del perpetuo mientras la posición sigue abierta.",
        importa:
          "Casi cualquier regla parece rentable sin costes. Los costes son el filtro que separa una idea de una operación que se podría haber ejecutado de verdad.",
        interpreta:
          "La escalera es un dibujo con cifras inventadas: muestra el orden de las restas, no su magnitud. La tabla, en cambio, es real: cuenta cuántas semillas siguen en positivo al duplicar los costes.",
        conclusion:
          "El estudio backtestea con costes explícitos y, además, exige que un resultado sobreviva a duplicarlos. Los parámetros exactos del modelo de costes no los publica este endpoint.",
      },
      estrategiasProbadas: {
        title: "¿Qué estrategias se probaron?",
        viendo:
          "El inventario completo de familias del estudio, con la ronda en la que se probó cada una, el activo y la hipótesis que apostaba.",
        importa:
          "El inventario es el denominador del estudio. Publicar solo la mejor familia y callar las demás es exactamente la práctica que invalida un resultado.",
        interpreta:
          "Cada fila es una hipótesis distinta, no una variante de la anterior. La columna de ronda indica en qué fase se probó y con qué criterio de promoción.",
        conclusion:
          "Se declara todo lo probado, no solo lo que sobrevivió. Ese recuento es el que alimenta la corrección por comparaciones múltiples del panel siguiente.",
      },
      resultados: {
        title: "¿Qué resultados se obtuvieron?",
        viendo:
          "Todos los resultados fuera de muestra en una tabla ordenable y, debajo, la corrección aplicada al conjunto: Holm, Benjamini–Hochberg, PBO y Sharpe deflactado.",
        importa:
          "Un p-valor crudo responde a «¿es raro este resultado?». Con trece familias probadas, la pregunta correcta es «¿es raro el mejor de trece?», y esa exige mover el umbral.",
        interpreta:
          "Ordene por retorno y después mire el p-valor ajustado: son dos lecturas distintas de la misma fila. El veredicto lo decide el ajustado, nunca el retorno.",
        conclusion:
          "Todas las cifras se leen del artefacto de cierre, incluida la conclusión escrita del informe. Ninguna está escrita a mano en esta página.",
      },
      rechazo: {
        title: "¿Por qué una estrategia que parece rentable puede rechazarse?",
        viendo:
          "Las tres razones por las que un backtest positivo puede no ser una ventaja: fue el mejor de muchos intentos, no se repite en el segundo activo y no se sostiene al partir la muestra.",
        importa:
          "El máximo de una lista de intentos siempre parece bueno, aunque ninguno tenga ventaja. Sin corregir por el número de intentos, «el mejor backtest» mide cuántos backtests se hicieron.",
        interpreta:
          "Compare la misma familia en los dos activos: un efecto estructural no debería cambiar de signo entre mercados tan acoplados. Y lea el PBO contra 0,5, que es lo que produce el puro ruido.",
        conclusion:
          "Rentable en el backtest y con ventaja real no son lo mismo. El estudio rechaza sobre esa distinción, no sobre el signo del retorno.",
      },
      conclusion: {
        title: "¿A qué conclusión científica se llega?",
        viendo:
          "La conclusión textual del informe de cierre y el estado de la partición congelada. Esta guía no muestra ninguna lectura del holdout.",
        importa:
          "Un resultado negativo riguroso es un resultado válido; un resultado positivo obtenido mirando el holdout no lo es. Cerrar bien forma parte de la conclusión.",
        interpreta:
          "Lea la conclusión por lo que es: una afirmación sobre este universo de estrategias, este modelo de costes y este horizonte. No es una afirmación sobre el trading algorítmico en general.",
        conclusion:
          "Bajo este modelo de costes y en esta clase de instrumento, el estudio no encuentra ventaja. El holdout se abrió una vez y su lectura queda retenida a la espera de auditoría; la conclusión no depende de ella.",
      },
    },

    figures: {
      developmentHoldout: {
        title: "Cómo se parte el histórico",
        caption:
          "Proporciones inventadas. Lo importante es que el tramo congelado está al final y no participa en la investigación.",
        rows: { serie: "Serie histórica" },
      },
      nextBar: {
        title: "Señal en t, ejecución en t+1",
        caption:
          "La flecha del tiempo va de izquierda a derecha. La decisión nunca se ejecuta en la misma barra en la que se toma.",
        rows: { barras: "Barras consecutivas" },
      },
      splits: {
        title: "Los cuatro tramos y su papel",
        caption:
          "El orden es cronológico y no se altera nunca. Los tamaños del dibujo no representan los del estudio.",
        rows: { reparto: "Reparto del tiempo" },
      },
      walkForward: {
        title: "Un fold por fila, avanzando en el tiempo",
        caption:
          "Cuatro folds de ejemplo. El número real de folds lo fija la configuración del experimento, no este dibujo.",
        foldLabel: "Fold {n}",
      },
      purgeEmbargo: {
        title: "El mismo corte, sin y con huecos",
        caption:
          "Arriba, entrenamiento y test se tocan y comparten información. Abajo, las barras del solape se descartan y se añade una espera.",
        rows: { sin: "Sin purge ni embargo", con: "Con purge y embargo" },
      },
      costLadder: {
        title: "Del retorno bruto al neto",
        caption:
          "Cifras inventadas para ver el orden de las restas: comisión y slippage por lado, y funding mientras la posición está abierta.",
      },
      strategyRule: {
        title: "Una regla, no una opinión",
        caption:
          "Precio inventado y su media móvil. La regla dice «largo mientras el precio esté por encima»: ante los mismos datos, siempre decide lo mismo.",
      },
      curveFitting: {
        title: "Ajustar la forma frente a ajustar el ruido",
        caption:
          "Los puntos son observaciones inventadas. La línea quebrada pasa por todas y no sirve fuera de la muestra; la suave ignora el ruido.",
      },
      overfitting: {
        title: "La tijera del sobreajuste",
        caption:
          "Al aumentar la complejidad, el error dentro de la muestra sigue bajando mientras el de fuera empieza a subir. El cruce marca el sobreajuste.",
      },
      multipleTesting: {
        title: "Trece p-valores, un umbral",
        caption:
          "Cada punto es una prueba inventada. Con suficientes pruebas, la más baja acaba pareciendo significativa aunque ninguna tenga ventaja.",
      },
      holm: {
        title: "Los mismos p-valores, ajustados por Holm",
        caption:
          "Holm exige umbrales cada vez más laxos según el orden. Sobre los p-valores inventados de arriba, ninguno sobrevive.",
      },
      bh: {
        title: "Los mismos p-valores, ajustados por Benjamini–Hochberg",
        caption:
          "BH es más permisivo que Holm porque controla la proporción de falsos descubrimientos, no la probabilidad de tener uno.",
      },
      pHacking: {
        title: "Intentar hasta que salga",
        caption:
          "Mismos datos, análisis retocado una y otra vez. El p-valor del último intento no significa lo que dice, porque no fue el único.",
      },
      dataMining: {
        title: "Barrer el espacio de patrones",
        caption:
          "Cada punto es una combinación inventada que se probó. Encontrar la mejor no es un hallazgo si no se dice cuántas se miraron.",
      },
      selectionBias: {
        title: "El máximo no es un resultado cualquiera",
        caption:
          "Intentos inventados sin ventaja: su media es cero, pero el mayor siempre es positivo. Informar solo del mayor convierte ruido en hallazgo.",
      },
      hyperparameter: {
        title: "Elegir por validación y comprobar fuera",
        caption:
          "La mejor configuración en validación no es la mejor fuera de muestra. La diferencia inventada es el precio de haber elegido.",
      },
      fineTuning: {
        title: "Dos cosas distintas que se confunden",
        caption:
          "Arriba, fine-tuning: hay parámetros aprendidos y se reajustan. Abajo, optimización de hiperparámetros: la regla es fija y solo cambia su configuración.",
        rows: {
          ft: "Fine-tuning: modelo ya entrenado",
          hp: "Hiperparámetros: regla fija",
        },
      },
      leakage: {
        title: "Un valor que no podía conocerse",
        caption:
          "Arriba, la ventana de cálculo cruza el presente y toma información futura. Abajo, la misma ventana mira solo hacia atrás.",
        rows: { leak: "Ventana con fuga", ok: "Ventana causal" },
      },
      snooping: {
        title: "Mirar el test y volver atrás",
        caption:
          "Arriba, el test se consulta y luego se cambia el diseño: deja de ser fuera de muestra. Abajo, se abre una sola vez, al final.",
        rows: { mirado: "Test consultado antes de decidir", limpio: "Test abierto una sola vez" },
      },
      pbo: {
        title: "Mejor en una mitad, mediano en la otra",
        caption:
          "Posición relativa inventada de la misma configuración en dos mitades complementarias de la muestra. Si el orden no se mantiene, la selección no informaba.",
      },
      deflated: {
        title: "Descontar el mejor de N intentos",
        caption:
          "Sharpe inventado: el observado, lo que produciría por azar el mejor de N intentos, y lo que queda al restar el segundo del primero.",
      },
    },

    labels: {
      question: "La pregunta que responde el estudio",
      questionText: "«De todo lo que probamos, ¿funcionó algo?»",
      assets: "Activos evaluados",
      timeframe: "Temporalidad",
      oosBars: "Barras fuera de muestra (fila más larga)",
      holdoutState: "Estado del holdout",
      holdoutOpenedFalse:
        "Este artefacto se generó sobre desarrollo y no incorpora ninguna lectura de la partición reservada, así que no hay cifras suyas que mostrar aquí.",
      exampleFamily: "Familia de ejemplo (la de p-valor crudo más bajo)",
      foldsNotServed: "Número de folds del experimento",
      purgeNotServed: "Barras de purge y embargo",
      costModelNotServed: "Parámetros del modelo de costes",
      seeMethodology: "Consulte Metodología para el detalle del protocolo.",
      chooseFamily: "Familia que se muestra",
      costCriterionTitle: "Criterio real: sigue en positivo al duplicar los costes",
      costCriterionSubtitle:
        "Una fila por unidad familia × activo que puntuó este criterio, con las semillas que lo superan.",
      costCriterionEmpty: "Ninguna familia de este artefacto puntuó el criterio de costes dobles",
      criterionPassed: "Semillas que lo superan",
      criterionRequired: "Semillas exigidas",
      inventoryTitle: "Inventario de familias probadas",
      inventorySubtitle:
        "Todo lo que entró en el registro científico, no solo lo que sobrevivió a la corrección.",
      resultsNote:
        "Al seleccionar una fila cambia también la familia que muestra el panel 8, para que pueda mirar sus semillas.",
      reasonsTitle: "Las tres razones del rechazo",
      reasonBest: "Fue el mejor de muchos intentos",
      reasonBestText:
        "El p-valor crudo no descuenta cuántas familias se probaron; el ajustado, sí. Compare las dos columnas en la tabla del panel 11.",
      reasonAsset: "No se repite en el segundo activo",
      reasonAssetText:
        "La misma hipótesis, medida sobre dos mercados muy acoplados, debería conservar el signo. Las tarjetas de abajo son cifras reales de la API.",
      reasonSplit: "No se sostiene al partir la muestra",
      reasonSplitText:
        "El PBO mide con qué frecuencia la configuración ganadora en una mitad cae por debajo de la mediana en la otra. La referencia de ruido es 0,5.",
      spuriousTitle: "Probabilidad de que el mejor sea espurio",
      spuriousRule: "Regla de conteo de intentos",
      regimeQuestion:
        "¿Y si el efecto existiera solo en un estado de mercado concreto? Esa pregunta se contestó en un bloque explícitamente exploratorio, con su propia corrección interna.",
      holdoutWithheld:
        "La lectura del holdout queda retenida a la espera de auditoría. Esta guía explica qué es la partición reservada y por qué su cifra no se publica, pero no muestra ninguna de sus métricas.",
    },

    concepts: {
      title: "Conceptos, uno a uno",
      subtitle:
        "Las trampas que puede esconder un backtest y las herramientas que las detectan. Cada tarjeta lleva un dibujo didáctico, no un resultado.",
      fineTuningTitle: "Aclaración necesaria: fine-tuning no es optimización de hiperparámetros",
      fineTuningBody:
        "Fine-tuning significa reajustar un modelo YA ENTRENADO: se parte de unos parámetros aprendidos y se siguen actualizando con datos nuevos. Es lo que se hace con una red neuronal preentrenada.",
      fineTuningBody2:
        "Cambiar un lookback, mover un stop o subir el umbral de un RSI NO es fine-tuning: es optimización de hiperparámetros, porque no reajusta nada aprendido, sino que vuelve a evaluar la misma regla fija con otra configuración. En este estudio no hay fine-tuning, porque no hay ningún modelo entrenado que reajustar: hay búsqueda de hiperparámetros con Random Search y con un algoritmo genético.",
      whatIs: "Qué es",
      whyMatters: "Por qué importa aquí",
      items: {
        mineria: {
          term: "Minería de datos (data mining)",
          plain:
            "Buscar patrones probando muchas combinaciones sobre los mismos datos hasta que alguna destaca.",
          matters:
            "No es malo en sí: así se generan hipótesis. Se vuelve un problema cuando el patrón encontrado se presenta como descubrimiento sin descontar cuántas combinaciones se probaron.",
        },
        snooping: {
          term: "Data snooping (espiar los datos)",
          plain:
            "Tomar decisiones de diseño usando información del tramo que debía servir para evaluar, aunque solo se haya mirado.",
          matters:
            "Basta con haber visto el resultado del test y volver atrás a cambiar algo. Ese tramo deja de ser fuera de muestra en el momento en que informa una decisión.",
        },
        curva: {
          term: "Ajuste a la curva (curve fitting)",
          plain:
            "Retocar la regla hasta que reproduce la forma exacta del histórico, ruido incluido.",
          matters:
            "La curva ajustada explica el pasado casi a la perfección y no dice nada del futuro. La señal de alarma es una mejora que solo aparece con parámetros muy finos.",
        },
        hiper: {
          term: "Optimización de hiperparámetros",
          plain:
            "Elegir los valores de los parámetros libres de una regla fija: cuántas barras mirar atrás, dónde poner el stop, qué umbral usar.",
          matters:
            "Es exactamente lo que hacen Random Search y el algoritmo genético en este estudio. Cada configuración probada es un intento más que hay que contar.",
        },
        fineTuning: {
          term: "Fine-tuning (reajuste fino)",
          plain:
            "Reajustar un modelo YA ENTRENADO: se parte de parámetros aprendidos y se siguen actualizando con datos nuevos.",
          matters:
            "Cambiar un lookback, un stop o un umbral de RSI NO es fine-tuning: es optimización de hiperparámetros. En este estudio no hay fine-tuning, porque no hay modelo entrenado que reajustar.",
        },
        sobreajuste: {
          term: "Sobreajuste (overfitting)",
          plain: "Aprender el ruido del histórico en lugar de su estructura.",
          matters:
            "Se reconoce por la tijera: el error dentro de la muestra sigue bajando mientras el de fuera empieza a subir. Lo que mejora es la memoria, no la capacidad de generalizar.",
        },
        multiples: {
          term: "Comparaciones múltiples (multiple testing)",
          plain:
            "Al probar muchas hipótesis a la vez, la probabilidad de que alguna parezca significativa por azar crece con el número de pruebas.",
          matters:
            "Con veinte pruebas y un umbral de 0,05 se espera una «significativa» aunque ninguna tenga ventaja. Trece familias exigen corregir el umbral una vez, sobre todo el conjunto.",
        },
        seleccion: {
          term: "Sesgo de selección (selection bias)",
          plain: "Informar del mejor de varios resultados como si fuera un resultado cualquiera.",
          matters:
            "El máximo de una muestra siempre supera a su media. Publicar el máximo sin decir de cuántos sale convierte ruido en hallazgo.",
        },
        pHacking: {
          term: "P-hacking",
          plain:
            "Repetir el análisis con variantes —otro periodo, otro filtro, otra métrica— hasta que el p-valor baja del umbral.",
          matters:
            "El p-valor final ya no significa lo que dice, porque el umbral no se cruzó una vez: se cruzó en el intento número N y solo se publicó ese.",
        },
        leakage: {
          term: "Fuga de información (leakage)",
          plain:
            "Que un valor usado para decidir contenga información que en ese momento no existía.",
          matters:
            "Suele ser sutil: una media calculada sobre toda la muestra, una etiqueta que cruza el corte, una ejecución en la misma barra que la señal. Cualquiera de las tres infla el resultado.",
        },
        pbo: {
          term: "PBO (probabilidad de sobreajuste del backtest)",
          plain:
            "Con qué frecuencia la configuración que gana en una mitad de la muestra queda por debajo de la mediana en la mitad complementaria.",
          matters:
            "Bajo puro ruido se espera 0,5. Un valor cercano a 0,5 indica que el proceso de selección no está capturando información, solo reordenando azar.",
        },
        deflated: {
          term: "Sharpe deflactado (Deflated Sharpe Ratio)",
          plain:
            "El Sharpe observado descontando lo que produciría por casualidad el mejor de N intentos.",
          matters:
            "El número de intentos declarado cambia el resultado, así que se informa para varias reglas de conteo en lugar de quedarse con la más favorable.",
        },
        holm: {
          term: "Corrección de Holm–Bonferroni",
          plain:
            "Ajusta los p-valores para controlar la probabilidad de cometer al menos un falso positivo en todo el conjunto de pruebas.",
          matters:
            "Ordena los p-valores de menor a mayor y aplica umbrales cada vez más laxos. Es conservadora: lo que sobrevive a Holm sobrevive a casi todo.",
        },
        bh: {
          term: "Corrección de Benjamini–Hochberg",
          plain:
            "Ajusta los p-valores para controlar la proporción esperada de falsos positivos entre los rechazos, no la probabilidad de tener uno.",
          matters:
            "Es más permisiva que Holm: acepta algún falso positivo a cambio de detectar más efectos reales. Si nada sobrevive tampoco a BH, la conclusión negativa es más sólida.",
        },
      },
    },
  },

  explorer: {
    title: "Explorador de estrategias",
    subtitle:
      "Quince de las dieciséis familias con estudio multi-semilla completo (macro_event_brake, de la ronda S3, no está exportada aquí): curvas de equity fuera de muestra reales y el conjunto íntegro de métricas, por activo y por semilla.",
    que: "¿Qué muestra esta sección?",
    queAnswer:
      "Cada familia evaluada, con la curva de equity de sus diez semillas sobre la ventana out-of-sample concatenada y todas las métricas que calculó la batería de robustez. Nada está simulado: cada punto es la equity exacta de ese instante.",
    porQue: "¿Por qué enseñar estrategias rechazadas?",
    porQueAnswer:
      "Porque el hallazgo del estudio es precisamente que parecer rentable y tener ventaja real son cosas distintas. Aquí se ve, familia a familia, cuánto varía el resultado con la semilla y contra comprar y mantener.",
    comoInterpretar: "¿Cómo leer las curvas?",
    comoInterpretarAnswer:
      "La línea gruesa es la media de las semillas; las finas, cada semilla por separado. Cuanto más se abren, más depende el resultado del azar del arranque de la búsqueda. Compare siempre contra comprar y mantener.",
    queConcluir: "¿Qué NO concluir aquí?",
    queConcluirAnswer:
      "Que una curva suba no la convierte en ventaja: el veredicto lo decidió la corrección estadística del cierre, no el retorno. Ninguna familia está promovida y ninguna cifra es rendimiento del holdout.",
    pickFamily: "Familia",
    pickAsset: "Activo",
    pickSeed: "Semilla",
    averageSeeds: "Media de las semillas",
    allSeeds: "Todas las semillas",
    equityTitle: "Equity fuera de muestra",
    equitySubtitle:
      "Ventana {start} — {end} · {bars} barras · motor {engine}. Curvas decimadas para el dibujo; cada punto conserva su valor exacto.",
    metricsTitle: "Métricas completas",
    metricsSubtitle: "Las dieciséis métricas de la batería, para la selección actual.",
    medianAcrossSeeds: "mediana entre las {n} semillas",
    medianNote:
      "Con la media seleccionada, cada métrica es la mediana entre semillas; el rango min–max aparece al pasar el cursor.",
    bestSeed: "Mejor",
    worstSeed: "Peor",
    benchmarkLine: "Comprar y mantener con funding (perpetuo, misma ventana)",
    averageLine: "Media de las semillas",
    seedLine: "Semilla {seed}",
    configTitle: "Configuración ganadora por pliegue",
    configSubtitleSeed:
      "Los 15 ganadores congelados de la semilla {seed}: los parámetros se eligieron en la ventana de validación y se puntuaron una única vez en el test de su pliegue.",
    configSubtitleAverage:
      "Valores más elegidos por la búsqueda entre los {n} ganadores de pliegue de todas las semillas. Seleccione una semilla concreta para ver sus 15 configuraciones exactas.",
    configFold: "Pliegue",
    configParams: "Parámetros",
    configValSharpe: "Sharpe val.",
    configTestSharpe: "Sharpe test",
    configTestReturn: "Retorno test",
    configTrades: "Ops.",
    configParam: "Parámetro",
    configTopValues: "Valores más frecuentes (nº de pliegues)",
    mcTitle: "Monte Carlo — dispersión bajo remuestreo",
    mcSubtitle:
      "Bootstrap estacionario por bloques ({block} barras esperadas, {paths} caminos, semilla del generador fija) sobre la serie OOS real de la semilla mediana por retorno ({seed}). Mide dispersión; no valida nada.",
    mcObserved: "Retorno observado",
    mcPercentile: "Percentil de lo observado",
    mcProbPositive: "P(retorno > 0) bajo remuestreo",
    mcQuantile: "Cuantil",
    mcTotalReturn: "Retorno total",
    mcNote:
      "La distribución remuestrea los retornos reales de una sola semilla: si lo observado cae dentro de la masa, el resultado es indistinguible de la variación de muestreo de su propia serie.",
    buyAndHold: "Comprar y mantener",
    thesis: "Qué apuesta esta familia",
    thesisMissing: "La hipótesis registrada de esta familia vive en su ronda, no en el cierre.",
    round: "Ronda",
    verdictRejected: "RECHAZADA en el cierre",
    verdictNotPromotable: "Evaluada tras el cierre — no promocionable (partición consumida)",
    banner:
      "Resultados exploratorios de desarrollo. Ninguna familia está promovida; el estudio cerró en negativo y la ronda CRT posterior no puede promover porque la partición reservada está consumida.",
    tableFamily: "Familia",
    tableRound: "Ronda",
    tableVerdict: "Veredicto",
    tableMedianReturn: "Retorno mediano",
    tableMedianSharpe: "Sharpe mediano",
    tableBh: "B&H",
    loading: "Cargando el índice de estrategias…",
    loadError:
      "No se pudo cargar el índice. Genérelo con: uv run python scripts/export_strategy_explorer.py",
    metric: {
      total_return: "Retorno total",
      ann_return: "Retorno anualizado",
      ann_volatility: "Volatilidad anualizada",
      sharpe: "Sharpe",
      sortino: "Sortino",
      calmar: "Calmar",
      max_drawdown: "Drawdown máximo",
      time_in_drawdown: "Tiempo en drawdown",
      hit_rate: "Tasa de acierto",
      n_trades: "Operaciones",
      exposure: "Exposición",
      turnover: "Rotación",
      var_95: "VaR 95%",
      expected_shortfall_95: "ES 95%",
      skewness: "Asimetría",
      excess_kurtosis: "Curtosis en exceso",
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

  provenance: {
    generated: "datos generados",
    contract: "contrato",
    holdout: "holdout desde",
    regen: "regenerable con",
  },

  experimentosApi: {
    title: "Esta sección necesita la API local",
    body:
      "El navegador de runs lee los artefactos de artifacts/runs a través de la API de " +
      "solo lectura. El resto del panel funciona sin ella; esta página no. Arránquela con " +
      "el comando siguiente y pulse reintentar.",
    retry: "Reintentar",
  },

  cuadernos: {
    title: "Cuadernos del estudio",
    subtitle:
      "Los ocho notebooks de análisis, reconstruibles de forma determinista por sus scripts " +
      "constructores, con el inventario de figuras y tablas congeladas que cita la memoria.",
    que: "¿Qué es esto?",
    queAnswer:
      "El índice de los ocho cuadernos: qué establece cada uno, cuántas celdas tiene, qué " +
      "figuras y tablas congeladas produce, y a qué capítulo de la memoria alimenta.",
    como: "¿Cómo se regeneran?",
    comoAnswer:
      "Cada cuaderno lo escribe un script constructor determinista (celdas, semilla y " +
      "contrato declarados). Ejecutar el script reproduce el cuaderno; el doble-run con " +
      "hash verifica que los artefactos salen byte a byte iguales.",
    queNo: "¿Qué NO son?",
    queNoAnswer:
      "No son exploración libre: son el registro ejecutable del estudio. Ninguna figura se " +
      "edita a mano; si una figura cambia, cambia su constructor y queda en el historial.",
    cells: "celdas",
    chapterLabel: "Destino en la memoria",
    chapterSource: "según",
    builderLabel: "Se regenera con",
    figuresLabel: "Figuras congeladas",
    tablesLabel: "Tablas congeladas",
    chainLabel: "Encadena (no computa nada)",
    none: "—",
    loadError:
      "No se pudo cargar el índice. Genérelo con: uv run python " +
      "scripts/export_notebooks_index.py",
  },

  panelHome: {
    verdictTitle: "El veredicto del estudio",
    verdictSubtitle:
      "Cierre estadístico sobre la partición de desarrollo. Estas cifras son estáticas y " +
      "auditables; no dependen de ningún servicio.",
    families: "familias evaluadas en el cierre",
    survive: "sobreviven a la corrección múltiple",
    pValue: "p-valor mínimo (umbral: {alpha})",
    pbo: "probabilidad de sobreajuste (PBO)",
    verdictLink: "Ver la evidencia completa →",
    statsTitle: "El estudio en cifras",
    statBars: "velas 1h de desarrollo",
    statRuns: "ejecuciones registradas",
    statFamilies: "familias implementadas",
    statRotations: "rotaciones del test de aleatorización",
    quickTitle: "Secciones",
    quickSubtitle: "El hilo del estudio, en orden de lectura.",
    liveTitle: "Estado en vivo",
    liveSubtitle: "Datos servidos por la API local en este momento.",
    apiHint:
      "La API local no está en marcha; las secciones estáticas de arriba no la necesitan. " +
      "Para el navegador de runs: uv run uvicorn perp_lab.api.main:app --port 8000",
    liveRunsTotal: "Runs totales",
    liveRunsDev: "Runs desarrollo",
    liveRunsSynthetic: "Runs sintéticos",
    liveRunsSyntheticSub: "no son resultados",
    liveHoldout: "Holdout",
    liveHoldoutSub: "partición bloqueada",
    pilotTitle: "Run piloto de referencia",
    pilotSymbol: "Símbolo",
    pilotInterval: "Intervalo",
    pilotBudget: "Budget",
    pilotFolds: "Folds",
    pilotFraction: "Fracción dev",
    pilotSeed: "Seed",
    pilotLink: "Ver experimento piloto →",
  },

  eda: {
    statBars: "velas 1h de desarrollo",
    statCoverage: "cobertura media de la serie",
    statSpan: "periodo de desarrollo",
    statDatasets: "datasets con manifiesto",
    provenanceTitle: "Procedencia y particiones",
    provenanceSubtitle:
      "Cada dataset con su hash SHA-256: la re-descarga desde Binance Vision reproduce estos " +
      "bytes exactamente. El holdout está separado físicamente en ficheros propios.",
    colDataset: "Dataset",
    colPartition: "Partición",
    colRows: "Filas",
    colSpan: "Periodo",
    colSha: "SHA-256",
    partitionDev: "desarrollo",
    partitionHoldout: "holdout (congelado)",
    priceTitle: "Precio",
    priceSubtitle: "Cierre diario, escala logarítmica",
    priceWhat:
      "Qué mira: la serie completa de precio con la partición reservada sombreada al final.",
    priceWhy:
      "Qué implica: la escala log evita que los primeros años queden aplastados; la zona " +
      "sombreada nunca alimentó ninguna decisión de diseño.",
    holdoutLabel: "holdout",
    volTitle: "Volatilidad rodante",
    volSubtitlePrefix: "Desviación típica móvil de",
    volSubtitleSuffix: "días, anualizada",
    volWhat: "Qué mira: cuánto se mueve el mercado, con ventana estrictamente retrospectiva.",
    volWhy:
      "Qué implica: la volatilidad cambia de régimen en órdenes de magnitud; una estrategia " +
      "de parámetros fijos no se comporta igual en 2021 que en 2024, y por eso el estudio " +
      "valida por ventanas temporales.",
    medianLabel: "mediana",
    distTitle: "Distribución de retornos horarios",
    distSubtitle: "Observada frente a una normal de igual media y desviación típica",
    distWhat:
      "Qué mira: el histograma real de retornos de 1h contra la campana gaussiana equivalente " +
      "(eje vertical logarítmico).",
    distWhy:
      "Qué implica: las colas reales exceden a la normal por órdenes de magnitud; cualquier " +
      "métrica de riesgo que asuma normalidad subestima el suceso extremo. Es la base " +
      "empírica del capítulo de riesgo.",
    distObserved: "observada",
    distNormal: "normal equivalente",
    tailsMove: "Movimiento",
    tailsExpected: "Prevé la normal",
    tailsObserved: "Ocurrió",
    tailsOver: "Más de",
    tailsFooterPrefix: "Sobre",
    tailsFooterSuffix: "horas de desarrollo.",
    seasonTitle: "Estacionalidad de la volatilidad",
    seasonWhat:
      "Qué mira: movimiento medio absoluto por barra de 1h (puntos básicos), hora UTC × día.",
    seasonWhy:
      "Qué implica: la sesión estadounidense concentra el movimiento y el fin de semana lo " +
      "apaga; el 'intradía' del título no es decorativo, es donde vive la estructura.",
    uwTitle: "Distancia al máximo previo (comprar y mantener)",
    uwWhat: "Qué mira: la profundidad respecto al máximo histórico en cada instante.",
    uwWhy:
      "Qué implica: incluso el activo pasa casi todo el tiempo bajo un máximo anterior; el " +
      "drawdown no es una anomalía del trading, es el estado normal de la serie.",
    fundingTitle: "Funding del perpetuo",
    fundingWhat: "Qué mira: media semanal del funding rate real (eventos de 8 horas).",
    fundingWhy:
      "Qué implica: mantener un largo cuesta de media un {pct} anual solo en funding; el " +
      "motor del estudio lo cobra barra a barra y ninguna comparación es válida sin él.",
    annexTitle: "Anexo: galería EDA congelada",
    annexSubtitle:
      "Las figuras matplotlib generadas por el pipeline de EDA, tal como se citan en la " +
      "memoria. Son artefactos congelados; los gráficos vivos de arriba se calculan de los " +
      "mismos datos.",
    annexApiNote:
      "La galería se sirve desde la API local. Arránquela con: uv run uvicorn " +
      "perp_lab.api.main:app --port 8000",
    annexOpen: "Mostrar galería ({n} figuras)",
  },

  lab: {
    title: "Laboratorio de estrategias",
    subtitle:
      "Construya una estrategia con las familias del estudio, ajuste sus parámetros y ejecútela " +
      "sobre las velas horarias reales de BTC y ETH — con el mismo modelo de ejecución, costes y " +
      "funding que el motor de la investigación.",
    banner:
      "Herramienta exploratoria y docente. El motor del navegador replica el del estudio " +
      "(ejecución next-open, comisiones, deslizamiento y funding reales), pero un resultado " +
      "favorable aquí NO valida nada: la batería del estudio exige multi-semilla, walk-forward y " +
      "corrección por comparaciones múltiples. El periodo de reserva está excluido de estos datos.",
    flow: {
      title: "El flujo completo, en el mismo orden que el estudio",
      design: "Diseña",
      designDesc: "Familia y parámetros del espacio del estudio",
      backtest: "Ejecuta",
      backtestDesc: "Backtest con costes y funding reales",
      validate: "Valida",
      validateDesc: "Walk-forward multi-semilla, el protocolo del estudio",
      compare: "Compara",
      compareDesc: "Frente a las 15 familias formales",
      done: "hecho",
      pending: "pendiente",
    },
    que: "¿Qué es esto?",
    queAnswer:
      "Un backtester real que corre en su navegador sobre la partición de desarrollo (2020–2025). " +
      "Cuatro familias del estudio están portadas línea a línea desde el código Python: mismos " +
      "umbrales, misma exclusión del bar de decisión, misma máquina de estados de posición.",
    comoFunciona: "¿Cómo se ejecuta una orden?",
    comoFuncionaAnswer:
      "La señal se decide con la vela cerrada y se ejecuta en la apertura de la siguiente; nunca al " +
      "precio que generó la señal. Cada cambio de posición paga comisión y deslizamiento (un giro " +
      "largo→corto paga doble), y cada barra en posición liquida el funding que venza en su " +
      "intervalo.",
    queNo: "¿Qué NO concluir aquí?",
    queNoAnswer:
      "Que su configuración «funciona». Con miles de combinaciones posibles, encontrar una curva " +
      "ascendente es cuestión de intentos, no de ventaja: es exactamente el sesgo de selección que " +
      "el estudio mide. Use la batería de contraste como lo que es: un primer filtro honesto.",
    pickStrategy: "Familia",
    pickAsset: "Activo",
    paramsTitle: "Parámetros",
    studyValuesNote: "Los valores marcados pertenecen al espacio de búsqueda del estudio.",
    costsTitle: "Costes",
    fee: "Comisión (pb por lado)",
    slippage: "Deslizamiento (pb por lado)",
    costsNote: "Por defecto: taker 4 pb + 1 pb, los del estudio.",
    splitLabel: "Corte in-sample / out-of-sample",
    splitNote:
      "Los indicadores se calculan de forma causal sobre toda la serie; las métricas se separan " +
      "en las dos fases por fecha de entrada.",
    run: "Ejecutar backtest",
    running: "Ejecutando…",
    dataLoading: "Cargando las velas reales…",
    dataError:
      "No se pudieron cargar los datos del laboratorio. Genérelos con: uv run python " +
      "scripts/export_lab_data.py",
    dataFootnote:
      "{n} velas de 1h · {start} — {end} · partición de desarrollo, holdout excluido · " +
      "funding real de Binance ({nf} eventos).",
    strategies: {
      momentum: {
        name: "Momentum (cruce de medias)",
        tagline: "Seguir la tendencia cuando la media rápida cruza la lenta.",
        how:
          "Largo cuando la SMA rápida supera a la lenta; corto cuando queda por debajo. Es la " +
          "familia de seguimiento de tendencia más clásica y la referencia histórica del género.",
      },
      mean_reversion: {
        name: "Reversión a la media (z-score)",
        tagline: "Apostar a que el precio vuelve tras un extremo.",
        how:
          "Se mide cuántas desviaciones típicas se aleja el precio de su media móvil. Corto por " +
          "encima de +z de entrada, largo por debajo de −z, cierre cuando vuelve a ±z de salida.",
      },
      breakout: {
        name: "Ruptura de canal (Donchian)",
        tagline: "Entrar cuando el precio rompe su rango reciente.",
        how:
          "Largo si el cierre supera el máximo de las N barras anteriores; corto si pierde el " +
          "mínimo. Salida cuando el precio vuelve dentro del canal. Se puede exigir confirmación " +
          "de varias barras.",
      },
      volatility_breakout: {
        name: "Ruptura escalada por volatilidad",
        tagline: "Una ruptura solo cuenta si es grande para la volatilidad del momento.",
        how:
          "Como la ruptura de canal, pero el umbral se desplaza un múltiplo del ATR: un 2% en " +
          "mercado tranquilo no es lo mismo que un 2% en plena tormenta. Fue la mejor familia del " +
          "estudio — y aun así, rechazada.",
      },
      funding_reversal: {
        name: "Reversión tras funding extremo",
        tagline: "Cuando un lado paga demasiado por mantenerse, apostar a que cede.",
        how:
          "Un funding en el extremo de su distribución rodante indica un lado saturado del " +
          "libro. La señal abre la posición contraria y la mantiene un número fijo de barras, " +
          "pase lo que pase. Usa la serie real de funding de Binance (evento cada 8h, unido " +
          "causalmente barra a barra).",
      },
      intraday_seasonality: {
        name: "Estacionalidad intradía",
        tagline: "La entrada es una hora del reloj, no un patrón de precio.",
        how:
          "Entra a una hora UTC fija y mantiene un número fijo de barras; opcionalmente solo a " +
          "favor de la media móvil. No contiene ningún predictor de precio: si funcionara, la " +
          "explicación sería la periodicidad del flujo, no un patrón.",
      },
    },
    exampleCaption: "Ilustración esquemática de la regla; no son datos reales.",
    phasesTitle: "Métricas por fase",
    phaseIn: "In-sample",
    phaseOut: "Out-of-sample",
    phaseFull: "Serie completa",
    buyHold: "Comprar y mantener",
    strategyLabel: "Estrategia",
    testsTitle: "Batería de contraste (out-of-sample)",
    testsSubtitle:
      "Siete comprobaciones sobre la fase que la estrategia no ha visto al elegir parámetros. " +
      "Superarlas es condición necesaria, jamás suficiente.",
    testReturn: "Retorno neto positivo",
    testReturnDesc:
      "El retorno compuesto out-of-sample, neto de todos los costes, es mayor que cero.",
    testSharpe: "Sharpe positivo",
    testSharpeDesc: "La media de los retornos por barra supera su ruido (Sharpe anualizado > 0).",
    testBh: "Supera a comprar y mantener",
    testBhDesc: "Rinde más que la referencia pasiva con sus mismos costes en la misma fase.",
    testNull: "Distinguible de su propio azar",
    testNullDesc:
      "Prueba de rotación circular: {n} versiones de la estrategia con las posiciones giradas a un " +
      "punto aleatorio, mismos costes. p-valor unilateral del retorno real contra ese nulo.",
    pass: "SUPERADA",
    fail: "NO SUPERADA",
    pValueLabel: "p-valor",
    testBootstrap: "Sharpe robusto al remuestreo",
    testBootstrapDesc:
      "Bootstrap estacionario (200 remuestreos por bloques, semilla fija) del Sharpe " +
      "out-of-sample. Supera si el intervalo del 95% queda entero por encima de cero.",
    testStress: "Sobrevive con costes ×2",
    testStressDesc:
      "El mismo backtest con comisión y deslizamiento duplicados. Sin holgura frente a los " +
      "costes, cualquier ventaja aparente es frágil.",
    testTwin: "Generaliza al activo gemelo",
    testTwinDesc:
      "La misma configuración, sin retocar nada, sobre el otro activo (BTC↔ETH). Una regla " +
      "que solo funciona en un activo es sospechosa de estar ajustada a su historia.",
    tornadoTitle: "Sensibilidad de parámetros (tornado)",
    tornadoSubtitle:
      "Cambio del retorno out-of-sample al mover cada parámetro un paso del espacio del " +
      "estudio, hacia abajo (−1) y hacia arriba (+1).",
    tornadoNote:
      "Barras grandes = configuración frágil: el resultado depende del valor exacto del " +
      "parámetro, la firma clásica del sobreajuste. Es la prueba de perturbación del " +
      "estudio, interactiva.",
    regimeTitle: "Métricas por régimen de volatilidad",
    regimeSubtitle:
      "La fase out-of-sample partida por terciles de volatilidad (rvol 168h causal; " +
      "fronteras calculadas solo con la fase in-sample).",
    regimeCol: "Régimen",
    regimeBars: "Barras",
    regimeLow: "Tranquilo (tercil bajo)",
    regimeMid: "Medio",
    regimeHigh: "Turbulento (tercil alto)",
    regimeNote:
      "Si toda la ganancia vive en un solo régimen, la regla no captura una ventaja: captura " +
      "un tipo de época — y las épocas no se eligen de antemano.",
    testsDisclaimer:
      "Aunque las siete salgan verdes: el estudio exigió además diez semillas, quince pliegues " +
      "walk-forward y corrección de Holm por todas las familias probadas — y ninguna sobrevivió. " +
      "Un 7/7 aquí es una invitación a desconfiar, no un descubrimiento.",
    equityTitle: "Curva de equity",
    equitySubtitle:
      "Capital compuesto barra a barra, neto de costes y funding. La zona sombreada es la fase " +
      "in-sample; la línea vertical marca el corte.",
    signalsTitle: "Precio y señales",
    signalsSubtitle:
      "Ventana de {bars} barras alrededor del punto seleccionado. ▲ entrada larga · ▼ entrada " +
      "corta · ✕ salida a plano.",
    signalsWindow: "Posición de la ventana",
    drawdownTitle: "Drawdown",
    maefeTitle: "Excursión máxima por operación (MAE / MFE)",
    maefeSubtitle:
      "Para cada operación: cuánto llegó a ir a favor (MFE) y cuánto en contra (MAE) respecto al " +
      "precio de entrada, medido con los máximos y mínimos reales de cada barra en posición.",
    maefeX: "MAE — excursión adversa máxima",
    maefeY: "Retorno neto de la operación",
    medianMae: "MAE mediana",
    medianMfe: "MFE mediana",
    eRatio: "e-ratio (MFE media / MAE media)",
    eRatioNote:
      "Un e-ratio ≤ 1 indica que las operaciones sufren tanto o más en contra de lo que llegan a " +
      "ir a favor: la regla de entrada no está capturando asimetría alguna.",
    tradeStatsTitle: "Estadística de operaciones",
    profitFactor: "Factor de beneficio",
    expectancy: "Expectativa por operación",
    tradeHitRate: "Acierto por operación",
    nTradesClosed: "Operaciones cerradas",
    meanDuration: "Duración media (barras)",
    ulcer: "Índice de úlcera",
    winStreak: "Racha ganadora más larga",
    lossStreak: "Racha perdedora más larga",
    history: {
      title: "Sus intentos de esta sesión",
      subtitle:
        "Cada backtest ejecutado en este navegador, con sus métricas out-of-sample. La fila " +
        "destacada es su mejor Sharpe — es decir, la cola derecha de sus propios intentos.",
      clear: "Limpiar historial",
      colFamily: "Familia",
      colParams: "Parámetros",
      colReturn: "Retorno OOS",
      colTests: "Tests",
      best: "mejor",
      note:
        "Esta tabla es el sesgo de selección hecho visible: si publicara solo la fila " +
        "destacada y borrara las demás, tendría el folleto de cualquier vendedor de " +
        "estrategias. El contador de intentos de arriba deflacta ese mejor resultado.",
    },
    overlay: {
      title: "Salidas y filtros",
      stop: "Stop (× ATR)",
      takeProfit: "Take-profit (× ATR)",
      trailing: "Trailing (× ATR)",
      maxBars: "Salida por tiempo (barras)",
      trendGate: "Solo a favor de la SMA(200)",
      regimes: "Regímenes permitidos",
      low: "bajo",
      mid: "medio",
      high: "alto",
      note:
        "Los overlays solo recortan exposición (la reentrada exige señal nueva de la " +
        "familia). ATR causal de 24 barras; régimen por terciles rodantes causales de rvol " +
        "168h. Se aplican al backtest simple, no al walk-forward.",
    },
    wf: {
      title: "Walk-forward multi-semilla — el protocolo del estudio",
      subtitle:
        "La misma validación de la tesis, en miniatura y ejecutable: en cada pliegue se " +
        "eligen parámetros en la ventana de validación y se puntúan una sola vez en los 90 " +
        "días de test que nunca vieron. Corre en un hilo aparte del navegador.",
      budget: "Candidatos por pliegue",
      seeds: "Semillas",
      run: "Ejecutar walk-forward",
      running: "Ejecutando…",
      seedProgress: "Semilla {i} de {n}",
      foldsNote:
        "Geometría real del estudio: {n} pliegues con purga y embargo, tomados literalmente " +
        "de {run}. Selección por Sharpe de validación (simplificación declarada del fitness " +
        "penalizado del estudio).",
      fanTitle: "Equity out-of-sample concatenada, por semilla",
      foldsTitle: "Retorno de test por pliegue (media de semillas)",
      explainer:
        "Configure presupuesto y semillas y ejecute. El resultado honesto no es una curva: " +
        "es un abanico — la misma búsqueda con distinto azar de arranque produce resultados " +
        "distintos, y esa dispersión es parte de la respuesta.",
      disclaimer:
        "Este walk-forward selecciona en validación y evalúa en test, pero sigue siendo una " +
        "herramienta exploratoria: el estudio añadió además corrección por comparaciones " +
        "múltiples entre todas las familias probadas — y bajo esa corrección ninguna " +
        "sobrevivió.",
    },
    attempts: {
      title: "Contador de intentos de la sesión",
      body:
        "Backtests ejecutados en este navegador. Con este número de intentos sin habilidad " +
        "alguna, el mejor Sharpe esperable por puro azar ya es ≈ {sharpe}.",
      compare:
        "Su mejor Sharpe OOS: {best}. Umbral del azar con sus intentos: {chance}. Si no lo " +
        "supera con holgura, la selección — no la estrategia — explica el resultado.",
    },
    pretrainedTitle: "Las familias ya estudiadas",
    pretrainedBody:
      "Las familias del estudio formal exportadas al explorador (quince de las dieciséis con " +
      "estudio completo) se consultan allí con sus diez semillas, su walk-forward y sus métricas.",
    pretrainedLink: "Abrir el explorador de estrategias →",
  },
} as const;

export type EsCopy = typeof es;
