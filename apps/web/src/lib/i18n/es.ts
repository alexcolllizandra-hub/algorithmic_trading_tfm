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
        "La conclusión textual del informe de cierre se cita literalmente en el panel 13. El holdout congelado sigue bloqueado: esta página explica qué es, pero no muestra ninguna lectura suya.",
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
      holdout: "Holdout congelado (no se abre)",
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
          "Los datos son velas de futuros perpetuos USDT-M sobre dos activos muy acoplados, y la partición final sigue cerrada: todo lo que se juzga aquí ocurre en desarrollo.",
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
          "El reparto es cronológico y el holdout permanece cerrado, así que las cifras de los paneles siguientes son de test dentro de la partición de desarrollo.",
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
          "Bajo este modelo de costes y en esta clase de instrumento, el estudio no encuentra ventaja. El holdout sigue cerrado a la espera de auditoría y su lectura queda retenida.",
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
        "El artefacto declara la partición congelada como no abierta, así que ninguna cifra suya existe todavía en el estudio.",
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
        "La lectura del holdout queda retenida a la espera de auditoría. Esta guía explica qué es la partición congelada y por qué sigue cerrada, pero no publica ninguna de sus métricas.",
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
