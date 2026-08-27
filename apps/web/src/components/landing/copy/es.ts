// Spanish landing copy. Academic register: hypothesis, method, evidence,
// finding. Every factual claim is traceable to a repository artifact; the
// numbers themselves are never hard-coded here — they come from /data.
//
// Strings that need runtime values use {token} placeholders resolved by
// `tpl()` in ./index.ts.

export const es = {
  header: {
    links: [
      { href: "#marco", label: "Marco" },
      { href: "#sesgo", label: "Sesgo de selección" },
      { href: "#metodo", label: "Método" },
      { href: "#datos", label: "Datos" },
      { href: "#resultado", label: "Resultado" },
      { href: "#estado", label: "Estado" },
    ],
    panel: "Panel de investigación",
    signIn: "Entrar",
    signOut: "Salir",
    openMenu: "Abrir menú",
    closeMenu: "Cerrar menú",
    sectionsAria: "Secciones",
  },

  hero: {
    kicker: "Trabajo de Fin de Máster · Ciencia de Datos · Investigación abierta",
    titleA: "Detección y validación de estrategias intradía ",
    titleGradient: "con control explícito del sesgo de selección",
    titleB: ".",
    sub:
      "Estudio reproducible sobre futuros perpetuos de BTC y ETH: seis años de datos, " +
      "validación walk-forward, corrección por comparaciones múltiples y un periodo de " +
      "reserva congelado. El resultado principal es negativo y se publica íntegro, " +
      "porque en este dominio el resultado negativo riguroso es el hallazgo.",
    ctaData: "Ver los datos del estudio",
    ctaPlain: "Lectura no técnica",
    ctaPanel: "Panel de investigación",
    stats: {
      bars: "velas horarias analizadas",
      years: "años de historia de mercado",
      coverage: "cobertura de la serie, sin huecos",
      holdout: "periodo de reserva congelado desde",
    },
  },

  plain: {
    eyebrow: "Marco conceptual",
    title: "El objeto de estudio, en tres pasos",
    lead:
      "Esta sección presenta el problema sin vocabulario técnico. El resto de la página " +
      "desarrolla cada paso con los datos y métodos del estudio.",
    steps: [
      {
        n: "01",
        title: "Una estrategia sistemática es una regla explícita",
        body:
          "Operar de forma sistemática consiste en fijar por escrito qué se compra, en qué " +
          "cantidad y cuándo se vende. Al estar formalizada, la regla puede repetirse, " +
          "medirse y auditarse — condiciones necesarias para tratarla como objeto de estudio.",
      },
      {
        n: "02",
        title: "El backtest la evalúa sobre el pasado",
        body:
          "Antes de comprometer capital, la regla se simula sobre la historia disponible: " +
          "¿qué habría producido durante los últimos seis años? Esa simulación es el " +
          "backtest, y constituye la evidencia principal — y la principal fuente de error — " +
          "de este campo.",
      },
      {
        n: "03",
        title: "El problema metodológico es el sesgo de selección",
        body:
          "Si se ajusta la regla hasta que el pasado sale favorable, el resultado no informa " +
          "sobre el futuro: informa sobre cuánto se ha ajustado. La mayor parte del diseño de " +
          "este estudio existe para impedir esa vía, incluso de forma involuntaria.",
      },
    ],
    quote:
      "Un resultado negativo obtenido con rigor es un resultado válido. Un resultado " +
      "positivo obtenido con información del futuro no lo es.",
    quoteFooter: "Criterio que ordena todas las decisiones metodológicas del proyecto.",
  },

  concepts: {
    eyebrow: "Fundamentos",
    title: "Cinco conceptos que condicionan la validez de un backtest",
    lead:
      "Cada tarjeta recoge la definición formal y una ilustración cotidiana. Son los cinco " +
      "mecanismos de error que la literatura identifica con más frecuencia en la evaluación " +
      "de estrategias.",
    everydayLabel: "Ilustración",
    seeMeasured: "Ver la medición",
    items: [
      {
        title: "Sobreajuste",
        technical:
          "Un modelo con suficientes grados de libertad memoriza el ruido de la muestra: su " +
          "error de entrenamiento baja mientras el error fuera de muestra crece.",
        everyday:
          "Es memorizar las preguntas del examen del año pasado: nota perfecta en ese examen, " +
          "suspenso en el de este año.",
        punchline: "Un backtest con métricas excepcionales es, por defecto, sobreajuste.",
      },
      {
        title: "Eficiencia de mercado",
        technical:
          "Si el precio incorpora la información disponible, ninguna regla basada en esa " +
          "información obtiene beneficio esperado positivo neto de costes.",
        everyday:
          "La cola más corta del supermercado deja de serlo en cuanto todos la observan: la " +
          "ventaja desaparece al difundirse.",
        punchline: "Por eso la hipótesis nula del estudio es la ausencia de ventaja.",
      },
      {
        title: "Ley de los grandes números",
        technical:
          "La media muestral converge a la esperanza al crecer n. Con n pequeño, la varianza " +
          "del estimador hace indistinguibles azar y habilidad.",
        everyday:
          "Con diez lanzamientos no se distingue una moneda sesgada de una equilibrada; con " +
          "diez mil, sí.",
        punchline: "Treinta operaciones no constituyen evidencia.",
      },
      {
        title: "Criterio de Kelly",
        technical:
          "La fracción de capital que maximiza el crecimiento logarítmico esperado. Apostar " +
          "por encima del óptimo reduce el crecimiento y eleva la probabilidad de ruina; el " +
          "óptimo es además frágil al error de estimación.",
        everyday:
          "Incluso con un juego favorable, apostarlo todo en cada mano conduce a la ruina: el " +
          "tamaño de la posición importa tanto como el acierto.",
        punchline: "Tener razón y arruinarse no son incompatibles.",
      },
      {
        title: "Colas pesadas",
        technical:
          "Los retornos presentan colas mucho más pesadas que la normal: los sucesos extremos " +
          "son órdenes de magnitud más frecuentes de lo que predice el modelo gaussiano.",
        everyday:
          "Un dique dimensionado para la peor riada del siglo pasado no protege del año en " +
          "que llega una mayor.",
        punchline: "Más abajo está cuantificado sobre los datos del estudio.",
      },
    ],
  },

  overfitting: {
    eyebrow: "El problema central",
    title: "El sesgo de selección, medido en este estudio",
    lead:
      "Evaluar muchas configuraciones y retener la mejor produce métricas favorables aunque " +
      "no exista señal. Aquí está medido con las búsquedas del propio estudio.",
    loadErrorPrefix: "No se pudo cargar la evidencia del estudio. Genere el fichero con",
    simpleLabel: "Lectura no técnica",
    simpleStrong: "Los seleccionados no mantienen su ventaja.",
    simpleLede:
      "Considérese una cohorte de 3.000 candidatos evaluados en una prueba preliminar. Se " +
      "retiene a los mejores y se les somete a una prueba posterior independiente. ",
    simpleAfter:
      "No por irregularidad alguna: con una cohorte tan numerosa, algunos puntúan alto por puro azar.",
    scatterBody:
      "Cada punto es una configuración que ganó su ronda de selección. Si la métrica de " +
      "selección fuese informativa, los puntos se alinearían con la diagonal discontinua. La " +
      "recta ajustada es casi plana: la posición en la selección apenas predice el " +
      "comportamiento posterior.",
    stats: {
      selected: "Sharpe medio en la ventana de selección",
      after: "Sharpe medio en la ventana de prueba posterior",
      worsened: "configuraciones que empeoran respecto a su selección",
      survives: "de la ventaja aparente que persiste (100% indicaría selección informativa)",
    },
    leak: {
      label: "El segundo mecanismo de error",
      title: "Fuga de información futura",
      p1:
        "Un indicador mal especificado puede incorporar datos que no eran conocibles en el " +
        "momento de la decisión. El síntoma no es un fallo: es un rendimiento anómalamente " +
        "alto. Aquí el efecto está reproducido de forma deliberada — misma regla, mismos " +
        "datos, mismos costes — permitiendo que una variante observe 23 horas de futuro.",
      p2:
        "El signo es irrelevante, porque bastaría invertir la regla; lo que delata la fuga es " +
        "la magnitud. Ningún resultado legítimo de este mercado se aproxima a esas cifras.",
      variants: {
        causal: "Especificación causal (solo pasado)",
        leaky: "Con fuga temporal",
        flipped: "Con fuga temporal, signo invertido",
        buyAndHold: "Comprar y mantener",
      },
      caption:
        "Figura 8 · Sharpe anualizado neto de costes, en valor absoluto. «Comprar y mantener» " +
        "es la referencia pasiva del mismo periodo.",
    },
  },

  costs: {
    eyebrow: "Eficiencia y costes",
    title: "La ventaja aparente frente al coste de transacción",
    lead:
      "La eficiencia predice que ninguna regla sobre información pública sobrevive neta de " +
      "costes. Contraste: misma estrategia, mismo periodo, variando solo el coste por " +
      "operación.",
    panels: {
      erosionLabel: "Erosión por costes",
      erosionTitle: "El punto de cruce de la ventaja",
      erosionCaption:
        "Figura 9 · Sharpe anualizado sobre la partición de desarrollo, variando únicamente el " +
        "coste de ida y vuelta. El resto de condiciones permanece fijo.",
      wedgeLabel: "Bruto frente a neto",
      wedgeTitle: "La brecha crece con la rotación",
      wedgeCaption:
        "Figura 10 · Cada par de puntos es una configuración de medias móviles: arriba, el " +
        "resultado antes de costes; debajo, el mismo tras comisiones, deslizamiento y funding.",
    },
    statCrossing: "coste por operación completa al que la ventaja se anula",
    statBuyHold: "Sharpe de comprar y mantener en el mismo periodo",
    simpleLabel: "Lectura no técnica",
    simpleStrong: "Basta con que participar tenga precio.",
    simpleLede: "No se requiere eficiencia perfecta para que la ventaja desaparezca. ",
    body1Prefix:
      "La curva descendente no refleja un deterioro de la estrategia: es la misma regla sobre " +
      "los mismos datos, y lo único que aumenta es el coste. En torno a ",
    body1Fallback: "cierto nivel de coste",
    body1Suffix:
      " por operación completa, la ventaja aparente se anula — y ese nivel está dentro del " +
      "rango que cobra un exchange real.",
    body2:
      "El panel derecho explica por qué operar más no es una solución: cuanto mayor es la " +
      "rotación, mayor es la separación entre el resultado bruto y el neto. ",
    body2Accent: "La actividad no es una fuente de rentabilidad; es una fuente de coste.",
    bpsUnit: "puntos básicos",
  },

  pipeline: {
    eyebrow: "Diseño del estudio",
    title: "Del dato en bruto al veredicto, por etapas",
    lead:
      "Cada etapa alimenta a la siguiente y ninguna puede omitirse. Se indica el estado de " +
      "implementación de cada una.",
    statusLabel: {
      done: "Implementado",
      "in-review": "En revisión",
      blocked: "Bloqueado",
      planned: "Planificado",
    },
    steps: [
      {
        id: "datos",
        title: "Datos",
        what: "Descarga de velas de BTC y ETH perpetuo en Binance Futures.",
        status: "done",
        detail:
          "Seis años y medio de historia desde enero de 2020. El fichero descargado es " +
          "inmutable: toda corrección se aplica sobre una copia derivada y documentada.",
      },
      {
        id: "validacion",
        title: "Validación de datos",
        what: "Verificación de integridad de las series.",
        status: "done",
        detail:
          "Huecos, duplicados, velas inconsistentes (mínimo superior al máximo), volúmenes " +
          "negativos. Las anomalías se marcan y se reportan; nunca se eliminan en silencio.",
      },
      {
        id: "eda",
        title: "Análisis exploratorio",
        what: "Caracterización del mercado antes de modelarlo.",
        status: "done",
        detail:
          "Volatilidad, colas de la distribución, regímenes, estacionalidad, funding y " +
          "dependencia entre activos. Esta fase determina qué hipótesis merecen contraste.",
      },
      {
        id: "features",
        title: "Indicadores",
        what: "Variables construidas exclusivamente con información pasada.",
        status: "done",
        detail:
          "Cada indicador se somete a una prueba de causalidad: si se trunca el futuro del " +
          "conjunto de datos, ningún valor pasado puede cambiar.",
      },
      {
        id: "estrategias",
        title: "Estrategias",
        what: "Reglas explícitas y auditables, no cajas negras.",
        status: "done",
        detail:
          "Cruce de medias, ruptura de rango, reversión a la media, consenso multi-marco. El " +
          "criterio de diseño: toda regla debe poder enunciarse en una frase.",
      },
      {
        id: "backtest",
        title: "Backtest con costes",
        what: "Simulación histórica con la estructura de costes completa.",
        status: "done",
        detail:
          "Comisiones, deslizamiento y funding. La orden se decide con la vela cerrada y se " +
          "ejecuta en la apertura siguiente, nunca al precio que generó la señal.",
      },
      {
        id: "validacion-temporal",
        title: "Validación temporal",
        what: "Entrenamiento en el pasado, evaluación en el futuro, repetido.",
        status: "done",
        detail:
          "Walk-forward con purga y embargo, búsqueda aleatoria y algoritmo genético con " +
          "presupuestos idénticos, y contabilidad explícita del número de contrastes.",
      },
      {
        id: "meta",
        title: "Filtro de aprendizaje automático",
        what: "Un clasificador que decide cuándo no operar.",
        status: "in-review",
        detail:
          "Etiquetado por triple barrera y un clasificador que filtra las señales de la " +
          "estrategia base. Validado sobre mercados sintéticos con respuesta conocida; se " +
          "mantiene como infraestructura porque ninguna estrategia base justificó su uso.",
      },
      {
        id: "holdout",
        title: "Evaluación confirmatoria",
        what: "Apertura única del periodo de reserva.",
        status: "in-review",
        detail:
          "Se abrió una única vez, sobre un candidato declarado de antemano, y su lectura " +
          "existe en disco. Queda pendiente la auditoría de procedencia que verificaría la " +
          "congelación previa del candidato; hasta entonces, la cifra no se publica.",
      },
      {
        id: "riesgo",
        title: "Riesgo y cartera",
        what: "Dimensionado de posiciones y combinación de estrategias.",
        status: "planned",
        detail:
          "Carece de objeto mientras ninguna estrategia supere las fases anteriores. Está " +
          "especificado en el roadmap; no implementado.",
      },
    ],
  },

  architecture: {
    eyebrow: "Arquitectura del sistema",
    title: "Seis capas, cada una con su salvaguarda",
    lead:
      "El dato entra por la primera capa y sale de la última convertido en un veredicto. La " +
      "propiedad que hace defendible el resultado no es ninguna capa aislada, sino que todas " +
      "fallan en cerrado: ante una condición no prevista, el sistema se detiene en lugar de " +
      "continuar con un supuesto.",
    howBuilt: "Implementación",
    lockLabel: "Salvaguarda",
    layers: [
      {
        id: "datos",
        name: "Datos",
        role: "Persistir el mercado y no volver a tocarlo",
        plain:
          "Las velas se descargan una vez y se conservan tal cual. Toda transformación " +
          "posterior vive en una copia derivada con procedencia documentada.",
        technical:
          "Descarga masiva desde data.binance.vision con incrementales por CCXT. Cada dataset " +
          "lleva manifiesto con origen, símbolo, periodo, número de filas y SHA-256. " +
          "Validación con esquemas: huecos, duplicados, OHLC inconsistente, volumen negativo.",
        guard: "data/raw es de solo lectura. Los valores extremos se marcan, nunca se eliminan.",
        modules: ["data/providers", "data/manifest", "validation/schemas"],
      },
      {
        id: "features",
        name: "Indicadores",
        role: "Calcular solo lo conocible en cada instante",
        plain:
          "Cada indicador mira exclusivamente hacia atrás: truncar el futuro del fichero no " +
          "puede alterar ningún valor pasado.",
        technical:
          "Registro declarativo de indicadores: cada uno declara entradas, ventana, el " +
          "instante en que su valor es conocible y cuántas filas iniciales quedan vacías. Los " +
          "indicadores contextuales se retrasan explícitamente antes de usarse.",
        guard:
          "Siete pruebas de causalidad ejecutadas sobre los datos reales, no sobre fixtures. " +
          "Una fuga introducida deliberadamente las hace fallar de inmediato.",
        modules: ["features/spec", "features/causal", "features/registry"],
      },
      {
        id: "estrategias",
        name: "Estrategias",
        role: "Reglas enunciables en una frase",
        plain:
          "Sin cajas negras: cruce de medias, ruptura de rango, reversión a la media, funding, " +
          "confirmación entre BTC y ETH. Toda regla evaluada es legible y auditable.",
        technical:
          "Trece familias con espacio de parámetros tipado y finito, reparación de " +
          "combinaciones inválidas y hash canónico por candidato. Un mismo motor sirve las " +
          "nueve variantes de Candle Range Theory.",
        guard: "El espacio se declara antes de buscar y no se amplía tras ver resultados.",
        modules: ["strategies/*", "search/space", "crt/*"],
      },
      {
        id: "backtest",
        name: "Backtest",
        role: "Simular con la estructura de costes completa",
        plain:
          "La orden se decide con la vela cerrada y se ejecuta en la apertura de la siguiente, " +
          "nunca al precio que acaba de revelar la señal.",
        technical:
          "Registro por vela con señal, posición, precio de ejecución, retorno bruto, " +
          "comisión, deslizamiento, funding y retorno neto. Un giro de largo a corto mueve dos " +
          "unidades de nocional y se contabiliza como dos.",
        guard:
          "Si el experimento exige funding y no existe la serie, el motor falla en lugar de " +
          "asumir cero.",
        modules: ["backtesting/engine", "backtesting/metrics"],
      },
      {
        id: "validacion",
        name: "Validación temporal",
        role: "Construir futuro genuino, quince veces",
        plain:
          "Se entrena con el pasado y se evalúa con lo posterior, avanzando por el calendario, " +
          "con un intervalo de separación para que ninguna operación cruce la frontera.",
        technical:
          "Walk-forward expandido: quince pliegues con entrenamiento anclado y ventanas de " +
          "selección y prueba de 90 días sin solape. Purga y embargo derivados del periodo " +
          "máximo de mantenimiento, no elegidos ad hoc.",
        guard:
          "Ningún pliegue puede alcanzar el periodo de reserva. La comprobación lanza " +
          "excepción, no un aviso.",
        modules: ["validation/walk_forward", "search/evaluator"],
      },
      {
        id: "inferencia",
        name: "Inferencia",
        role: "Contabilizar cada contraste realizado",
        plain:
          "Al evaluar trece familias, alguna parecerá buena por azar. El estudio lleva la " +
          "cuenta de todos los contrastes y corrige el resultado en consecuencia.",
        technical:
          "Diez semillas por unidad, con la unidad de inferencia en activo × pliegue y las " +
          "semillas promediadas por celda. Corrección de Holm-Bonferroni y Benjamini-Hochberg, " +
          "Sharpe deflactado y probabilidad de sobreajuste del backtest (PBO).",
        guard:
          "El veredicto se verifica bajo cuatro definiciones del número de contrastes, de " +
          "trece a casi medio millón.",
        modules: ["evaluation/multiple_testing", "evaluation/study_robustness"],
      },
    ],
  },

  integrity: {
    eyebrow: "Integridad metodológica",
    title: "Cuatro reglas contra el autoengaño",
    lead:
      "En la evaluación de estrategias, la principal fuente de error es el propio " +
      "investigador. Estas reglas están implementadas en el código y verificadas por las " +
      "pruebas, no confiadas a la disciplina personal.",
    techLabel: "Formalmente",
    receiptCaption: "Manifiesto real de uno de los datasets que alimentan esta página",
    rowRows: "filas",
    rowGenerated: "generado",
    principles: [
      {
        title: "El orden temporal es inviolable",
        plain:
          "La regla se entrena con el pasado y se evalúa con lo que vino después. Permutar " +
          "las fechas equivaldría a examinarse con las respuestas a la vista.",
        technical:
          "Particiones estrictamente cronológicas, con purga y embargo entre entrenamiento y " +
          "prueba para que ninguna operación cruce la frontera.",
      },
      {
        title: "Seis meses en reserva",
        plain:
          "Los últimos seis meses de datos se apartaron desde el inicio y no participaron en " +
          "ninguna decisión. Se abrieron una única vez, al final; la lectura quedó retenida a " +
          "la espera de una auditoría de procedencia, y la conclusión no depende de ella.",
        technical:
          "Partición reservada en [2026-01-01, 2026-07-01). El código de desarrollo falla si " +
          "intenta cargarla; la apertura exigió una ruta explícita y auditada, y su resultado " +
          "permanece sin publicar mientras la auditoría siga pendiente.",
      },
      {
        title: "El dato crudo es inmutable",
        plain:
          "Lo descargado del exchange se conserva sin modificación. Las correcciones se " +
          "aplican sobre copias derivadas y quedan registradas.",
        technical:
          "data/raw es de solo lectura. Las observaciones extremas se marcan; nunca se " +
          "eliminan automáticamente.",
      },
      {
        title: "Toda cifra es regenerable",
        plain:
          "Cada número de esta página puede reproducirse: consta el fichero de origen, la " +
          "versión del código y la semilla aleatoria empleada.",
        technical:
          "Manifiesto por dataset con SHA-256, commit de git en cada artefacto y una única " +
          "semilla global de la que derivan todos los componentes estocásticos.",
      },
    ],
  },

  market: {
    eyebrow: "Datos del estudio",
    title: "El conjunto de datos, caracterizado",
    lead:
      "Todos los paneles siguientes se generan desde los ficheros que usa la investigación, " +
      "exportados por el propio pipeline. El área sombreada señala el periodo de reserva: se " +
      "dibuja para mostrar dónde comienza, y ningún número de esta página se eligió mirándolo.",
    assetAria: "Activo",
    seriesSuffix: "perpetuo USDT-M · velas de",
    loadError: "No se pudieron cargar los datos",
    metrics: {
      vol: "Volatilidad anualizada",
      worst: "Peor hora",
      drawdown: "Caída máxima",
      kurtosis: "Exceso de curtosis",
    },
    pricePanelTitle: "Precio de",
    pricePanelSubtitle: "Cierre diario, escala logarítmica",
    priceCaption:
      "Figura 1 · Escala logarítmica: en seis años el precio se multiplica y la escala lineal " +
      "aplastaría los primeros años contra el eje.",
    volPanelTitle: "Volatilidad",
    volPanelSubtitlePrefix: "Desviación típica móvil de",
    volPanelSubtitleSuffix: "días, anualizada",
    volCaption:
      "Figura 2 · La ventana es estrictamente retrospectiva: el valor de cada día se calcula " +
      "con las horas anteriores. La volatilidad no es estacionaria, y por ello una estrategia " +
      "de parámetros fijos se comporta de forma distinta según el régimen.",
    distPanelTitle: "Distribución de retornos",
    distPanelSubtitle: "Observada frente a una normal de igual media y desviación típica",
    distCaption:
      "Figura 3 · Eje vertical logarítmico. La curva discontinua es la predicción gaussiana; " +
      "la zona sombreada, lo que excede tres desviaciones típicas. La divergencia en los " +
      "extremos es la definición operativa de colas pesadas.",
    fatTailsCaption: "Movimientos extremos observados frente a los previstos por una normal",
    fatTailsMove: "Movimiento",
    fatTailsExpected: "Prevé la normal",
    fatTailsObserved: "Observado",
    fatTailsOver: "Más de",
    fatTailsFooterPrefix: "Sobre",
    fatTailsFooterSuffix: "horas de la partición de desarrollo.",
    kurtosisText:
      "Con exceso de curtosis de {kurtosis} y asimetría de {skew}, la normal no es una " +
      "aproximación imperfecta: es la distribución equivocada. Toda medida de riesgo que la " +
      "asuma subestima el suceso extremo.",
  },

  structure: {
    eyebrow: "Estructura del mercado",
    title: "Tres propiedades que condicionan cualquier estrategia",
    lead:
      "Cuándo se mueve el mercado, cuánto castiga mantener y el coste que casi nunca se " +
      "modela. Las tres, medidas sobre los mismos datos del estudio.",
    seasonTitle: "Volatilidad por hora y día",
    seasonCaption:
      "Figura 4 · Movimiento medio absoluto por barra de 1h (puntos básicos), hora UTC × día " +
      "de la semana, BTC 2020–2025. Destacan la apertura de la sesión estadounidense " +
      "(14–16 UTC) y la calma relativa del fin de semana.",
    seasonUnit: "pb",
    days: ["L", "M", "X", "J", "V", "S", "D"],
    underwaterTitle: "Distancia al máximo previo (comprar y mantener)",
    underwaterCaption:
      "Figura 5 · Profundidad de la serie de BTC respecto a su máximo previo, 2020–2025. " +
      "Incluso el activo en su mejor década pasa casi todo el tiempo por debajo de un máximo " +
      "anterior.",
    uwShare: "del tiempo por debajo de un máximo previo",
    uwMaxDd: "caída máxima del periodo",
    uwLongest: "días consecutivos bajo el agua (el peor tramo)",
    fundingTitle: "Funding: el tercer coste",
    fundingCaption:
      "Figura 6 · Media semanal del funding rate del perpetuo de BTC ({n} eventos de 8h, " +
      "2020–2025). Con tasa positiva, quien está largo paga; el motor del estudio lo cobra " +
      "en cada barra expuesta.",
    fundingMean: "coste medio anualizado de mantener un largo",
    fundingPositive: "de los eventos con tasa positiva (paga el largo)",
  },

  zoo: {
    eyebrow: "El denominador del estudio",
    title: "Las quince familias evaluadas, en conjunto",
    lead:
      "Cada línea es la equity media (diez semillas) de una familia sobre BTC fuera de " +
      "muestra. Se publica el conjunto completo: el número de intentos forma parte del " +
      "resultado.",
    bestLabel: "mejor media",
    worstLabel: "peor media",
    othersLabel: "familias restantes",
    startLine: "capital inicial",
    tooltipFamilies: "familias",
    tooltipBest: "mejor",
    tooltipWorst: "peor",
    caption:
      "Figura 11 · Ventana de prueba walk-forward concatenada (2022–2025), motor de búsqueda " +
      "aleatoria, media de diez semillas por familia. En color, la mejor y la peor media " +
      "finales; el resto en gris. Curvas decimadas para el trazado conservando valores exactos.",
    stats: {
      n: "familias con estudio multi-semilla completo",
      positive: "terminan por encima del capital inicial",
      best: "mejor curva media",
      worst: "peor curva media",
    },
    closing:
      "Con quince intentos, el azar por sí solo garantiza ganadores aparentes. La pregunta " +
      "relevante no es cuál subió, sino si alguna sube más de lo esperable por azar.",
    exploreLink: "Explorar las quince familias, semilla a semilla →",
  },

  anatomy: {
    eyebrow: "Anatomía de la búsqueda",
    title: "La mejor familia, por dentro",
    lead:
      "Cuatro cortes sobre volatility_breakout, la familia mejor clasificada del estudio — y " +
      "aun así rechazada: qué produce la búsqueda, cuánto depende de la semilla, dónde se " +
      "concentra la ganancia y si el optimizador importa.",
    fanTitle: "Diez semillas, diez resultados",
    fanCaption:
      "Figura 12 · Equity out-of-sample de cada semilla (líneas finas) y su media (gruesa), " +
      "frente a comprar y mantener. La dispersión entre semillas es parte del resultado, no " +
      "un detalle técnico.",
    fanAvg: "media de semillas",
    fanBh: "comprar y mantener",
    mountainTitle: "La montaña de intentos",
    mountainCaption:
      "Figura 13 · Sharpe de validación de las {n} evaluaciones (candidato × pliegue) de la " +
      "búsqueda aleatoria en diez semillas. La configuración publicada por cualquier vendedor " +
      "de estrategias es la cola derecha de una montaña como esta.",
    mountainStats: {
      n: "evaluaciones registradas",
      positive: "con Sharpe de validación positivo",
      median: "Sharpe mediano de la búsqueda",
      failed: "combinaciones inviables descartadas",
    },
    foldsTitle: "Retorno por pliegue walk-forward",
    foldsCaption:
      "Figura 14 · Retorno de test por pliegue temporal, media de diez semillas; los bigotes " +
      "marcan mínimo y máximo entre semillas. La ganancia no se reparte: se concentra en " +
      "ventanas concretas del calendario.",
    foldsStat1: "pliegues de quince terminan en positivo",
    foldsStat2: "de la ganancia media concentrada en los dos mejores pliegues",
    rsgaTitle: "Búsqueda aleatoria frente a algoritmo genético",
    rsgaCaption:
      "Figura 15 · Sharpe medio de test de los ganadores por pliegue, con presupuesto " +
      "idéntico (2.000 evaluaciones) y diez semillas por familia, BTC. Un optimizador más " +
      "sofisticado no encuentra más ventaja cuando no la hay: ambos terminan en negativo en " +
      "las cinco familias.",
    rs: "búsqueda aleatoria",
    ga: "algoritmo genético",
  },

  verdict: {
    eyebrow: "Resultado principal",
    titleWithData: "{n} familias evaluadas; ninguna supera el contraste",
    titleFallback: "Ninguna familia supera el contraste",
    lead:
      "Es el hallazgo central de la tesis, y es negativo. Conviene precisar por qué es un " +
      "resultado y no un fracaso: el diseño podía detectar una ventaja si existía, se le dio " +
      "la oportunidad, y tres diagnósticos independientes coinciden en su ausencia.",
    loadError: "No se pudo cargar la evidencia del estudio.",
    stats: {
      families: "familias de estrategia evaluadas",
      configs: "configuraciones distintas contrastadas",
      survive: "sobreviven a la corrección por comparaciones múltiples",
      pValue: "p-valor mínimo del estudio; el umbral exigido es {alpha}",
    },
    pbo: {
      label: "Probabilidad de sobreajuste (PBO)",
      title: "Seleccionar la mejor no aporta información",
      meterLow: "0 · la selección es informativa",
      meterMid: "0,5 · equivalente al azar",
      meterHigh: "1 · sistemáticamente inversa",
      meterCaption:
        "Probabilidad de que la mejor configuración dentro de muestra caiga en la mitad " +
        "inferior fuera de muestra, estimada sobre {splits} particiones.",
      body:
        "El valor queda prácticamente en el centro: la firma de una búsqueda que opera sobre " +
        "ruido. La configuración ganadora en una mitad de los datos no tiene más probabilidad " +
        "que cualquier otra de ganar en la siguiente.",
    },
    sensitivity: {
      label: "Análisis de sensibilidad",
      title: "El veredicto es robusto a la definición del denominador",
      body:
        "La objeción habitual a una corrección por comparaciones múltiples es que el número " +
        "de contrastes se elige a conveniencia. Aquí la conclusión no varía: bajo las cuatro " +
        "definiciones razonables del denominador, el umbral exigido queda por debajo del " +
        "mejor p-valor observado.",
      testsUnit: "contrastes",
      someSurvive: "sobrevive alguna",
      noneSurvive: "ninguna",
    },
    table: {
      title: "Resultados por familia",
      subtitle:
        "Retorno compuesto neto de comisiones, deslizamiento y funding sobre el periodo de " +
        "desarrollo, promediado entre semillas.",
      family: "Familia",
      asset: "Activo",
      ret: "Retorno",
      sharpe: "Sharpe",
      pValue: "p-valor",
      verdict: "Veredicto",
      rejected: "rechazada",
    },
    holdout: {
      label: "El periodo de reserva",
      title: "Se abrió una única vez; la cifra no se publica",
      p1:
        "La partición reservada se abrió sobre un candidato declarado de antemano, y su " +
        "lectura existe en disco. No se publica porque queda pendiente una auditoría de " +
        "procedencia: verificar que el candidato estaba efectivamente congelado antes de la " +
        "apertura. El historial no se ha reescrito para ocultarlo, porque hacerlo destruiría " +
        "precisamente la evidencia que hace auditable una apertura.",
      p2Prefix:
        "La conclusión del estudio no depende de esa lectura: el periodo de reserva era la " +
        "prueba confirmatoria de un candidato que la corrección por comparaciones múltiples ",
      p2Strong: "ya había rechazado",
      p2Suffix: ". Publicarla modificaría el énfasis de un párrafo, no el resultado.",
      statePrefix: "estado:",
      commitPrefix: "commit",
    },
  },

  nullDist: {
    eyebrow: "Contraste por aleatorización",
    title: "La mejor familia frente a su propio nulo",
    lead:
      "Las posiciones de la mejor familia se rotan a un punto aleatorio del tiempo, mil " +
      "veces por semilla, conservando exposición y costes. El gris es ese azar estructurado; " +
      "las líneas verdes, las diez ejecuciones reales.",
    xAxisLabel: "retorno total del periodo fuera de muestra",
    caption:
      "Figura 16 · {family} · {symbol} · {rotations} rotaciones (10 semillas × 1.000) · banda " +
      "sombreada: 95% central del nulo · misma semilla y parámetros que la figura homóloga " +
      "del estudio. Para la legibilidad, el histograma omite el 1% más extremo de la cola; la " +
      "banda y los percentiles se calculan sobre la muestra completa.",
    statInside: "ejecuciones reales dentro de la banda del nulo",
    statPercentiles: "percentiles de las diez ejecuciones: compatibles con el azar",
    simpleLabel: "Lectura no técnica",
    simpleStrong: "el backtest está midiendo el mercado, no la regla.",
    simpleLede: "Si una estrategia es indistinguible de sus propias posiciones rotadas, ",
    body:
      "Esta lectura no requiere estadística avanzada, y toda la estadística avanzada del " +
      "estudio — p-valores corregidos, Sharpe deflactado, PBO — converge en la misma " +
      "conclusión. Es la verificación visual del resultado principal, con idénticos costes, " +
      "idéntica exposición y ninguna información.",
    sweepTitle: "Monte Carlo: el margen frente a los costes",
    sweepCaption:
      "Figura 17 · Retorno total al multiplicar la estructura de costes por ×0–×4, unidad de " +
      "semilla mediana del estudio Monte Carlo (cuaderno 07). El punto de equilibrio se " +
      "interpola entre los dos multiplicadores que cambian de signo.",
    sweepBreakeven: "multiplicador de costes que anula el retorno",
    sweepZeroCost: "retorno con costes cero (el bruto que erosionan)",
    sweepBody:
      "Todo el aparente margen de la mejor familia vive por debajo de ×2,3 los costes " +
      "reales. Una estimación optimista del deslizamiento, una comisión mal negociada o un " +
      "funding adverso bastan para consumirlo: el resultado no tiene holgura económica.",
    sweepAxis: "multiplicador de costes",
  },

  mlfilter: {
    eyebrow: "Aprendizaje automático",
    title: "El filtro que aprende a no operar",
    lead:
      "Meta-labeling sobre datos reales: un clasificador (regresión logística, random " +
      "forest, LightGBM) decide qué señales de la estrategia base ejecutar y cuándo " +
      "abstenerse.",
    barPrimary: "estrategia base",
    barMeta: "con filtro ML",
    caption:
      "Figura 18 · Retorno total out-of-sample de la estrategia base y de la misma " +
      "estrategia filtrada. {family} · {symbol} · {n} eventos etiquetados por triple " +
      "barrera con costes · validación por pliegues cronológicos purgados.",
    roc: "ROC mediana del clasificador — compatible con el azar",
    abst: "tasa de abstención del filtro",
    folds: "pliegues rentables tras filtrar",
    body:
      "El filtro mejora el resultado en los cuatro pliegues, pero por la vía de la " +
      "abstención: reduce pérdidas, no genera beneficio. Con un ROC de 0,55 sobre ~45 " +
      "eventos por pliegue, la capacidad predictiva es indistinguible del azar; la mejora " +
      "es economía de costes, no predicción. Es la lectura honesta de la capa de ML, y por " +
      "eso se clasifica como infraestructura y no como candidato operativo.",
  },

  funded: {
    eyebrow: "Aplicación: evaluaciones de fondeo",
    title: "La tasa de aprobación bajo la hipótesis nula",
    lead:
      "Las reglas publicadas de dos empresas reales de fondeo, aplicadas a mil trayectorias " +
      "de la mejor estrategia del estudio y a una moneda equilibrada con sus mismos tiempos " +
      "y costes. Ninguno de los dos procesos contiene información; ambos aprueban.",
    phase1Title: "Fase 1",
    bothTitle: "Ambas fases",
    armStrategy: "estrategia",
    armCoin: "moneda equilibrada",
    caption:
      "Figura 19 · {paths} trayectorias por brazo. Reglas transcritas de las páginas públicas " +
      "de cada firma (fuentes y fecha de consulta en el artefacto). Las reglas cualitativas " +
      "no modeladas — consistencia, stop obligatorio, mínimo de días — solo reducirían las " +
      "tasas, por lo que estas cifras son cotas superiores.",
    simpleLabel: "Lectura no técnica",
    simpleStrong: "no constituye evidencia de habilidad.",
    simpleLede: "Superar una evaluación de fondeo ",
    body:
      "Una estrategia sin ventaja demostrable supera la fase 1 entre el 14% y el 18% de las " +
      "veces; una moneda con sus mismos costes, entre el 9% y el 13%. La diferencia es del " +
      "orden de su propio error de muestreo. Con un volumen suficiente de aspirantes, el azar " +
      "produce «traders verificados» de forma sistemática: es el mecanismo, aquí cuantificado, " +
      "por el que la industria de evaluaciones genera casos aparentes de éxito.",
    footnote:
      "Modificar las reglas altera los porcentajes; no altera de qué lado del azar se " +
      "encuentra la estrategia.",
  },

  numbers: {
    eyebrow: "El estudio en cifras",
    title: "Todo el trabajo, contado",
    lead: "Cada cifra procede de un artefacto del repositorio y puede regenerarse.",
    bars: "velas horarias de desarrollo (BTC + ETH)",
    runs: "ejecuciones de experimento registradas",
    familiesRegistered: "familias de estrategia implementadas",
    familiesClosure: "familias en el cierre estadístico",
    configs: "evaluaciones de búsqueda en la mejor familia",
    rotations: "rotaciones del contraste de aleatorización",
    maxTests: "contrastes en el denominador más exigente",
    promoted: "estrategias promovidas",
  },

  roadmap: {
    eyebrow: "Estado del proyecto",
    title: "Fases completadas y trabajo futuro",
    lead:
      "Dos de las puertas de decisión se cerraron en negativo y así están documentadas. En " +
      "investigación, un cierre negativo con criterios prefijados es un resultado, no un " +
      "contratiempo.",
    stepperAria: "Progreso de las fases",
    stepperDone: "completadas",
    stepperReview: "en revisión",
    stepperPlanned: "planificadas",
    phases: [
      {
        id: "fase-1",
        period: "Fase 1",
        title: "Datos y análisis exploratorio",
        status: "done",
        summary:
          "Descarga, validación y EDA completos sobre BTC y ETH perpetuo, con manifiestos y " +
          "hashes por dataset. Constituye la base del resto del estudio.",
        source: "docs/roadmap/current_state.md",
      },
      {
        id: "r2-r3",
        period: "Puertas R2–R3",
        title: "Primeras familias de estrategias",
        status: "done",
        summary:
          "Cinco familias evaluadas con walk-forward, costes y batería de robustez. Ninguna " +
          "promocionó: la puerta se cerró en negativo conforme a los criterios prefijados.",
        source: "reports/r3_gate/…/thesis_report.md",
      },
      {
        id: "s1",
        period: "Puerta S1",
        title: "Expansión controlada",
        status: "done",
        summary:
          "Cuatro familias adicionales llevadas a piloto. Las cuatro terminaron con retorno " +
          "compuesto negativo; ninguna activó el criterio de continuación.",
        source: "docs/roadmap/gate_s1b_outcome.md",
      },
      {
        id: "s2",
        period: "Puerta S2",
        title: "Segunda expansión",
        status: "in-review",
        summary:
          "Nuevas familias sobre datos de desarrollo, con la misma geometría temporal y los " +
          "mismos presupuestos. Ninguna activó el criterio de señal parcial.",
        source: "rama feat/s2-evidence-and-strategy-lab",
      },
      {
        id: "m1",
        period: "Fases M1–M2",
        title: "Etiquetado y filtro de aprendizaje automático",
        status: "in-review",
        summary:
          "Triple barrera con costes incorporados y un filtro que aprende cuándo no operar. " +
          "Validado sobre mercados sintéticos: recupera una ventaja introducida y se abstiene " +
          "ante ruido puro. No constituye un candidato operativo.",
        source: "rama feat/m1m2-synthetic-validation",
      },
      {
        id: "holdout",
        period: "Evaluación confirmatoria",
        title: "Apertura del periodo de reserva",
        status: "in-review",
        summary:
          "Un único contraste sobre los seis meses reservados, con candidato declarado de " +
          "antemano. Se ejecutó; la lectura queda retenida a la espera de la auditoría de " +
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
          "Especificado en el roadmap; sin implementar.",
        source: "docs/roadmap/master_roadmap.md",
      },
    ],
  },

  cta: {
    title: "El código, los datos y los resultados negativos son públicos",
    body:
      "El repositorio permite regenerar cada cifra de esta página y auditar el rastro de la " +
      "única apertura del periodo de reserva. La forma más útil de contribuir es señalar un " +
      "error metodológico mediante una issue.",
    repo: "Ver el repositorio",
    panel: "Entrar al panel de investigación",
    disclaimer:
      "Proyecto académico. No constituye asesoramiento financiero, no gestiona capital real y " +
      "no está conectado a ningún exchange.",
  },

  footer: {
    tagline:
      "Descubrimiento y validación reproducible de estrategias intradía sobre futuros " +
      "perpetuos USDT-M de BTC y ETH.",
    disclaimer:
      "Contenido educativo e informativo. No constituye asesoramiento financiero ni " +
      "recomendación de inversión. La operativa con derivados conlleva alto riesgo de " +
      "pérdida; los resultados pasados no garantizan resultados futuros.",
    generated: "datos generados",
    contract: "contrato",
    nav: {
      panel: "Panel",
      data: "Datos y EDA",
      methodology: "Metodología",
      privacy: "Privacidad",
      legal: "Aviso legal",
    },
    footAria: "Pie",
  },
} as const;
