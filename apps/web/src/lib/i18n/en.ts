/**
 * English copy for the perp-lab research platform.
 *
 * Typed as `Dictionary` (the shape of `es`) in `@/lib/i18n`, so a missing key
 * fails the build instead of rendering blank. Numbers inside interpolated
 * strings keep their placeholder form; decimal separators in prose follow the
 * locale, which is why "0.5" here reads "0,5" in the Spanish file.
 */

export const en = {
  app: {
    name: "perp-lab",
    tagline: "research platform",
    apiOnline: "API online",
    apiOffline: "API offline",
    runs: "runs",
  },

  nav: {
    overview: { label: "Overview", description: "Phases, evidence and warnings" },
    guia: { label: "Guide", description: "A 13-panel walkthrough" },
    datosEda: { label: "Data & EDA", description: "Coverage, timeline and findings" },
    metodologia: { label: "Methodology", description: "Features, strategies and validation" },
    experimentos: { label: "Experiments", description: "RS vs GA search" },
    resultados: {
      label: "Results & closure",
      description: "13 families, multiple testing and holdout",
    },
    estudio: {
      label: "Study closure",
      description: "13 families, multiple testing and holdout",
    },
    estrategias: {
      label: "Strategies",
      description: "Every family: real equity and metrics",
    },
    laboratorio: {
      label: "Laboratory",
      description: "Build and run a strategy on the real data",
    },
    cuadernos: {
      label: "Notebooks",
      description: "The 8 notebooks: frozen figures and thesis map",
    },
    diagnostico: { label: "Diagnostics", description: "Artifacts and system" },
  },

  navGroups: {
    start: "Start",
    learn: "Learn",
    study: "The study",
    explore: "Explore",
    system: "System",
  },

  phases: {
    data: { id: "data", label: "Data and quality", short: "Phase 1" },
    eda: { id: "eda", label: "Descriptive EDA", short: "Phase 1b" },
    features: { id: "features", label: "Causal features", short: "Phase 2" },
    strategies: { id: "strategies", label: "Interpretable strategies", short: "Phase 3" },
    search: { id: "search", label: "RS/GA search", short: "Phase 4" },
    validation: { id: "validation", label: "Walk-forward", short: "Phase 5" },
    holdout: { id: "holdout", label: "Final holdout (reading withheld)", short: "Phase 6" },
  },

  sections: {
    overview: {
      title: "Research overview",
      subtitle:
        "State of the reproducible pipeline for discovering interpretable strategies on BTC/ETH perpetual futures.",
      que: "What is this platform?",
      queAnswer:
        "A read-only dashboard exposing verifiable artifacts from every experiment: data, features, search and out-of-sample metrics on the development partition.",
      porQue: "Why does it matter?",
      porQueAnswer:
        "The thesis demands traceability and holdout isolation. Every figure must be traceable to a specific run, fold and candidate.",
      comoInterpretar: "How should you read what you see?",
      comoInterpretarAnswer:
        "The metrics shown come from walk-forward windows on the development partition. They are not the final result from the frozen holdout.",
      queConcluir: "What can be concluded so far?",
      queConcluirAnswer:
        "Provisional conclusion: the pipeline is operational and auditable; the numerical results remain exploratory until the final evaluation.",
    },
    guia: {
      title: "The study, step by step",
      subtitle:
        "Thirteen panels in order, from the simplest question to the technical one. No quantitative finance background required.",
      que: "What is this guided mode?",
      queAnswer:
        "A walkthrough of the thesis: what was asked, on what data, how it was tested and why the conclusion is what it is. Each panel explains one concept and, where one exists, shows the real figure that belongs to it.",
      porQue: "Why does this mode exist?",
      porQueAnswer:
        "A negative result is only convincing if the procedure that produced it is understood. This guide makes that procedure visible without assuming any vocabulary.",
      comoInterpretar: "How do you tell a drawing from a result?",
      comoInterpretarAnswer:
        "Every teaching figure carries an “illustrative example” badge and made-up values. Study figures arrive from the API, and when one is unavailable a state is shown in its place — never a zero.",
      queConcluir: "What can be concluded here?",
      queConcluirAnswer:
        "The closure report's written conclusion is quoted verbatim in panel 13. The reserved partition was opened once and its reading was withheld pending audit: this page explains what it is, but shows none of its figures.",
    },
    datosEda: {
      title: "Data and exploratory analysis",
      subtitle: "Dataset authenticity, the development timeline and the key EDA findings.",
      que: "Which data is used?",
      queAnswer:
        "Binance USDT-M candles (BTC/ETH), validated with SHA-256 manifests. The development partition ends strictly before the holdout.",
      porQue: "Why check coverage?",
      porQueAnswer:
        "Gaps, duplicates or rows crossing into the holdout would invalidate any later conclusion about leakage or reproducibility.",
      comoInterpretar: "How do you read the timeline?",
      comoInterpretarAnswer:
        "The chart shows the development period, the pilot subset used in search, the train/validation/test folds and the reserved partition.",
      queConcluir: "What does the EDA settle?",
      queConcluirAnswer:
        "EDA findings guide the design (regimes, costs, tail dependence) but they do not select parameters or strategies.",
    },
    metodologia: {
      title: "Experimental methodology",
      subtitle:
        "Data flow, the causal feature catalogue, strategy families and walk-forward validation.",
      que: "What pipeline is followed?",
      queAnswer:
        "Data → causal features → regimes (train only) → interpretable signals → backtest with costs → RS/GA search under a matched budget.",
      porQue: "Why causal features?",
      porQueAnswer:
        "Every predictor must be computed from past information only (rolling/expanding), so that no look-ahead enters selection or evaluation.",
      comoInterpretar: "How do you read the feature table?",
      comoInterpretarAnswer:
        "Check the formula, inputs, lag and warm-up bars. A non-causal feature invalidates every candidate that uses it.",
      queConcluir: "What does walk-forward guarantee?",
      queConcluirAnswer:
        "Chronological partitions with purge and embargo; the per-fold winner is chosen on validation and scored exactly once on test.",
    },
    experimentos: {
      title: "Search experiments",
      subtitle: "Random Search against a Genetic Algorithm under a shared budget.",
      que: "What is a run?",
      queAnswer:
        "An artifact directory holding a frozen configuration, the candidates evaluated, folds, winners and per-method test equity.",
      porQue: "Why compare RS and GA?",
      porQueAnswer:
        "Both optimisers share the same evaluation budget; the comparison has to be fair before superiority can be inferred.",
      comoInterpretar: "How do you read convergence and diversity?",
      comoInterpretarAnswer:
        "Convergence shows the running best fitness; GA diversity indicates how much of the space is explored. Neither substitutes for out-of-sample metrics.",
      queConcluir: "What can an experiment conclude?",
      queConcluirAnswer:
        "Prioritise the aggregate out-of-sample metrics of the per-fold winner, and check the validity gates before any narrative.",
    },
    resultados: {
      title: "Performance results",
      subtitle: "Equity, drawdown and trades of the winning candidate over the test window.",
      que: "Which metrics are shown?",
      queAnswer:
        "Final equity, maximum drawdown, bar count and trades for the fold and method selected in the URL.",
      porQue: "Why use the summary and not paginated points?",
      porQueAnswer:
        "The equity endpoint carries a whole-series summary; the cards must use it to avoid pagination artefacts.",
      comoInterpretar: "How do you read the fold table?",
      comoInterpretarAnswer:
        "Each row is one out-of-sample test window of the winner chosen on validation. Compare methods only under the same cost definition.",
      queConcluir: "What can be concluded from the results?",
      queConcluirAnswer:
        "Exploratory development results; not to be reported as the thesis's final performance until the holdout is opened exactly once.",
    },
    estudio: {
      title: "Results and study closure",
      subtitle:
        "All 13 families judged together: every backtest, the multiple-comparison correction and the state of the frozen holdout.",
      que: "What does this section show?",
      queAnswer:
        "Every out-of-sample result in the study (family × asset) and the correction applied across the set. The holdout appears only as a state: it was opened once and its reading is still unaudited, so none of its figures are published.",
      porQue: "Why judge them together?",
      porQueAnswer:
        "Every family tested adds one more chance of getting lucky. Evaluating 13 hypotheses and keeping the best one demands correcting the significance level; without it, the best backtest always looks good.",
      comoInterpretar: "How should you read what you see?",
      comoInterpretarAnswer:
        "Total return sorts the table, but the adjusted p-value decides the verdict. Seed dispersion and the probability of backtest overfitting (PBO) tell you how much of the figure is selection noise.",
      queConcluir: "What is concluded?",
      queConcluirAnswer:
        "The study's written conclusion is shown verbatim in the multiple-comparisons panel, exactly as the closure report wrote it. A rigorous negative result is a valid result.",
    },
    diagnostico: {
      title: "Diagnostics and traceability",
      subtitle: "Artifact inspection, manifests and system state.",
      que: "Which artifacts exist?",
      queAnswer:
        "Manifests for data, features, the search space, the objective, the environment, git state and a per-run file listing.",
      porQue: "Why inspect them?",
      porQueAnswer:
        "They make reproducibility auditable: hashes, seeds, configuration and failed candidates, without reading live code.",
      comoInterpretar: "How do you read the system state?",
      comoInterpretarAnswer:
        "Components marked implemented exist in the repository; planned or reserved ones imply no deployment in this phase.",
      queConcluir: "What is diagnostics for?",
      queConcluirAnswer:
        "Use this section to verify integrity before citing any number in the thesis manuscript.",
    },
  },

  glossary: {
    holdout: {
      term: "Frozen holdout",
      definition:
        "The final partition ([holdout_start, cutoff)) opened exactly once for the definitive report, which no development code loads. It was opened on a candidate declared in advance; its reading remains withheld while the provenance audit is pending.",
    },
    walkForward: {
      term: "Walk-forward",
      definition:
        "Chronological validation with train/validation/test folds, plus purge and embargo between windows.",
    },
    oos: {
      term: "Out-of-sample (OOS)",
      definition:
        "Metrics on the fold's test window, after selecting the candidate on validation alone.",
    },
    pilot: {
      term: "Pilot subset",
      definition:
        "The fraction of development used in the pilot search; the rest is reserved for structural validation.",
    },
    fairBudget: {
      term: "Matched budget",
      definition:
        "RS and GA must spend the same effective number of unique evaluations within the configured budget.",
    },
    causalFeature: {
      term: "Causal feature",
      definition:
        "A predictor computed exclusively from past data (rolling/expanding), with no whole-sample statistics.",
    },
    nextBar: {
      term: "Next-bar execution",
      definition:
        "A signal on bar t is executed at the open of bar t+1, with costs charged explicitly.",
    },
  },

  warnings: {
    exploratory:
      "Exploratory results: validation/test metrics on the development partition only. These are NOT final holdout performance and must not be cited as the thesis's definitive out-of-sample result.",
    holdoutLocked:
      "The platform never serves observations from the holdout (Jan–Jun 2026), nor lets it inform design decisions. Its single reading was withheld pending audit.",
    devPartitionOnly: "Development partition only — frozen-holdout observations excluded.",
    integrityMismatch:
      "Integrity error: metrics computed from paginated points do not match the whole-series summary.",
    provisionalConclusion:
      "Provisional conclusion, subject to the robustness battery and the final holdout evaluation.",
    noHoldoutRuns:
      "No final-holdout runs exist in this phase; any positive metric remains preliminary.",
  },

  validity: {
    title: "Experiment validity checks",
    subtitle: "RS vs GA verifications and methodological integrity rules.",
    statusPass: "OK",
    statusWarn: "Warning",
    statusFail: "Fail",
    equalEvaluations: "Equal effective evaluations",
    withinBudget: "Within budget",
    noHoldoutLeakage: "No holdout leakage",
  },

  contextBar: {
    run: "Run",
    method: "Method",
    fold: "Fold",
    candidate: "Candidate",
    interval: "Interval",
    period: "Test period",
  },

  timeline: {
    title: "Experiment timeline",
    development: "Development",
    pilotUsed: "Pilot used",
    pilotUnused: "Pilot unused",
    train: "Train",
    validation: "Validation",
    test: "Test",
    holdout: "Holdout (reserved)",
    purge: "Purge",
    embargo: "Embargo",
  },

  trades: {
    long: "Long",
    short: "Short",
    flat: "Flat",
    exportCsv: "Export CSV",
  },

  study: {
    unavailable: {
      title: "The consolidated study artifact is unavailable",
      detail:
        "The API returns 503 because reports/study_closure/study_dashboard.json does not exist. Build it with: uv run python scripts/build_study_dashboard.py",
      generic: "The study closure could not be loaded",
    },
    headline: {
      title: "Study result",
      subtitle: "Figures read from the closure artifact; none is hard-coded in the frontend.",
      families: "Families tested",
      familiesSub: "Independent hypotheses evaluated",
      configurations: "Configurations evaluated",
      configurationsSub: "Backtests run to produce them",
      survivors: "Survivors after correction",
      survivorsSub: "Holm–Bonferroni rejections at α = {alpha}",
      pbo: "Probability of backtest overfitting (PBO)",
      pboSub: "Under pure noise, 0.5 is expected",
      units: "Family × asset × seed units",
      rowsLabel: "Family × asset rows",
      generatedAt: "Artifact generated",
      commit: "Source commit",
      bestFamily: "Family with the lowest raw p-value",
      bestFamilyNote:
        "Being the best of thirteen is not evidence of an edge: it is the result of taking the maximum across thirteen attempts. That is why it is corrected.",
    },
    table: {
      title: "Every backtest in the study",
      subtitle:
        "One row per family and asset, sortable and filterable. Select a row to open its detail.",
      family: "Family",
      gate: "Round",
      symbol: "Asset",
      totalReturn: "Total return",
      sharpe: "Sharpe",
      maxDrawdown: "Maximum drawdown",
      pValue: "Raw p-value",
      holm: "Holm p-value",
      bh: "BH p-value",
      verdict: "Verdict",
      seeds: "Seeds",
      filterGate: "Round",
      filterSymbol: "Asset",
      filterVerdict: "Verdict",
      all: "All",
      open: "view",
      empty: "No row matches these filters",
      shown: "{n} of {total} rows",
      sortAsc: "ascending",
      sortDesc: "descending",
      nullNote: "An empty adjusted p-value means the correction did not cover that unit.",
    },
    detail: {
      hypothesis: "What this family bets on",
      loading: "Loading the family detail…",
      empty: "Select a family in the table to see its detail",
      equityTitle: "Equity curve: seed average and every seed",
      equitySubtitle:
        "The thick line is what was put to the test; the thin ones are the same hypothesis under a different search seed.",
      seedTableTitle: "Result by seed",
      seedSpread: "Seed dispersion: from {min} to {max}",
      seedColumn: "Seed",
      fanTitle: "Resampling fan",
      criteriaTitle: "Promotion criteria",
      criteriaEmpty:
        "This family was not scored on the six-criteria grid: its round asked a different question. Inventing a row would misrepresent it.",
      crossAssetTitle: "BTC against ETH",
      crossAssetNote:
        "A real effect should not flip sign between two assets this tightly coupled. When it does, the sign was most likely set by the fit rather than by the market.",
      crossAssetSingle: "This family was evaluated on a single asset only.",
      buyAndHold: "Buy and hold (median)",
      gateNote: "Round note",
      bars: "Out-of-sample bars",
    },
    chart: {
      averageSeries: "Seed average",
      seedSeries: "Individual seeds ({n})",
      seedCaption:
        "The curves are decimated for drawing; each point is the exact equity at that instant, so the final value is the real final value.",
    },
    fan: {
      observedSeries: "Observed path",
      medianSeries: "Resampled median (p50)",
      innerBand: "p25–p75 band",
      outerBand: "p05–p95 band",
      barLabel: "Bar",
      method: "{method} · {paths} paths · {block}-bar blocks · seed {seed}",
      caption:
        "The fan measures PATH RISK, not statistical significance. It is built by resampling the family's own returns, so it carries the observed mean along with it: it shows how differently this same result could have turned out, not whether the edge is real. That question belongs to the p-value and the probability of backtest overfitting (PBO).",
      measuresLabel: "What the fan measures (measures field)",
      terminalTitle: "Distribution of the final return",
      terminalObserved: "Observed",
      probabilityPositive: "Resampled paths with a positive return",
    },
    criteria: {
      required: "requires",
      vetoLabel: "Veto: minimum out-of-sample trades",
      vetoTriggered: "triggered",
      vetoClear: "not triggered",
      vetoNote:
        "The veto is not a seventh criterion: it discards the unit for lack of trades, regardless of its performance.",
      gloss: {
        positive_total_return: "Positive net out-of-sample return.",
        bootstrap_sharpe_ci_excludes_zero:
          "The bootstrap confidence interval for the Sharpe excludes zero.",
        survives_double_costs: "Still positive when fees and slippage are doubled.",
        beats_buy_and_hold: "Beats buying and holding the asset.",
        survives_drop_top_trades: "Still positive with the five best trades removed.",
        not_confined_to_one_fold: "The result does not come from a single fold.",
      },
    },
    corrections: {
      title: "Multiple-comparison correction",
      subtitle: "Thirteen hypotheses judged at once, not thirteen independent tests.",
      conclusionTitle: "Study conclusion (verbatim from the closure report)",
      holmTitle: "Holm–Bonferroni",
      bhTitle: "Benjamini–Hochberg",
      rejected: "Hypotheses rejected",
      adjustedTitle: "Adjusted p-values by family",
      familyColumn: "Family",
      pboTitle: "Probability of backtest overfitting (PBO)",
      pboNoiseLine: "Noise line: 0.5",
      pboCaption:
        "PBO estimates how often the configuration that is best in one partition falls below the median in its complement. A value near 0.5 is what is expected when selection captures nothing but noise.",
      pboUnavailable: "PBO unavailable in this artifact",
      pboSplits: "Combinatorial splits",
      pboConfigurations: "Configurations compared",
      deflatedTitle: "Deflated Sharpe",
      deflatedCaption:
        "Discounts from the observed Sharpe what the best of N attempts would be expected to reach anyway. The number of attempts changes the conclusion, so it is shown under each counting rule.",
      trials: "Trials (N)",
      deflated: "Deflated Sharpe",
      spurious: "Probability the best is spurious",
      benchmark: "Benchmark Sharpe per observation",
      observedSharpe: "Observed Sharpe per observation",
      sensitivityTitle: "Sensitivity to the test count",
      sensitivityCaption:
        "How many tests are declared changes the Bonferroni threshold. The conclusion holds under all four rules.",
      rule: "Counting rule",
      nTests: "Tests",
      threshold: "Bonferroni threshold",
      smallestP: "Lowest raw p-value",
      anySurvive: "Any survivor?",
      yes: "Yes",
      no: "No",
      criteriaByGate: "Criterion applied in each round",
    },
    regimes: {
      title: "Analysis by market regime",
      subtitle: "Do the rejected families hide an effect confined to one particular market state?",
      banner:
        "EXPLORATORY block: these cells generate hypotheses, they do not validate results. Nothing here was promoted, and none of it may be cited as a confirmed finding.",
      dimension: "Dimension",
      regime: "Regime",
      cells: "Cells evaluated",
      testable: "Testable cells",
      excluded: "Cells excluded by size",
      minBars: "Minimum bars per cell",
      survivors: "Cells surviving correction",
      shareOfBars: "Share of bars",
      filterFamily: "Family",
      filterDimension: "Dimension",
      empty: "No cell matches these filters",
      noCandidate: "The exploratory block proposed no regime-conditioned candidate.",
      candidateTitle: "Candidate proposed by the exploratory block",
    },
    holdout: {
      title: "Final holdout",
      subtitle:
        "State of the frozen partition. This section reports the holdout's state; it shows no reading from it.",
      lockedTitle: "Holdout opened once: result unaudited",
      lockedBody:
        "The evaluation of the frozen partition is UNAUDITED, so none of its figures are published here: no return, no Sharpe, no drawdown, no seed dispersion, no buy-and-hold comparison. The API may still carry those fields; the interface does not render them.",
      period: "Reserved window",
      reason: "Reason for isolation",
      requirementsTitle: "Requirements before it can be opened and published",
      requirementsSubtitle:
        "Each point must be verified and recorded before any holdout figure may be cited.",
      requirementsEmpty: "The payload carries no requirements list",
      requirementsEmptyHint:
        "While the endpoint sends no requirements field, no list is shown: requirements are not invented.",
      deliberateAbsence:
        "The absence of metrics is deliberate, not a loading error or an API failure. An unaudited holdout is not a result, and showing it as one would compromise the thesis's conclusion.",
    },
  },

  guia: {
    toc: {
      title: "Guide contents",
      navLabel: "Contents of the guide's 13 panels",
      progress: "Panel {n} of {total}",
      jump: "Go to panel {n}: {title}",
      progressLabel: "Guide reading progress",
    },

    parts: {
      viendo: "What you are looking at",
      importa: "Why it matters",
      interpreta: "How to read it",
      conclusion: "Conclusion reached",
    },

    illustrative: {
      badge: "illustrative example",
      note: "A teaching drawing with made-up values to explain the concept. It is not a study result nor an API figure.",
    },

    data: {
      loading: "Loading the study figures…",
      unavailableTitle: "Study figures unavailable",
      unavailableHint:
        "The panel shows a state instead of a number: nothing is invented here and no gaps are filled with zeros.",
      notServedHint:
        "The study endpoints do not publish this value, so it is declared as a state rather than shown as an approximation.",
    },

    legend: {
      train: "Training",
      val: "Validation",
      test: "Out-of-sample test",
      holdout: "Reserved holdout (reading withheld)",
      development: "Development (where the research happens)",
      purge: "Purge: bars discarded",
      embargo: "Embargo: additional wait",
      signal: "Signal computed on bar t",
      exec: "Execution at t+1, with costs",
      future: "Information that did not exist yet",
      neutral: "Rest of the series",
      learned: "Parameters already learned",
      refit: "Refitted on new data",
      rule: "Fixed rule, nothing learned",
      config: "Another configuration of the same rule",
      decision: "A later design decision",
      window: "The indicator's computation window",
    },

    series: {
      price: "Price",
      average: "Moving average of the last bars",
      observations: "Observations",
      overfit: "A rule fitted to the noise",
      trend: "A rule that ignores the noise",
      inSample: "In-sample error",
      outSample: "Out-of-sample error",
    },

    pdots: {
      axisStart: "p = 0",
      axisEnd: "p = 1",
      threshold: "α threshold (vertical line)",
      rejected: "Crosses the threshold",
      notRejected: "Does not cross the threshold",
      smallest: "The lowest of the set",
    },

    bars: {
      gross: "Gross return of the rule",
      fees: "After fees, on each side",
      slippage: "After fees and slippage",
      net: "Net return, after funding too",
      valBest: "Best configuration on validation",
      oosSame: "The same configuration, out of sample",
      attemptsMax: "The largest of the attempts",
      attemptsMean: "The mean of the attempts",
      attemptsMin: "The smallest of the attempts",
      pboA: "Rank in the half where it won",
      pboB: "Rank of the same one in the complementary half",
      dsrObserved: "Observed Sharpe of the best",
      dsrExpected: "Maximum chance produces with N attempts",
      dsrDeflated: "What is left after discounting it",
    },

    panels: {
      pregunta: {
        title: "What question is this trying to answer?",
        viendo:
          "The study's starting point: a single scientific question and the count of attempts made to answer it. Both figures come from the closure artifact; neither is written into this page.",
        importa:
          "The question is not “does this strategy work?” but “out of everything we tried, did anything work?”. Those are different questions: the second includes the failed attempts, and that is why it demands a higher statistical bar.",
        interpreta:
          "Read the two figures together: strategy families tested and configurations evaluated. The more attempts, the easier it is for one of them to look good by pure chance.",
        conclusion:
          "The study commits to the broad question and declares how many attempts it made to answer it. That count is the basis of everything that follows.",
      },
      datos: {
        title: "What data does it use?",
        viendo:
          "The assets, the timeframe and the length of the evaluated series exactly as the API declares them, together with the state of the frozen partition.",
        importa:
          "If the data is not real, complete and verifiable, nothing that comes afterwards means anything. And if the final period is used during development, the result stops being a test.",
        interpreta:
          "The history splits in two: development, where the research happens, and the frozen holdout, which is not touched. The diagram is a drawing with invented proportions; the real figures are the cards above.",
        conclusion:
          "The data is USDT-M perpetual futures candles on two tightly coupled assets, and the final partition stayed outside development: everything judged here happens in development.",
      },
      estrategia: {
        title: "What is a strategy?",
        viendo:
          "The definition of strategy this study uses, and a real hypothesis: the text the API stores for one of the families tested.",
        importa:
          "A strategy is not an opinion about the market: it is a rule that, given the same data, always makes the same decision. What cannot be written as a rule cannot be tested or refuted.",
        interpreta:
          "Each family is a hypothesis with free parameters — how many bars to look back, for instance. The rule is fixed; the parameters are what the search adjusts.",
        conclusion:
          "Every family in the study is interpretable: it can be read, argued with and refuted. That is a requirement of the thesis, not a technical limitation.",
      },
      backtest: {
        title: "What is a backtest?",
        viendo:
          "How a rule turns into a series of outcomes: the signal is computed when a bar closes and the trade is executed on the next one, paying costs.",
        importa:
          "A backtest is the only way to test a rule without risking money, and also the easiest way to fool yourself. The difference lies in the execution details.",
        interpreta:
          "Watch the offset: the decision is made on bar t, the execution happens at the open of t+1. If execution occurred on the same bar as the decision, the backtest would be using a price that was not yet known.",
        conclusion:
          "The study executes on the following bar and charges costs explicitly. That choice makes the numbers smaller and more believable.",
      },
      particiones: {
        title: "What are train, validation and out-of-sample?",
        viendo:
          "Time split into four stretches with different roles: training, validation, out-of-sample test and frozen holdout.",
        importa:
          "Fitting and evaluating on the same data guarantees a good result and says nothing. Separating the stretches is what turns a number into evidence.",
        interpreta:
          "The stretches run in chronological order, never at random: the past trains and the future judges. Each stretch serves exactly one purpose: train fits, validation chooses, test scores exactly once.",
        conclusion:
          "The split is chronological and the holdout stayed outside development, so the figures in the following panels are test figures within the development partition.",
      },
      walkForward: {
        title: "What is walk-forward validation?",
        viendo:
          "The same split repeated several times, advancing through time. Each repetition is called a fold.",
        importa:
          "A single train/test cut can turn out well or badly depending on where the line happened to fall. Repeating it forward measures whether the rule holds across several different periods, not just one lucky one.",
        interpreta:
          "Each row of the diagram is a fold: it trains on the past, chooses on its own validation slice, and scores on a test it had not seen. The test stretches of every fold are concatenated to judge the family.",
        conclusion:
          "The study validates with walk-forward and searches parameters independently inside each fold, so that one fold's choice cannot look at another fold's test.",
      },
      purgeEmbargo: {
        title: "What are purge and embargo?",
        viendo:
          "Two deliberate gaps around each cut: the purge discards bars whose computation crosses the line, and the embargo adds a wait after it.",
        importa:
          "Indicators mix neighbouring bars. Without gaps, the last training bars share information with the first test bars, and that overlap reads as a hit.",
        interpreta:
          "The discarded band is used neither for training nor for evaluation: it is thrown away. The further back an indicator looks, the wider the gap has to be.",
        conclusion:
          "The protocol applies purge and embargo at every cut. Without them, any positive result would be suspect by construction.",
      },
      semillasFolds: {
        title: "What are seeds and folds?",
        viendo:
          "The same experiment repeated with different search seeds, for a real family you can choose here: the average curve, each seed separately, and the spread between them.",
        importa:
          "Parameter search starts from a random point. If changing that arbitrary point flips the sign of the result, what was being measured was the luck of the start, not the idea.",
        interpreta:
          "The thick line is the seed average and the thin ones are the same hypothesis under a different start. The wider the thin ones spread, the less the thick one tells you.",
        conclusion:
          "Seeds are treated as replicates of one hypothesis and averaged, rather than counted as independent tests. Folds, by contrast, are genuinely different periods and are concatenated.",
      },
      costes: {
        title: "What costs are applied?",
        viendo:
          "The path from gross to net return: fee and slippage on each side of the trade, and the perpetual's funding while the position stays open.",
        importa:
          "Almost any rule looks profitable without costs. Costs are the filter separating an idea from a trade that could actually have been executed.",
        interpreta:
          "The ladder is a drawing with invented figures: it shows the order of the subtractions, not their size. The table, by contrast, is real: it counts how many seeds stay positive when costs are doubled.",
        conclusion:
          "The study backtests with explicit costs and, on top of that, requires a result to survive doubling them. The exact parameters of the cost model are not published by this endpoint.",
      },
      estrategiasProbadas: {
        title: "Which strategies were tested?",
        viendo:
          "The full inventory of the study's families, with the round each was tested in, the asset, and the hypothesis it was betting on.",
        importa:
          "The inventory is the study's denominator. Publishing only the best family and staying quiet about the rest is exactly the practice that invalidates a result.",
        interpreta:
          "Each row is a distinct hypothesis, not a variant of the previous one. The round column says in which phase it was tested and under which promotion criterion.",
        conclusion:
          "Everything tested is declared, not only what survived. That count is what feeds the multiple-comparison correction in the next panel.",
      },
      resultados: {
        title: "What results were obtained?",
        viendo:
          "Every out-of-sample result in one sortable table and, below it, the correction applied to the set: Holm, Benjamini–Hochberg, PBO and the deflated Sharpe.",
        importa:
          "A raw p-value answers “is this result unusual?”. With thirteen families tested, the right question is “is the best of thirteen unusual?”, and that one demands moving the threshold.",
        interpreta:
          "Sort by return and then look at the adjusted p-value: they are two different readings of the same row. The verdict is decided by the adjusted one, never by the return.",
        conclusion:
          "Every figure is read from the closure artifact, including the report's written conclusion. None of it is hard-coded into this page.",
      },
      rechazo: {
        title: "Why can a seemingly profitable strategy be rejected?",
        viendo:
          "The three reasons a positive backtest may not be an edge: it was the best of many attempts, it does not repeat on the second asset, and it does not hold when the sample is split.",
        importa:
          "The maximum of a list of attempts always looks good, even when none of them has an edge. Without correcting for the number of attempts, “the best backtest” measures how many backtests were run.",
        interpreta:
          "Compare the same family across both assets: a structural effect should not flip sign between markets this tightly coupled. And read the PBO against 0.5, which is what pure noise produces.",
        conclusion:
          "Profitable in the backtest and holding a real edge are not the same thing. The study rejects on that distinction, not on the sign of the return.",
      },
      conclusion: {
        title: "What scientific conclusion is reached?",
        viendo:
          "The closure report's written conclusion and the state of the frozen partition. This guide shows no reading from the holdout.",
        importa:
          "A rigorous negative result is a valid result; a positive result obtained by looking at the holdout is not. Closing properly is part of the conclusion.",
        interpreta:
          "Read the conclusion for what it is: a claim about this universe of strategies, this cost model and this horizon. It is not a claim about algorithmic trading in general.",
        conclusion:
          "Under this cost model and on this class of instrument, the study finds no edge. The holdout was opened once and its reading is withheld pending audit; the conclusion does not depend on it.",
      },
    },

    figures: {
      developmentHoldout: {
        title: "How the history is split",
        caption:
          "Invented proportions. What matters is that the frozen stretch sits at the end and takes no part in the research.",
        rows: { serie: "Historical series" },
      },
      nextBar: {
        title: "Signal at t, execution at t+1",
        caption:
          "Time runs left to right. A decision is never executed on the same bar it is taken.",
        rows: { barras: "Consecutive bars" },
      },
      splits: {
        title: "The four stretches and their roles",
        caption:
          "The order is chronological and is never altered. The sizes in the drawing do not represent the study's.",
        rows: { reparto: "How time is divided" },
      },
      walkForward: {
        title: "One fold per row, advancing through time",
        caption:
          "Four example folds. The real number of folds is set by the experiment's configuration, not by this drawing.",
        foldLabel: "Fold {n}",
      },
      purgeEmbargo: {
        title: "The same cut, without and with gaps",
        caption:
          "Above, training and test touch and share information. Below, the overlapping bars are discarded and a wait is added.",
        rows: { sin: "Without purge or embargo", con: "With purge and embargo" },
      },
      costLadder: {
        title: "From gross to net return",
        caption:
          "Invented figures to show the order of the subtractions: fee and slippage per side, and funding while the position is open.",
      },
      strategyRule: {
        title: "A rule, not an opinion",
        caption:
          "An invented price and its moving average. The rule says “long while price is above”: given the same data, it always decides the same.",
      },
      curveFitting: {
        title: "Fitting the shape against fitting the noise",
        caption:
          "The points are invented observations. The jagged line passes through all of them and is useless out of sample; the smooth one ignores the noise.",
      },
      overfitting: {
        title: "The overfitting scissors",
        caption:
          "As complexity rises, in-sample error keeps falling while out-of-sample error starts climbing. The crossing marks overfitting.",
      },
      multipleTesting: {
        title: "Thirteen p-values, one threshold",
        caption:
          "Each point is an invented test. With enough tests, the lowest ends up looking significant even when none has an edge.",
      },
      holm: {
        title: "The same p-values, adjusted by Holm",
        caption:
          "Holm demands progressively looser thresholds down the ranking. On the invented p-values above, none survives.",
      },
      bh: {
        title: "The same p-values, adjusted by Benjamini–Hochberg",
        caption:
          "BH is more permissive than Holm because it controls the proportion of false discoveries, not the probability of having one.",
      },
      pHacking: {
        title: "Trying until it works",
        caption:
          "Same data, analysis tweaked again and again. The last attempt's p-value does not mean what it says, because it was not the only one.",
      },
      dataMining: {
        title: "Sweeping the space of patterns",
        caption:
          "Each point is an invented combination that was tried. Finding the best is not a discovery unless you say how many were looked at.",
      },
      selectionBias: {
        title: "The maximum is not just any result",
        caption:
          "Invented attempts with no edge: their mean is zero, yet the largest is always positive. Reporting only the largest turns noise into a finding.",
      },
      hyperparameter: {
        title: "Choose on validation, check outside",
        caption:
          "The best configuration on validation is not the best out of sample. The invented difference is the price of having chosen.",
      },
      fineTuning: {
        title: "Two different things that get confused",
        caption:
          "Above, fine-tuning: there are learned parameters and they are refitted. Below, hyperparameter optimisation: the rule is fixed and only its configuration changes.",
        rows: {
          ft: "Fine-tuning: an already-trained model",
          hp: "Hyperparameters: a fixed rule",
        },
      },
      leakage: {
        title: "A value that could not have been known",
        caption:
          "Above, the computation window crosses the present and takes future information. Below, the same window looks only backwards.",
        rows: { leak: "Leaking window", ok: "Causal window" },
      },
      snooping: {
        title: "Looking at the test and going back",
        caption:
          "Above, the test is consulted and the design is then changed: it stops being out of sample. Below, it is opened once, at the end.",
        rows: { mirado: "Test consulted before deciding", limpio: "Test opened exactly once" },
      },
      pbo: {
        title: "Best in one half, middling in the other",
        caption:
          "Invented relative rank of the same configuration in two complementary halves of the sample. If the ordering does not hold, selection was not informative.",
      },
      deflated: {
        title: "Discounting the best of N attempts",
        caption:
          "Invented Sharpe: the observed one, what the best of N attempts would produce by chance, and what is left after subtracting the second from the first.",
      },
    },

    labels: {
      question: "The question the study answers",
      questionText: "“Out of everything we tried, did anything work?”",
      assets: "Assets evaluated",
      timeframe: "Timeframe",
      oosBars: "Out-of-sample bars (longest row)",
      holdoutState: "Holdout state",
      holdoutOpenedFalse:
        "This artifact was generated over development and carries no reading from the reserved partition, so there are no figures from it to show here.",
      exampleFamily: "Example family (the one with the lowest raw p-value)",
      foldsNotServed: "Number of folds in the experiment",
      purgeNotServed: "Purge and embargo bars",
      costModelNotServed: "Cost-model parameters",
      seeMethodology: "See Methodology for the protocol in detail.",
      chooseFamily: "Family shown",
      costCriterionTitle: "The real criterion: still positive when costs are doubled",
      costCriterionSubtitle:
        "One row per family × asset unit that scored this criterion, with the seeds that clear it.",
      costCriterionEmpty: "No family in this artifact scored the doubled-cost criterion",
      criterionPassed: "Seeds clearing it",
      criterionRequired: "Seeds required",
      inventoryTitle: "Inventory of families tested",
      inventorySubtitle:
        "Everything that entered the scientific record, not only what survived the correction.",
      resultsNote:
        "Selecting a row also changes the family shown in panel 8, so you can inspect its seeds.",
      reasonsTitle: "The three reasons for rejection",
      reasonBest: "It was the best of many attempts",
      reasonBestText:
        "The raw p-value does not discount how many families were tested; the adjusted one does. Compare the two columns in the panel 11 table.",
      reasonAsset: "It does not repeat on the second asset",
      reasonAssetText:
        "The same hypothesis, measured on two tightly coupled markets, should keep its sign. The cards below are real API figures.",
      reasonSplit: "It does not hold when the sample is split",
      reasonSplitText:
        "PBO measures how often the configuration that wins in one half falls below the median in the other. The noise reference is 0.5.",
      spuriousTitle: "Probability that the best is spurious",
      spuriousRule: "Rule for counting attempts",
      regimeQuestion:
        "What if the effect existed only in one specific market state? That question was answered in an explicitly exploratory block, with its own internal correction.",
      holdoutWithheld:
        "The holdout reading is withheld pending audit. This guide explains what the reserved partition is and why its figure is not published, but shows none of its metrics.",
    },

    concepts: {
      title: "Concepts, one by one",
      subtitle:
        "The traps a backtest can hide and the tools that detect them. Every card carries a teaching drawing, not a result.",
      fineTuningTitle: "A necessary clarification: fine-tuning is not hyperparameter optimisation",
      fineTuningBody:
        "Fine-tuning means refitting an ALREADY-TRAINED model: you start from learned parameters and keep updating them with new data. It is what you do with a pre-trained neural network.",
      fineTuningBody2:
        "Changing a lookback, moving a stop or raising an RSI threshold is NOT fine-tuning: it is hyperparameter optimisation, because nothing learned is being refitted — the same fixed rule is simply re-evaluated under another configuration. There is no fine-tuning in this study, because there is no trained model to refit: there is hyperparameter search with Random Search and with a genetic algorithm.",
      whatIs: "What it is",
      whyMatters: "Why it matters here",
      items: {
        mineria: {
          term: "Data mining",
          plain:
            "Searching for patterns by trying many combinations on the same data until one stands out.",
          matters:
            "Not bad in itself: that is how hypotheses are generated. It becomes a problem when the pattern found is presented as a discovery without discounting how many combinations were tried.",
        },
        snooping: {
          term: "Data snooping",
          plain:
            "Making design decisions using information from the stretch that was supposed to evaluate, even if it was only looked at.",
          matters:
            "It is enough to have seen the test result and gone back to change something. That stretch stops being out of sample the moment it informs a decision.",
        },
        curva: {
          term: "Curve fitting",
          plain:
            "Tweaking the rule until it reproduces the exact shape of the history, noise included.",
          matters:
            "The fitted curve explains the past almost perfectly and says nothing about the future. The warning sign is an improvement that only appears with very finely tuned parameters.",
        },
        hiper: {
          term: "Hyperparameter optimisation",
          plain:
            "Choosing the values of a fixed rule's free parameters: how many bars to look back, where to put the stop, which threshold to use.",
          matters:
            "It is exactly what Random Search and the genetic algorithm do in this study. Every configuration tried is one more attempt that has to be counted.",
        },
        fineTuning: {
          term: "Fine-tuning",
          plain:
            "Refitting an ALREADY-TRAINED model: you start from learned parameters and keep updating them with new data.",
          matters:
            "Changing a lookback, a stop or an RSI threshold is NOT fine-tuning: it is hyperparameter optimisation. There is no fine-tuning in this study, because there is no trained model to refit.",
        },
        sobreajuste: {
          term: "Overfitting",
          plain: "Learning the history's noise instead of its structure.",
          matters:
            "You recognise it by the scissors: in-sample error keeps falling while out-of-sample error starts climbing. What improves is memory, not the ability to generalise.",
        },
        multiples: {
          term: "Multiple testing",
          plain:
            "When many hypotheses are tested at once, the chance that one looks significant by luck grows with the number of tests.",
          matters:
            "With twenty tests at a 0.05 threshold you expect one “significant” result even when none has an edge. Thirteen families demand correcting the threshold once, across the whole set.",
        },
        seleccion: {
          term: "Selection bias",
          plain: "Reporting the best of several results as though it were just any result.",
          matters:
            "The maximum of a sample always beats its mean. Publishing the maximum without saying how many it came from turns noise into a finding.",
        },
        pHacking: {
          term: "P-hacking",
          plain:
            "Repeating the analysis with variants — another period, another filter, another metric — until the p-value drops below the threshold.",
          matters:
            "The final p-value no longer means what it says, because the threshold was not crossed once: it was crossed on attempt number N, and only that one was published.",
        },
        leakage: {
          term: "Information leakage",
          plain: "A value used to decide containing information that did not exist at that moment.",
          matters:
            "It is usually subtle: an average computed over the whole sample, a label crossing the cut, an execution on the same bar as the signal. Any of the three inflates the result.",
        },
        pbo: {
          term: "PBO (probability of backtest overfitting)",
          plain:
            "How often the configuration that wins in one half of the sample falls below the median in the complementary half.",
          matters:
            "Under pure noise, 0.5 is expected. A value near 0.5 indicates that the selection process is capturing no information, merely reshuffling chance.",
        },
        deflated: {
          term: "Deflated Sharpe Ratio",
          plain:
            "The observed Sharpe, discounting what the best of N attempts would produce by chance.",
          matters:
            "The declared number of attempts changes the result, so it is reported under several counting rules instead of settling on the most favourable one.",
        },
        holm: {
          term: "Holm–Bonferroni correction",
          plain:
            "Adjusts p-values to control the probability of making at least one false positive across the whole set of tests.",
          matters:
            "It sorts p-values from smallest to largest and applies progressively looser thresholds. It is conservative: what survives Holm survives almost anything.",
        },
        bh: {
          term: "Benjamini–Hochberg correction",
          plain:
            "Adjusts p-values to control the expected proportion of false positives among the rejections, not the probability of having one.",
          matters:
            "It is more permissive than Holm: it accepts some false positives in exchange for detecting more real effects. If nothing survives BH either, the negative conclusion is stronger.",
        },
      },
    },
  },

  explorer: {
    title: "Strategy explorer",
    subtitle:
      "Fifteen of the sixteen families with a complete multi-seed study (macro_event_brake, from round S3, is not exported here): real out-of-sample equity curves and the full metric set, per asset and per seed.",
    que: "What does this section show?",
    queAnswer:
      "Every family evaluated, with the equity curve of its ten seeds over the concatenated out-of-sample window and every metric the robustness battery computed. Nothing is simulated: each point is the exact equity at that instant.",
    porQue: "Why show rejected strategies?",
    porQueAnswer:
      "Because the study's finding is precisely that looking profitable and holding a real edge are different things. Here you can see, family by family, how much the outcome moves with the seed and against buy and hold.",
    comoInterpretar: "How do you read the curves?",
    comoInterpretarAnswer:
      "The thick line is the seed average; the thin ones, each seed on its own. The wider they spread, the more the outcome depends on the search's starting luck. Always compare against buy and hold.",
    queConcluir: "What NOT to conclude here?",
    queConcluirAnswer:
      "A rising curve does not make an edge: the verdict was decided by the closure's statistical correction, not by the return. No family is promoted and no figure is holdout performance.",
    pickFamily: "Family",
    pickAsset: "Asset",
    pickSeed: "Seed",
    averageSeeds: "Seed average",
    allSeeds: "All seeds",
    equityTitle: "Out-of-sample equity",
    equitySubtitle:
      "Window {start} — {end} · {bars} bars · engine {engine}. Curves decimated for drawing; every point keeps its exact value.",
    metricsTitle: "Full metrics",
    metricsSubtitle: "All sixteen battery metrics, for the current selection.",
    medianAcrossSeeds: "median across the {n} seeds",
    medianNote:
      "With the average selected, each metric is the median across seeds; hover to see the min–max range.",
    bestSeed: "Best",
    worstSeed: "Worst",
    benchmarkLine: "Buy and hold with funding (perp, same window)",
    averageLine: "Average of the seeds",
    seedLine: "Seed {seed}",
    configTitle: "Winning configuration per fold",
    configSubtitleSeed:
      "The 15 frozen winners of seed {seed}: parameters were selected on the validation window and scored exactly once on their fold's test.",
    configSubtitleAverage:
      "Most-chosen values across the {n} fold winners of all seeds. Pick a specific seed to see its 15 exact configurations.",
    configFold: "Fold",
    configParams: "Parameters",
    configValSharpe: "Val. Sharpe",
    configTestSharpe: "Test Sharpe",
    configTestReturn: "Test return",
    configTrades: "Trades",
    configParam: "Parameter",
    configTopValues: "Most frequent values (fold count)",
    mcTitle: "Monte Carlo — dispersion under resampling",
    mcSubtitle:
      "Stationary block bootstrap ({block} expected bars, {paths} paths, fixed generator seed) over the real OOS series of the median-return seed ({seed}). It measures dispersion; it validates nothing.",
    mcObserved: "Observed return",
    mcPercentile: "Percentile of the observed",
    mcProbPositive: "P(return > 0) under resampling",
    mcQuantile: "Quantile",
    mcTotalReturn: "Total return",
    mcNote:
      "The distribution resamples one seed's real returns: if the observed value sits inside the mass, the result is indistinguishable from the sampling variation of its own series.",
    buyAndHold: "Buy and hold",
    thesis: "What this family bets on",
    thesisMissing: "This family's registered hypothesis lives in its round, not in the closure.",
    round: "Round",
    verdictRejected: "REJECTED at closure",
    verdictNotPromotable: "Evaluated post-closure — not promotable (partition consumed)",
    banner:
      "Exploratory development results. No family is promoted; the study closed negative, and the later CRT round cannot promote because the reserved partition is consumed.",
    tableFamily: "Family",
    tableRound: "Round",
    tableVerdict: "Verdict",
    tableMedianReturn: "Median return",
    tableMedianSharpe: "Median Sharpe",
    tableBh: "B&H",
    loading: "Loading the strategy index…",
    loadError:
      "Could not load the index. Generate it with: uv run python scripts/export_strategy_explorer.py",
    metric: {
      total_return: "Total return",
      ann_return: "Annualised return",
      ann_volatility: "Annualised volatility",
      sharpe: "Sharpe",
      sortino: "Sortino",
      calmar: "Calmar",
      max_drawdown: "Maximum drawdown",
      time_in_drawdown: "Time in drawdown",
      hit_rate: "Hit rate",
      n_trades: "Trades",
      exposure: "Exposure",
      turnover: "Turnover",
      var_95: "VaR 95%",
      expected_shortfall_95: "ES 95%",
      skewness: "Skewness",
      excess_kurtosis: "Excess kurtosis",
    },
  },

  common: {
    loading: "Loading…",
    noData: "No data",
    selectRun: "Select a run",
    viewAll: "View the full gallery",
    keyFindings: "Key findings",
    fullGallery: "Full EDA gallery",
    howToRead: "How to read this section",
    expand: "Expand",
    collapse: "Collapse",
  },

  provenance: {
    generated: "data generated",
    contract: "contract",
    holdout: "holdout since",
    regen: "regenerate with",
  },

  experimentosApi: {
    title: "This section needs the local API",
    body:
      "The run browser reads the artifacts under artifacts/runs through the read-only " +
      "API. The rest of the panel works without it; this page does not. Start it with the " +
      "command below and press retry.",
    retry: "Retry",
  },

  cuadernos: {
    title: "Study notebooks",
    subtitle:
      "The eight analysis notebooks, deterministically rebuildable by their builder " +
      "scripts, with the inventory of frozen figures and tables the thesis cites.",
    que: "What is this?",
    queAnswer:
      "The index of the eight notebooks: what each one establishes, how many cells it has, " +
      "which frozen figures and tables it produces, and which thesis chapter it feeds.",
    como: "How are they regenerated?",
    comoAnswer:
      "Each notebook is written by a deterministic builder script (cells, seed, and " +
      "contract declared). Running the script reproduces the notebook; the double-run hash " +
      "check verifies the artifacts come out byte-identical.",
    queNo: "What are they NOT?",
    queNoAnswer:
      "Not free-form exploration: they are the study's executable record. No figure is " +
      "hand-edited; when a figure changes, its builder changes and the history shows it.",
    cells: "cells",
    chapterLabel: "Thesis destination",
    chapterSource: "per",
    builderLabel: "Regenerated with",
    figuresLabel: "Frozen figures",
    tablesLabel: "Frozen tables",
    chainLabel: "Chains (computes nothing)",
    none: "—",
    loadError:
      "The index could not be loaded. Generate it with: uv run python " +
      "scripts/export_notebooks_index.py",
  },

  panelHome: {
    verdictTitle: "The study's verdict",
    verdictSubtitle:
      "Statistical closure on the development partition. These figures are static and " +
      "auditable; they depend on no service.",
    families: "families evaluated in the closure",
    survive: "survive the multiple-comparison correction",
    pValue: "smallest p-value (threshold: {alpha})",
    pbo: "probability of backtest overfitting (PBO)",
    verdictLink: "See the full evidence →",
    statsTitle: "The study in numbers",
    statBars: "development 1h candles",
    statRuns: "recorded runs",
    statFamilies: "families implemented",
    statRotations: "randomisation-test rotations",
    quickTitle: "Sections",
    quickSubtitle: "The study's thread, in reading order.",
    liveTitle: "Live status",
    liveSubtitle: "Data served by the local API right now.",
    apiHint:
      "The local API is not running; the static sections above do not need it. For the run " +
      "browser: uv run uvicorn perp_lab.api.main:app --port 8000",
    liveRunsTotal: "Total runs",
    liveRunsDev: "Development runs",
    liveRunsSynthetic: "Synthetic runs",
    liveRunsSyntheticSub: "not results",
    liveHoldout: "Holdout",
    liveHoldoutSub: "locked partition",
    pilotTitle: "Reference pilot run",
    pilotSymbol: "Symbol",
    pilotInterval: "Interval",
    pilotBudget: "Budget",
    pilotFolds: "Folds",
    pilotFraction: "Dev fraction",
    pilotSeed: "Seed",
    pilotLink: "View pilot experiment →",
  },

  eda: {
    statBars: "development 1h candles",
    statCoverage: "mean series coverage",
    statSpan: "development period",
    statDatasets: "datasets with a manifest",
    provenanceTitle: "Provenance and partitions",
    provenanceSubtitle:
      "Every dataset with its SHA-256 hash: re-downloading from Binance Vision reproduces " +
      "these bytes exactly. The holdout is physically separated into its own files.",
    colDataset: "Dataset",
    colPartition: "Partition",
    colRows: "Rows",
    colSpan: "Span",
    colSha: "SHA-256",
    partitionDev: "development",
    partitionHoldout: "holdout (frozen)",
    priceTitle: "Price",
    priceSubtitle: "Daily close, logarithmic scale",
    priceWhat:
      "What it shows: the full price series with the reserved partition shaded at the end.",
    priceWhy:
      "What it implies: the log scale keeps the early years readable; the shaded zone never " +
      "fed any design decision.",
    holdoutLabel: "holdout",
    volTitle: "Rolling volatility",
    volSubtitlePrefix: "Rolling standard deviation over",
    volSubtitleSuffix: "days, annualised",
    volWhat: "What it shows: how much the market moves, with a strictly backward-looking window.",
    volWhy:
      "What it implies: volatility regimes differ by orders of magnitude; a fixed-parameter " +
      "strategy does not behave the same in 2021 and 2024, which is why the study validates " +
      "across temporal windows.",
    medianLabel: "median",
    distTitle: "Hourly return distribution",
    distSubtitle: "Observed versus a normal with the same mean and standard deviation",
    distWhat:
      "What it shows: the real histogram of 1h returns against the equivalent Gaussian bell " +
      "(logarithmic vertical axis).",
    distWhy:
      "What it implies: real tails exceed the normal by orders of magnitude; any risk metric " +
      "assuming normality underestimates the extreme event. This is the empirical basis of " +
      "the risk chapter.",
    distObserved: "observed",
    distNormal: "equivalent normal",
    tailsMove: "Move",
    tailsExpected: "Normal predicts",
    tailsObserved: "Observed",
    tailsOver: "More than",
    tailsFooterPrefix: "Over",
    tailsFooterSuffix: "development hours.",
    seasonTitle: "Volatility seasonality",
    seasonWhat: "What it shows: mean absolute move per 1h bar (basis points), UTC hour × weekday.",
    seasonWhy:
      "What it implies: the US session concentrates the movement and the weekend mutes it; " +
      "the 'intraday' in the title is not decorative — it is where the structure lives.",
    uwTitle: "Distance from the prior peak (buy and hold)",
    uwWhat: "What it shows: depth relative to the running maximum at every instant.",
    uwWhy:
      "What it implies: even the asset spends nearly all its time below an earlier peak; " +
      "drawdown is not a trading anomaly, it is the series' normal state.",
    fundingTitle: "Perpetual funding",
    fundingWhat: "What it shows: weekly mean of the real funding rate (8-hour events).",
    fundingWhy:
      "What it implies: holding a long costs on average {pct} per year in funding alone; the " +
      "study's engine charges it bar by bar and no comparison is valid without it.",
    annexTitle: "Annex: frozen EDA gallery",
    annexSubtitle:
      "The matplotlib figures generated by the EDA pipeline, as cited in the thesis. They " +
      "are frozen artifacts; the live charts above are computed from the same data.",
    annexApiNote:
      "The gallery is served by the local API. Start it with: uv run uvicorn " +
      "perp_lab.api.main:app --port 8000",
    annexOpen: "Show gallery ({n} figures)",
  },

  lab: {
    title: "Strategy laboratory",
    subtitle:
      "Build a strategy from the study's families, adjust its parameters, and run it on the real " +
      "hourly BTC and ETH candles — under the same execution model, costs, and funding as the " +
      "research engine.",
    banner:
      "Exploratory, educational tool. The browser engine replicates the study's (next-open " +
      "execution, real fees, slippage, and funding), but a favourable result here validates " +
      "NOTHING: the study's battery requires multi-seed runs, walk-forward, and " +
      "multiple-comparison correction. The holdout period is excluded from this data.",
    flow: {
      title: "The complete flow, in the study's own order",
      design: "Design",
      designDesc: "Family and parameters from the study's space",
      backtest: "Run",
      backtestDesc: "Backtest under real costs and funding",
      validate: "Validate",
      validateDesc: "Multi-seed walk-forward, the study's protocol",
      compare: "Compare",
      compareDesc: "Against the 15 formal families",
      done: "done",
      pending: "pending",
    },
    que: "What is this?",
    queAnswer:
      "A real backtester running in your browser on the development partition (2020–2025). Four " +
      "of the study's families are ported line by line from the Python code: same thresholds, " +
      "same exclusion of the decision bar, same position state machine.",
    comoFunciona: "How does an order execute?",
    comoFuncionaAnswer:
      "The signal is decided on the closed candle and executed at the next open; never at the " +
      "price that generated the signal. Every position change pays fee and slippage (a " +
      "long→short flip pays double), and every bar in position settles the funding falling due " +
      "in its interval.",
    queNo: "What NOT to conclude here?",
    queNoAnswer:
      "That your configuration “works”. With thousands of possible combinations, finding a " +
      "rising curve is a matter of attempts, not of edge: it is exactly the selection bias the " +
      "study measures. Use the test battery as what it is — an honest first filter.",
    pickStrategy: "Family",
    pickAsset: "Asset",
    paramsTitle: "Parameters",
    studyValuesNote: "Marked values belong to the study's own search space.",
    costsTitle: "Costs",
    fee: "Fee (bps per side)",
    slippage: "Slippage (bps per side)",
    costsNote: "Defaults: taker 4 bps + 1 bps — the study's.",
    splitLabel: "In-sample / out-of-sample split",
    splitNote:
      "Indicators are computed causally over the full series; metrics are separated into the " +
      "two phases by entry date.",
    run: "Run backtest",
    running: "Running…",
    dataLoading: "Loading the real candles…",
    dataError:
      "The lab data could not be loaded. Generate it with: uv run python " +
      "scripts/export_lab_data.py",
    dataFootnote:
      "{n} 1h candles · {start} — {end} · development partition, holdout excluded · real " +
      "Binance funding ({nf} events).",
    strategies: {
      momentum: {
        name: "Momentum (moving-average crossover)",
        tagline: "Follow the trend when the fast average crosses the slow one.",
        how:
          "Long when the fast SMA is above the slow one; short when below. The most classical " +
          "trend-following family and the genre's historical benchmark.",
      },
      mean_reversion: {
        name: "Mean reversion (z-score)",
        tagline: "Bet that price returns after an extreme.",
        how:
          "Measures how many standard deviations price sits from its rolling mean. Short above " +
          "+entry z, long below −entry z, close when it returns inside ±exit z.",
      },
      breakout: {
        name: "Channel breakout (Donchian)",
        tagline: "Enter when price breaks its recent range.",
        how:
          "Long if the close exceeds the previous N bars' high; short if it loses the low. Exit " +
          "when price re-enters the channel. Multi-bar confirmation optional.",
      },
      volatility_breakout: {
        name: "Volatility-scaled breakout",
        tagline: "A break only counts if it is large for the moment's volatility.",
        how:
          "Like the channel breakout, but the threshold moves a multiple of ATR away: 2% in a " +
          "calm market is not the same as 2% in a storm. The study's best family — and still " +
          "rejected.",
      },
      funding_reversal: {
        name: "Post-extreme funding reversal",
        tagline: "When one side pays too much to stay, bet that it folds.",
        how:
          "Funding at the extreme of its trailing distribution marks a crowded side of the " +
          "book. The signal opens the opposite position and holds it a fixed number of bars, " +
          "no matter what. Uses the real Binance funding series (8h events, joined causally " +
          "bar by bar).",
      },
      intraday_seasonality: {
        name: "Intraday seasonality",
        tagline: "The entry is a clock hour, not a price pattern.",
        how:
          "Enters at a fixed UTC hour and holds a fixed number of bars; optionally only with " +
          "the moving-average trend. It contains no price predictor at all: if it worked, the " +
          "explanation would be flow periodicity, not a pattern.",
      },
    },
    exampleCaption: "Schematic illustration of the rule; not real data.",
    phasesTitle: "Metrics by phase",
    phaseIn: "In-sample",
    phaseOut: "Out-of-sample",
    phaseFull: "Full series",
    buyHold: "Buy and hold",
    strategyLabel: "Strategy",
    testsTitle: "Test battery (out-of-sample)",
    testsSubtitle:
      "Seven checks on the phase the strategy has not seen while choosing parameters. Passing " +
      "them is a necessary condition, never a sufficient one.",
    testReturn: "Positive net return",
    testReturnDesc: "The out-of-sample compound return, net of all costs, is greater than zero.",
    testSharpe: "Positive Sharpe",
    testSharpeDesc: "The mean per-bar return exceeds its noise (annualised Sharpe > 0).",
    testBh: "Beats buy and hold",
    testBhDesc: "Outperforms the passive benchmark with the same costs over the same phase.",
    testNull: "Distinguishable from its own chance",
    testNullDesc:
      "Circular-rotation test: {n} versions of the strategy with positions rotated to a random " +
      "point, same costs. One-sided p-value of the real return against that null.",
    pass: "PASSED",
    fail: "NOT PASSED",
    pValueLabel: "p-value",
    testBootstrap: "Sharpe robust to resampling",
    testBootstrapDesc:
      "Stationary bootstrap (200 block resamples, fixed seed) of the out-of-sample Sharpe. " +
      "Passes if the entire 95% interval sits above zero.",
    testStress: "Survives 2x costs",
    testStressDesc:
      "The same backtest with fee and slippage doubled. Without slack against costs, any " +
      "apparent edge is fragile.",
    testTwin: "Generalises to the twin asset",
    testTwinDesc:
      "The same configuration, untouched, on the other asset (BTC↔ETH). A rule that only " +
      "works on one asset is suspect of being fitted to its history.",
    tornadoTitle: "Parameter sensitivity (tornado)",
    tornadoSubtitle:
      "Change in out-of-sample return when each parameter moves one step of the study grid, " +
      "down (−1) and up (+1).",
    tornadoNote:
      "Large bars = fragile configuration: the result depends on the exact parameter value, " +
      "the classic signature of overfitting. The study's perturbation check, interactive.",
    regimeTitle: "Metrics by volatility regime",
    regimeSubtitle:
      "The out-of-sample phase split by volatility terciles (causal 168h rvol; boundaries " +
      "computed on the in-sample phase only).",
    regimeCol: "Regime",
    regimeBars: "Bars",
    regimeLow: "Calm (low tercile)",
    regimeMid: "Middle",
    regimeHigh: "Turbulent (high tercile)",
    regimeNote:
      "If all the gains live in a single regime, the rule is not capturing an edge: it is " +
      "capturing a kind of era — and eras cannot be chosen in advance.",
    testsDisclaimer:
      "Even with all seven green: the study additionally required ten seeds, fifteen " +
      "walk-forward folds, and Holm correction across every family tried — and none survived. " +
      "A 7/7 here is an invitation to distrust, not a discovery.",
    equityTitle: "Equity curve",
    equitySubtitle:
      "Capital compounded bar by bar, net of costs and funding. The shaded zone is the " +
      "in-sample phase; the vertical line marks the split.",
    signalsTitle: "Price and signals",
    signalsSubtitle:
      "Window of {bars} bars around the selected point. ▲ long entry · ▼ short entry · ✕ exit " +
      "to flat.",
    signalsWindow: "Window position",
    drawdownTitle: "Drawdown",
    maefeTitle: "Maximum excursion per trade (MAE / MFE)",
    maefeSubtitle:
      "For every trade: how far it went in favour (MFE) and against (MAE) relative to the entry " +
      "price, measured with the real highs and lows of each bar in position.",
    maefeX: "MAE — maximum adverse excursion",
    maefeY: "Net trade return",
    medianMae: "Median MAE",
    medianMfe: "Median MFE",
    eRatio: "e-ratio (mean MFE / mean MAE)",
    eRatioNote:
      "An e-ratio ≤ 1 means trades suffer as much or more against as they ever go in favour: " +
      "the entry rule is capturing no asymmetry.",
    tradeStatsTitle: "Trade statistics",
    profitFactor: "Profit factor",
    expectancy: "Expectancy per trade",
    tradeHitRate: "Per-trade hit rate",
    nTradesClosed: "Closed trades",
    meanDuration: "Mean duration (bars)",
    ulcer: "Ulcer index",
    winStreak: "Longest winning streak",
    lossStreak: "Longest losing streak",
    history: {
      title: "Your attempts this session",
      subtitle:
        "Every backtest run in this browser, with its out-of-sample metrics. The highlighted " +
        "row is your best Sharpe — that is, the right tail of your own attempts.",
      clear: "Clear history",
      colFamily: "Family",
      colParams: "Parameters",
      colReturn: "OOS return",
      colTests: "Tests",
      best: "best",
      note:
        "This table is selection bias made visible: publish only the highlighted row and " +
        "delete the rest, and you would have any strategy vendor's brochure. The attempts " +
        "counter above deflates that best result.",
    },
    overlay: {
      title: "Exits and filters",
      stop: "Stop (× ATR)",
      takeProfit: "Take-profit (× ATR)",
      trailing: "Trailing (× ATR)",
      maxBars: "Time exit (bars)",
      trendGate: "Only with the SMA(200) trend",
      regimes: "Allowed regimes",
      low: "low",
      mid: "mid",
      high: "high",
      note:
        "Overlays only remove exposure (re-entry requires a fresh family signal). Causal " +
        "24-bar ATR; regime from causal trailing rvol-168h terciles. Applied to the single " +
        "backtest, not to the walk-forward.",
    },
    wf: {
      title: "Multi-seed walk-forward — the study's protocol",
      subtitle:
        "The thesis's validation, miniaturised and runnable: in every fold, parameters are " +
        "chosen on the validation window and scored exactly once on the 90 test days they " +
        "never saw. Runs on a separate browser thread.",
      budget: "Candidates per fold",
      seeds: "Seeds",
      run: "Run walk-forward",
      running: "Running…",
      seedProgress: "Seed {i} of {n}",
      foldsNote:
        "The study's real geometry: {n} folds with purge and embargo, taken verbatim from " +
        "{run}. Selection by validation Sharpe (a declared simplification of the study's " +
        "penalised fitness).",
      fanTitle: "Concatenated out-of-sample equity, per seed",
      foldsTitle: "Test return per fold (seed average)",
      explainer:
        "Set the budget and seeds and run. The honest result is not a curve: it is a fan — " +
        "the same search with different starting chance produces different outcomes, and " +
        "that dispersion is part of the answer.",
      disclaimer:
        "This walk-forward selects on validation and scores on test, but it remains an " +
        "exploratory tool: the study additionally corrected for multiple comparisons across " +
        "every family tried — and under that correction none survived.",
    },
    attempts: {
      title: "Session attempts counter",
      body:
        "Backtests run in this browser. With this many tries and no skill at all, the best " +
        "Sharpe expected from pure chance is already ≈ {sharpe}.",
      compare:
        "Your best OOS Sharpe: {best}. The chance threshold at your attempt count: {chance}. " +
        "If it does not clear that bar comfortably, selection — not the strategy — explains " +
        "the result.",
    },
    pretrainedTitle: "The families already studied",
    pretrainedBody:
      "The formal-study families exported to the explorer (fifteen of the sixteen with a complete " +
      "study) live there with their ten seeds, walk-forward and metrics.",
    pretrainedLink: "Open the strategy explorer →",
  },
} as const;
