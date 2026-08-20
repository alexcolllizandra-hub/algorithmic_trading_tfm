// English landing copy. Mirrors ./es.ts exactly in structure; the Dictionary
// type in ./index.ts enforces the match at compile time.

import type { LandingCopy } from "./index";

export const en: LandingCopy = {
  header: {
    links: [
      { href: "#marco", label: "Framework" },
      { href: "#sesgo", label: "Selection bias" },
      { href: "#metodo", label: "Method" },
      { href: "#datos", label: "Data" },
      { href: "#resultado", label: "Findings" },
      { href: "#estado", label: "Status" },
    ],
    panel: "Research panel",
    signIn: "Sign in",
    signOut: "Sign out",
    openMenu: "Open menu",
    closeMenu: "Close menu",
    sectionsAria: "Sections",
  },

  hero: {
    kicker: "Master's Thesis · Data Science · Open research",
    titleA: "Detection and validation of intraday strategies ",
    titleGradient: "under explicit selection-bias control",
    titleB: ".",
    sub:
      "A reproducible study on BTC and ETH perpetual futures: six years of data, " +
      "walk-forward validation, multiple-comparison correction, and a frozen holdout " +
      "period. The principal finding is negative and is published in full, because in " +
      "this domain a rigorous negative result is the finding.",
    ctaData: "View the study data",
    ctaPlain: "Non-technical reading",
    ctaPanel: "Research panel",
    stats: {
      bars: "hourly candles analysed",
      years: "years of market history",
      coverage: "series coverage, no gaps",
      holdout: "holdout period frozen since",
    },
  },

  plain: {
    eyebrow: "Conceptual framework",
    title: "The object of study, in three steps",
    lead:
      "This section states the problem without technical vocabulary. The rest of the page " +
      "develops each step with the study's data and methods.",
    steps: [
      {
        n: "01",
        title: "A systematic strategy is an explicit rule",
        body:
          "Systematic trading consists of fixing in writing what is bought, in what size, " +
          "and when it is sold. Because the rule is formalised, it can be repeated, " +
          "measured, and audited — the conditions required to treat it as an object of study.",
      },
      {
        n: "02",
        title: "The backtest evaluates it on the past",
        body:
          "Before committing capital, the rule is simulated on the available history: what " +
          "would it have produced over the last six years? That simulation is the backtest, " +
          "and it constitutes the primary evidence — and the primary source of error — in " +
          "this field.",
      },
      {
        n: "03",
        title: "The methodological problem is selection bias",
        body:
          "If the rule is adjusted until the past looks favourable, the result says nothing " +
          "about the future: it measures how much adjustment took place. Most of this " +
          "study's design exists to close that path, including the involuntary version of it.",
      },
    ],
    quote:
      "A negative result obtained with rigour is a valid result. A positive result " +
      "obtained with information from the future is not.",
    quoteFooter: "The criterion that orders every methodological decision in the project.",
  },

  concepts: {
    eyebrow: "Foundations",
    title: "Five concepts that determine whether a backtest is valid",
    lead:
      "Each card gives the formal definition and an everyday illustration. These are the " +
      "five error mechanisms the literature identifies most frequently in strategy " +
      "evaluation.",
    everydayLabel: "Illustration",
    seeMeasured: "See it measured",
    items: [
      {
        title: "Overfitting",
        technical:
          "A model with enough degrees of freedom memorises the noise in the sample: its " +
          "training error falls while its out-of-sample error grows.",
        everyday:
          "It is memorising last year's exam questions: a perfect score on that exam, a " +
          "fail on this year's.",
        punchline: "A backtest with exceptional metrics is, by default, overfitting.",
      },
      {
        title: "Market efficiency",
        technical:
          "If the price incorporates the available information, no rule based on that " +
          "information earns positive expected profit net of costs.",
        everyday:
          "The shortest supermarket queue stops being shortest as soon as everyone sees it: " +
          "the advantage disappears as it spreads.",
        punchline: "This is why the study's null hypothesis is the absence of an edge.",
      },
      {
        title: "Law of large numbers",
        technical:
          "The sample mean converges to the expectation as n grows. At small n, estimator " +
          "variance makes luck and skill indistinguishable.",
        everyday: "Ten tosses cannot distinguish a biased coin from a fair one; ten thousand can.",
        punchline: "Thirty trades do not constitute evidence.",
      },
      {
        title: "Kelly criterion",
        technical:
          "The capital fraction that maximises expected logarithmic growth. Betting above " +
          "the optimum reduces growth and raises the probability of ruin; the optimum is " +
          "also fragile to estimation error.",
        everyday:
          "Even in a favourable game, staking everything on each hand leads to ruin: " +
          "position size matters as much as being right.",
        punchline: "Being right and going broke are not mutually exclusive.",
      },
      {
        title: "Heavy tails",
        technical:
          "Returns exhibit far heavier tails than the normal distribution: extreme events " +
          "are orders of magnitude more frequent than the Gaussian model predicts.",
        everyday:
          "A dam sized for the worst flood of the last century offers no protection in the " +
          "year a larger one arrives.",
        punchline: "It is quantified below, on the study's own data.",
      },
    ],
  },

  overfitting: {
    eyebrow: "The central problem",
    title: "Selection bias, measured within this study",
    lead:
      "Evaluating many configurations and retaining the best produces favourable metrics " +
      "even when no signal exists. Here it is measured with the study's own searches.",
    loadErrorPrefix: "The study evidence could not be loaded. Generate the file with",
    simpleLabel: "Non-technical reading",
    simpleStrong: "The selected candidates do not keep their advantage.",
    simpleLede:
      "Consider a cohort of 3,000 candidates assessed in a preliminary test. The best are " +
      "retained and given an independent follow-up test. ",
    simpleAfter:
      "Not through any irregularity: in a cohort that large, some score highly by chance alone.",
    scatterBody:
      "Each point is a configuration that won its selection round. If the selection metric " +
      "were informative, the points would align with the dashed diagonal. The fitted line " +
      "is nearly flat: rank at selection barely predicts subsequent performance.",
    stats: {
      selected: "Mean Sharpe in the selection window",
      after: "Mean Sharpe in the subsequent test window",
      worsened: "configurations that deteriorate relative to selection",
      survives: "of the apparent edge that persists (100% would indicate informative selection)",
    },
    leak: {
      label: "The second error mechanism",
      title: "Look-ahead information leakage",
      p1:
        "A mis-specified indicator can incorporate data that was not knowable at decision " +
        "time. The symptom is not a failure: it is anomalously high performance. Here the " +
        "effect is reproduced deliberately — same rule, same data, same costs — allowing " +
        "one variant to observe 23 hours of the future.",
      p2:
        "The sign is irrelevant, since inverting the rule would suffice; what exposes the " +
        "leak is the magnitude. No legitimate result in this market approaches those figures.",
      variants: {
        causal: "Causal specification (past only)",
        leaky: "With look-ahead leakage",
        flipped: "With leakage, sign inverted",
        buyAndHold: "Buy and hold",
      },
      caption:
        "Figure 8 · Annualised Sharpe net of costs, in absolute value. “Buy and hold” " +
        "is the passive benchmark over the same period.",
    },
  },

  costs: {
    eyebrow: "Efficiency and costs",
    title: "The apparent edge against transaction costs",
    lead:
      "Efficiency predicts that no rule on public information survives net of costs. The " +
      "test: same strategy, same period, varying only the cost per trade.",
    panels: {
      erosionLabel: "Cost erosion",
      erosionTitle: "Where the edge crosses zero",
      erosionCaption:
        "Figure 9 · Annualised Sharpe on the development partition, varying only the " +
        "round-trip cost. All other conditions held fixed.",
      wedgeLabel: "Gross versus net",
      wedgeTitle: "The gap widens with turnover",
      wedgeCaption:
        "Figure 10 · Each pair of points is a moving-average configuration: above, the " +
        "result before costs; below, the same after fees, slippage, and funding.",
    },
    statCrossing: "round-trip cost at which the edge reaches zero",
    statBuyHold: "Buy-and-hold Sharpe over the same period",
    simpleLabel: "Non-technical reading",
    simpleStrong: "It is enough that participation has a price.",
    simpleLede: "Perfect efficiency is not required for the edge to disappear. ",
    body1Prefix:
      "The declining curve does not reflect a deteriorating strategy: it is the same rule " +
      "on the same data, and the only thing rising is the cost. At around ",
    body1Fallback: "a certain cost level",
    body1Suffix:
      " per round trip, the apparent edge reaches zero — and that level lies within the " +
      "range a real exchange charges.",
    body2:
      "The right panel explains why trading more is not a solution: the higher the " +
      "turnover, the wider the gap between gross and net. ",
    body2Accent: "Activity is not a source of return; it is a source of cost.",
    bpsUnit: "basis points",
  },

  pipeline: {
    eyebrow: "Study design",
    title: "From raw data to verdict, stage by stage",
    lead:
      "Each stage feeds the next and none can be skipped. The implementation status of " +
      "each is indicated.",
    statusLabel: {
      done: "Implemented",
      "in-review": "Under review",
      blocked: "Blocked",
      planned: "Planned",
    },
    steps: [
      {
        id: "datos",
        title: "Data",
        what: "Download of BTC and ETH perpetual candles from Binance Futures.",
        status: "done",
        detail:
          "Six and a half years of history from January 2020. The downloaded file is " +
          "immutable: every correction is applied to a derived, documented copy.",
      },
      {
        id: "validacion",
        title: "Data validation",
        what: "Integrity verification of the series.",
        status: "done",
        detail:
          "Gaps, duplicates, inconsistent candles (low above high), negative volumes. " +
          "Anomalies are flagged and reported; they are never silently removed.",
      },
      {
        id: "eda",
        title: "Exploratory analysis",
        what: "Characterising the market before modelling it.",
        status: "done",
        detail:
          "Volatility, distribution tails, regimes, seasonality, funding, and cross-asset " +
          "dependence. This phase determines which hypotheses merit testing.",
      },
      {
        id: "features",
        title: "Indicators",
        what: "Variables built exclusively from past information.",
        status: "done",
        detail:
          "Every indicator passes a causality test: truncating the future of the dataset " +
          "cannot change any past value.",
      },
      {
        id: "estrategias",
        title: "Strategies",
        what: "Explicit, auditable rules — not black boxes.",
        status: "done",
        detail:
          "Moving-average crossover, range breakout, mean reversion, multi-timeframe " +
          "consensus. The design criterion: every rule must be statable in one sentence.",
      },
      {
        id: "backtest",
        title: "Backtest with costs",
        what: "Historical simulation under the full cost structure.",
        status: "done",
        detail:
          "Fees, slippage, and funding. The order is decided on the closed candle and " +
          "executed at the next open, never at the price that generated the signal.",
      },
      {
        id: "validacion-temporal",
        title: "Temporal validation",
        what: "Train on the past, evaluate on the future, repeatedly.",
        status: "done",
        detail:
          "Walk-forward with purge and embargo, random search and a genetic algorithm on " +
          "identical budgets, and explicit accounting of the number of tests performed.",
      },
      {
        id: "meta",
        title: "Machine-learning filter",
        what: "A classifier that decides when not to trade.",
        status: "in-review",
        detail:
          "Triple-barrier labelling and a classifier that filters the base strategy's " +
          "signals. Validated on synthetic markets with known ground truth; retained as " +
          "infrastructure because no base strategy justified its use.",
      },
      {
        id: "holdout",
        title: "Confirmatory evaluation",
        what: "Single opening of the holdout period.",
        status: "in-review",
        detail:
          "Opened exactly once, on a candidate declared in advance, and its reading exists " +
          "on disk. A provenance audit verifying the candidate was frozen beforehand " +
          "remains pending; until then, the figure is not published.",
      },
      {
        id: "riesgo",
        title: "Risk and portfolio",
        what: "Position sizing and strategy combination.",
        status: "planned",
        detail:
          "Without object while no strategy survives the preceding stages. Specified in " +
          "the roadmap; not implemented.",
      },
    ],
  },

  architecture: {
    eyebrow: "System architecture",
    title: "Six layers, each with its safeguard",
    lead:
      "Data enters at the first layer and leaves the last as a verdict. What makes the " +
      "result defensible is not any single layer but that all of them fail closed: on an " +
      "unforeseen condition, the system stops rather than proceeding on an assumption.",
    howBuilt: "Implementation",
    lockLabel: "Safeguard",
    layers: [
      {
        id: "datos",
        name: "Data",
        role: "Persist the market and never touch it again",
        plain:
          "Candles are downloaded once and kept as-is. Every later transformation lives in " +
          "a derived copy with documented provenance.",
        technical:
          "Bulk download from data.binance.vision with CCXT incrementals. Every dataset " +
          "carries a manifest with origin, symbol, period, row count, and SHA-256. Schema " +
          "validation: gaps, duplicates, inconsistent OHLC, negative volume.",
        guard: "data/raw is read-only. Extremes are flagged, never deleted.",
        modules: ["data/providers", "data/manifest", "validation/schemas"],
      },
      {
        id: "features",
        name: "Indicators",
        role: "Compute only what was knowable at each instant",
        plain:
          "Every indicator looks strictly backwards: truncating the file's future cannot " +
          "alter any past value.",
        technical:
          "Declarative indicator registry: each declares its inputs, window, the instant " +
          "its value becomes knowable, and how many initial rows stay empty. Contextual " +
          "indicators are explicitly lagged before use.",
        guard:
          "Seven causality tests run on the real data, not on fixtures. A deliberately " +
          "planted leak fails them immediately.",
        modules: ["features/spec", "features/causal", "features/registry"],
      },
      {
        id: "estrategias",
        name: "Strategies",
        role: "Rules statable in one sentence",
        plain:
          "No black boxes: moving-average crossover, range breakout, mean reversion, " +
          "funding, BTC–ETH confirmation. Every rule evaluated is legible and auditable.",
        technical:
          "Thirteen families with a typed, finite parameter space, repair of invalid " +
          "combinations, and a canonical hash per candidate. A single engine serves the " +
          "nine Candle Range Theory variants.",
        guard: "The space is declared before searching and never widened after seeing results.",
        modules: ["strategies/*", "search/space", "crt/*"],
      },
      {
        id: "backtest",
        name: "Backtest",
        role: "Simulate under the full cost structure",
        plain:
          "The order is decided on the closed candle and executed at the next open, never " +
          "at the price the signal just revealed.",
        technical:
          "Per-candle ledger with signal, position, execution price, gross return, fee, " +
          "slippage, funding, and net return. A long-to-short flip moves two units of " +
          "notional and is charged as two.",
        guard:
          "If the experiment requires funding and no funding series exists, the engine " +
          "fails rather than assuming zero.",
        modules: ["backtesting/engine", "backtesting/metrics"],
      },
      {
        id: "validacion",
        name: "Temporal validation",
        role: "Manufacture genuine future, fifteen times",
        plain:
          "Train on the past, evaluate on what came after, advancing through the calendar, " +
          "with a separation interval so no trade crosses the boundary.",
        technical:
          "Expanding walk-forward: fifteen folds with anchored training and non-overlapping " +
          "90-day selection and test windows. Purge and embargo derived from the maximum " +
          "holding period, not chosen ad hoc.",
        guard:
          "No fold can reach the holdout period. The check raises an exception, not a " +
          "warning.",
        modules: ["validation/walk_forward", "search/evaluator"],
      },
      {
        id: "inferencia",
        name: "Inference",
        role: "Account for every test performed",
        plain:
          "When thirteen families are evaluated, some will look good by chance. The study " +
          "counts every test and corrects the result accordingly.",
        technical:
          "Ten seeds per unit, with the inference unit at asset × fold and seeds averaged " +
          "within each cell. Holm-Bonferroni and Benjamini-Hochberg correction, deflated " +
          "Sharpe ratio, and probability of backtest overfitting (PBO).",
        guard:
          "The verdict is verified under four definitions of the test count, from thirteen " +
          "to nearly half a million.",
        modules: ["evaluation/multiple_testing", "evaluation/study_robustness"],
      },
    ],
  },

  integrity: {
    eyebrow: "Methodological integrity",
    title: "Four rules against self-deception",
    lead:
      "In strategy evaluation, the main source of error is the researcher. These rules are " +
      "implemented in code and verified by tests, not entrusted to personal discipline.",
    techLabel: "Formally",
    receiptCaption: "Actual manifest of one of the datasets behind this page",
    rowRows: "rows",
    rowGenerated: "generated",
    principles: [
      {
        title: "Temporal order is inviolable",
        plain:
          "The rule is trained on the past and evaluated on what came after. Permuting the " +
          "dates would be sitting the exam with the answers in view.",
        technical:
          "Strictly chronological partitions, with purge and embargo between training and " +
          "test so no trade crosses the boundary.",
      },
      {
        title: "Six months in reserve",
        plain:
          "The final six months of data were set aside from the start and played no part in " +
          "any decision. They were opened exactly once, at the end; the reading is withheld " +
          "pending a provenance audit, and the conclusion does not depend on it.",
        technical:
          "Reserved partition over [2026-01-01, 2026-07-01). Development code fails if it " +
          "attempts to load it; the opening required an explicit, audited path, and its " +
          "result remains unpublished while the audit is pending.",
      },
      {
        title: "Raw data is immutable",
        plain:
          "What was downloaded from the exchange is kept unmodified. Corrections are applied " +
          "to derived copies and recorded.",
        technical:
          "data/raw is read-only. Extreme observations are flagged; they are never removed " +
          "automatically.",
      },
      {
        title: "Every figure is regenerable",
        plain:
          "Every number on this page can be reproduced: the source file, code version, and " +
          "random seed are all on record.",
        technical:
          "Per-dataset manifest with SHA-256, git commit in every artifact, and a single " +
          "global seed from which every stochastic component derives.",
      },
    ],
  },

  market: {
    eyebrow: "Study data",
    title: "The dataset, characterised",
    lead:
      "Every panel below is generated from the files the research uses, exported by the " +
      "pipeline itself. The shaded area marks the holdout period: it is drawn to show where " +
      "it begins, and no number on this page was chosen by looking at it.",
    assetAria: "Asset",
    seriesSuffix: "USDT-M perpetual · candles of",
    loadError: "The data could not be loaded",
    metrics: {
      vol: "Annualised volatility",
      worst: "Worst hour",
      drawdown: "Maximum drawdown",
      kurtosis: "Excess kurtosis",
    },
    pricePanelTitle: "Price of",
    pricePanelSubtitle: "Daily close, logarithmic scale",
    priceCaption:
      "Figure 1 · Logarithmic scale: over six years the price multiplies, and a linear " +
      "scale would crush the early years against the axis.",
    volPanelTitle: "Volatility",
    volPanelSubtitlePrefix: "Rolling standard deviation over",
    volPanelSubtitleSuffix: "days, annualised",
    volCaption:
      "Figure 2 · The window is strictly backward-looking: each day's value is computed " +
      "from the preceding hours. Volatility is not stationary, which is why a fixed-" +
      "parameter strategy behaves differently across regimes.",
    distPanelTitle: "Return distribution",
    distPanelSubtitle: "Observed versus a normal with the same mean and standard deviation",
    distCaption:
      "Figure 3 · Logarithmic vertical axis. The dashed curve is the Gaussian prediction; " +
      "the shaded zone, what lies beyond three standard deviations. The divergence in the " +
      "extremes is the operational definition of heavy tails.",
    fatTailsCaption: "Extreme moves observed versus those predicted by a normal",
    fatTailsMove: "Move",
    fatTailsExpected: "Normal predicts",
    fatTailsObserved: "Observed",
    fatTailsOver: "More than",
    fatTailsFooterPrefix: "Over",
    fatTailsFooterSuffix: "hours of the development partition.",
    kurtosisText:
      "With excess kurtosis of {kurtosis} and skewness of {skew}, the normal is not an " +
      "imperfect approximation: it is the wrong distribution. Any risk measure that assumes " +
      "it underestimates the extreme event.",
  },

  structure: {
    eyebrow: "Market structure",
    title: "Three properties that constrain any strategy",
    lead:
      "When the market moves, how much holding punishes, and the cost almost nobody models. " +
      "All three measured on the study's own data.",
    seasonTitle: "Volatility by hour and day",
    seasonCaption:
      "Figure 4 · Mean absolute move per 1h bar (basis points), UTC hour × weekday, BTC " +
      "2020–2025. The US session open (14–16 UTC) and the relative weekend calm stand out.",
    seasonUnit: "bps",
    days: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    underwaterTitle: "Distance from the prior peak (buy and hold)",
    underwaterCaption:
      "Figure 5 · Depth of the BTC series relative to its prior maximum, 2020–2025. Even the " +
      "asset in its best decade spends nearly all its time below an earlier peak.",
    uwShare: "of the time below a prior peak",
    uwMaxDd: "maximum drawdown of the period",
    uwLongest: "consecutive days under water (worst stretch)",
    fundingTitle: "Funding: the third cost",
    fundingCaption:
      "Figure 6 · Weekly mean funding rate of the BTC perpetual ({n} 8h events, 2020–2025). " +
      "When the rate is positive, longs pay; the study's engine charges it on every exposed " +
      "bar.",
    fundingMean: "mean annualised cost of holding a long",
    fundingPositive: "of events with a positive rate (longs pay)",
  },

  zoo: {
    eyebrow: "The study's denominator",
    title: "All fifteen families evaluated, together",
    lead:
      "Each line is the seed-averaged equity (ten seeds) of one family on BTC out of " +
      "sample. The full set is published: the number of attempts is part of the result.",
    bestLabel: "best average",
    worstLabel: "worst average",
    othersLabel: "remaining families",
    startLine: "initial capital",
    tooltipFamilies: "families",
    tooltipBest: "best",
    tooltipWorst: "worst",
    caption:
      "Figure 11 · Concatenated walk-forward test window (2022–2025), random-search engine, " +
      "average of ten seeds per family. In colour, the best and worst final averages; the " +
      "rest in grey. Curves decimated for drawing while preserving exact values.",
    stats: {
      n: "families with a complete multi-seed study",
      positive: "finish above initial capital",
      best: "best average curve",
      worst: "worst average curve",
    },
    closing:
      "With fifteen attempts, chance alone guarantees apparent winners. The relevant " +
      "question is not which went up, but whether any rises more than chance would produce.",
    exploreLink: "Explore all fifteen families, seed by seed →",
  },

  anatomy: {
    eyebrow: "Anatomy of the search",
    title: "The best family, from the inside",
    lead:
      "Four cuts through volatility_breakout, the study's best-ranked family — and still " +
      "rejected: what the search produces, how much depends on the seed, where the gains " +
      "concentrate, and whether the optimizer matters.",
    fanTitle: "Ten seeds, ten outcomes",
    fanCaption:
      "Figure 12 · Out-of-sample equity of each seed (thin lines) and their average (thick), " +
      "against buy and hold. The dispersion across seeds is part of the result, not a " +
      "technical detail.",
    fanAvg: "seed average",
    fanBh: "buy and hold",
    mountainTitle: "The mountain of attempts",
    mountainCaption:
      "Figure 13 · Validation Sharpe of the {n} evaluations (candidate × fold) of the random " +
      "search across ten seeds. The configuration any strategy vendor publishes is the right " +
      "tail of a mountain like this one.",
    mountainStats: {
      n: "evaluations recorded",
      positive: "with positive validation Sharpe",
      median: "median Sharpe of the search",
      failed: "infeasible combinations discarded",
    },
    foldsTitle: "Return per walk-forward fold",
    foldsCaption:
      "Figure 14 · Test return per temporal fold, average of ten seeds; whiskers mark the " +
      "minimum and maximum across seeds. Gains do not spread out: they concentrate in " +
      "specific calendar windows.",
    foldsStat1: "folds out of fifteen finish positive",
    foldsStat2: "of the mean gains concentrated in the two best folds",
    rsgaTitle: "Random search versus genetic algorithm",
    rsgaCaption:
      "Figure 15 · Mean test Sharpe of per-fold winners, identical budget (2,000 " +
      "evaluations) and ten seeds per family, BTC. A more sophisticated optimizer finds no " +
      "more edge when there is none: both end negative across all five families.",
    rs: "random search",
    ga: "genetic algorithm",
  },

  verdict: {
    eyebrow: "Principal finding",
    titleWithData: "{n} families evaluated; none survives the test",
    titleFallback: "No family survives the test",
    lead:
      "This is the thesis's central finding, and it is negative. It is worth stating why " +
      "it is a result and not a failure: the design could have detected an edge if one " +
      "existed, it was given the opportunity, and three independent diagnostics agree on " +
      "its absence.",
    loadError: "The study evidence could not be loaded.",
    stats: {
      families: "strategy families evaluated",
      configs: "distinct configurations tested",
      survive: "survive the multiple-comparison correction",
      pValue: "smallest p-value in the study; the required threshold is {alpha}",
    },
    pbo: {
      label: "Probability of backtest overfitting (PBO)",
      title: "Selecting the best carries no information",
      meterLow: "0 · selection is informative",
      meterMid: "0.5 · equivalent to chance",
      meterHigh: "1 · systematically inverted",
      meterCaption:
        "Probability that the best in-sample configuration falls in the lower half out of " +
        "sample, estimated over {splits} partitions.",
      body:
        "The value sits almost exactly at the centre: the signature of a search operating " +
        "on noise. The winning configuration in one half of the data is no more likely " +
        "than any other to win in the next.",
    },
    sensitivity: {
      label: "Sensitivity analysis",
      title: "The verdict is robust to the denominator definition",
      body:
        "The usual objection to a multiple-comparison correction is that the number of " +
        "tests is chosen conveniently. Here the conclusion does not change: under all four " +
        "reasonable definitions of the denominator, the required threshold stays below the " +
        "best observed p-value.",
      testsUnit: "tests",
      someSurvive: "some survive",
      noneSurvive: "none",
    },
    table: {
      title: "Results by family",
      subtitle:
        "Compound return net of fees, slippage, and funding over the development period, " +
        "averaged across seeds.",
      family: "Family",
      asset: "Asset",
      ret: "Return",
      sharpe: "Sharpe",
      pValue: "p-value",
      verdict: "Verdict",
      rejected: "rejected",
    },
    holdout: {
      label: "The holdout period",
      title: "Opened exactly once; the figure is not published",
      p1:
        "The reserved partition was opened on a candidate declared in advance, and its " +
        "reading exists on disk. It is not published because a provenance audit remains " +
        "pending: verifying that the candidate was genuinely frozen before the opening. " +
        "The history has not been rewritten to conceal it, because doing so would destroy " +
        "precisely the evidence that makes an opening auditable.",
      p2Prefix:
        "The study's conclusion does not depend on that reading: the holdout was the " +
        "confirmatory test of a candidate the multiple-comparison correction ",
      p2Strong: "had already rejected",
      p2Suffix: ". Publishing it would change the emphasis of one paragraph, not the result.",
      statePrefix: "state:",
      commitPrefix: "commit",
    },
  },

  nullDist: {
    eyebrow: "Randomisation test",
    title: "The best family against its own null",
    lead:
      "The best family's positions are rotated to a random point in time, a thousand times " +
      "per seed, preserving exposure and costs. The grey is that structured chance; the " +
      "green lines, the ten real runs.",
    xAxisLabel: "total return over the out-of-sample period",
    caption:
      "Figure 16 · {family} · {symbol} · {rotations} rotations (10 seeds × 1,000) · shaded " +
      "band: central 95% of the null · same seed and parameters as the study's homologous " +
      "figure. For readability the histogram omits the most extreme 1% of the tail; the " +
      "band and percentiles are computed on the full sample.",
    statInside: "real runs inside the null band",
    statPercentiles: "percentiles of the ten runs: consistent with chance",
    simpleLabel: "Non-technical reading",
    simpleStrong: "the backtest is measuring the market, not the rule.",
    simpleLede: "If a strategy is indistinguishable from its own rotated positions, ",
    body:
      "This reading requires no advanced statistics, and all of the study's advanced " +
      "statistics — corrected p-values, deflated Sharpe, PBO — converge on the same " +
      "conclusion. It is the visual verification of the principal finding, under identical " +
      "costs, identical exposure, and zero information.",
  },

  mlfilter: {
    eyebrow: "Machine learning",
    title: "The filter that learns not to trade",
    lead:
      "Meta-labeling on real data: a classifier (logistic regression, random forest, " +
      "LightGBM) decides which of the base strategy's signals to execute and when to " +
      "abstain.",
    barPrimary: "base strategy",
    barMeta: "with ML filter",
    caption:
      "Figure 17 · Out-of-sample total return of the base strategy and of the same strategy " +
      "filtered. {family} · {symbol} · {n} events labelled by triple barrier with embedded " +
      "costs · validation on purged chronological folds.",
    roc: "median classifier ROC — consistent with chance",
    abst: "filter abstention rate",
    folds: "profitable folds after filtering",
    body:
      "The filter improves the outcome in all four folds, but through abstention: it cuts " +
      "losses rather than generating profit. With a ROC of 0.55 on ~45 events per fold, the " +
      "predictive power is indistinguishable from chance; the improvement is cost economics, " +
      "not prediction. That is the honest reading of the ML layer, and why it is classified " +
      "as infrastructure rather than an operational candidate.",
  },

  funded: {
    eyebrow: "Application: funded-account evaluations",
    title: "The pass rate under the null hypothesis",
    lead:
      "The published rules of two real prop firms, applied to a thousand paths of the " +
      "study's best strategy and to a fair coin with the same trade timing and costs. " +
      "Neither process contains information; both pass.",
    phase1Title: "Phase 1",
    bothTitle: "Both phases",
    armStrategy: "strategy",
    armCoin: "fair coin",
    caption:
      "Figure 18 · {paths} paths per arm. Rules transcribed from each firm's public pages " +
      "(sources and retrieval date in the artifact). Unmodelled qualitative rules — " +
      "consistency, mandatory stop, minimum trading days — would only lower the rates, so " +
      "these figures are upper bounds.",
    simpleLabel: "Non-technical reading",
    simpleStrong: "is not evidence of skill.",
    simpleLede: "Passing a funding evaluation ",
    body:
      "A strategy with no demonstrable edge passes phase 1 between 14% and 18% of the " +
      "time; a coin with the same costs, between 9% and 13%. The difference is of the " +
      "order of its own sampling error. With enough applicants, chance produces “verified " +
      "traders” systematically: this is the mechanism, quantified here, by which the " +
      "evaluation industry generates apparent success stories.",
    footnote:
      "Changing the rules changes the percentages; it does not change which side of chance " +
      "the strategy sits on.",
  },

  roadmap: {
    eyebrow: "Project status",
    title: "Completed phases and future work",
    lead:
      "Two decision gates closed negative and are documented as such. In research, a " +
      "negative closure under pre-specified criteria is a result, not a setback.",
    phases: [
      {
        id: "fase-1",
        period: "Phase 1",
        title: "Data and exploratory analysis",
        status: "done",
        summary:
          "Complete download, validation, and EDA on BTC and ETH perpetuals, with per-" +
          "dataset manifests and hashes. The foundation for the rest of the study.",
        source: "docs/roadmap/current_state.md",
      },
      {
        id: "r2-r3",
        period: "Gates R2–R3",
        title: "First strategy families",
        status: "done",
        summary:
          "Five families evaluated with walk-forward, costs, and a robustness battery. " +
          "None promoted: the gate closed negative under the pre-specified criteria.",
        source: "reports/r3_gate/…/thesis_report.md",
      },
      {
        id: "s1",
        period: "Gate S1",
        title: "Controlled expansion",
        status: "done",
        summary:
          "Four additional families taken to pilot. All four ended with negative compound " +
          "return; none triggered the continuation criterion.",
        source: "docs/roadmap/gate_s1b_outcome.md",
      },
      {
        id: "s2",
        period: "Gate S2",
        title: "Second expansion",
        status: "in-review",
        summary:
          "New families on development data, with the same temporal geometry and budgets. " +
          "None triggered the partial-signal criterion.",
        source: "branch feat/s2-evidence-and-strategy-lab",
      },
      {
        id: "m1",
        period: "Phases M1–M2",
        title: "Labelling and machine-learning filter",
        status: "in-review",
        summary:
          "Triple-barrier labelling with embedded costs and a filter that learns when not " +
          "to trade. Validated on synthetic markets: it recovers a planted edge and " +
          "abstains on pure noise. Not an operational candidate.",
        source: "branch feat/m1m2-synthetic-validation",
      },
      {
        id: "holdout",
        period: "Confirmatory evaluation",
        title: "Opening of the holdout period",
        status: "in-review",
        summary:
          "A single test on the reserved six months, with the candidate declared in " +
          "advance. It ran; the reading is withheld pending the provenance audit that " +
          "would make it citable.",
        source: "reports/study_closure/final_holdout.md",
      },
      {
        id: "cartera",
        period: "Phases P1–P3",
        title: "Portfolio, risk, and simulation",
        status: "planned",
        summary:
          "Position sizing, strategy combination, and execution simulation. Specified in " +
          "the roadmap; not implemented.",
        source: "docs/roadmap/master_roadmap.md",
      },
    ],
  },

  cta: {
    title: "The code, the data, and the negative results are public",
    body:
      "The repository allows every figure on this page to be regenerated and the trail of " +
      "the single holdout opening to be audited. The most useful way to contribute is to " +
      "point out a methodological error through an issue.",
    repo: "View the repository",
    panel: "Enter the research panel",
    disclaimer:
      "Academic project. Not financial advice; it manages no real capital and is not " +
      "connected to any exchange.",
  },

  footer: {
    tagline:
      "Reproducible discovery and validation of intraday strategies on BTC and ETH USDT-M " +
      "perpetual futures.",
    disclaimer:
      "Educational and informational content. Not financial advice or an investment " +
      "recommendation. Trading derivatives carries a high risk of loss; past results do " +
      "not guarantee future results.",
    generated: "data generated",
    contract: "contract",
    nav: {
      panel: "Panel",
      data: "Data & EDA",
      methodology: "Methodology",
      privacy: "Privacy",
      legal: "Legal notice",
    },
    footAria: "Footer",
  },
};
