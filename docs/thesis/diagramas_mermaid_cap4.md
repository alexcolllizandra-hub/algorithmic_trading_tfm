# Diagramas Mermaid — Capítulo 4

## Arquitectura del sistema de investigación y MLOps científico

Este documento propone una serie coherente de figuras para el capítulo 4. La
selección principal contiene siete figuras, suficientes para el cuerpo de la
tesis. Los diez diagramas complementarios permiten ampliar cada sección o
documentar detalles técnicos en un anexo.

Principios editoriales:

- representar contratos y responsabilidades, no cifras que envejecen;
- separar cálculo científico, custodia de evidencia y presentación;
- distinguir el identificador de un run de su identidad experimental;
- mostrar explícitamente la causalidad temporal y el aislamiento por fold;
- describir el catálogo como índice, no como fuente primaria de evidencia;
- denominar el holdout como partición originalmente reservada y posteriormente
  consumida, no como holdout todavía intacto;
- diferenciar la consulta web de solo lectura del laboratorio educativo en
  TypeScript.

---

## 4.1 Arquitectura y principios de diseño

### Figura 4.1 — Arquitectura lógica por planos [principal]

**Finalidad.** Presentar el sistema completo sin mezclar procesamiento,
experimentación, custodia de evidencia y consumo.

```mermaid
flowchart TB
    EXT["Fuentes de mercado<br/>data.binance.vision · CCXT"]
    CONTRACTS["Contratos versionados<br/>YAML · Pydantic · ADR"]

    subgraph DATA_PLANE["Plano de datos"]
        INGEST["data<br/>adquisición y barras"]
        QC["validation<br/>esquemas y control de calidad"]
        LAKE["Lago de datos<br/>raw · validated · processed"]
        FEAT["features<br/>variables causales"]
    end

    subgraph RESEARCH_PLANE["Motor de investigación"]
        HYP["strategies · crt<br/>hipótesis parametrizadas"]
        CV["validation.walk_forward<br/>folds con purga y embargo"]
        SEARCH["search · experiments<br/>RS, GA y multi-semilla"]
        BT["backtesting<br/>next-open, costes y funding"]
        EVAL["evaluation<br/>robustez y contraste múltiple"]
    end

    subgraph EVIDENCE_PLANE["Plano de evidencia"]
        TRACK["tracking<br/>identidad y paquete del run"]
        STORE["Artefactos<br/>JSON · YAML · Parquet · figuras"]
        CAT["catalog<br/>índice SQL y procedencia"]
        REPORT["reporting<br/>cierres, tablas y exportaciones"]
    end

    subgraph CONSUMPTION_PLANE["Plano de consumo"]
        API["FastAPI<br/>adaptador de solo lectura"]
        WEB["Next.js<br/>panel de evidencia"]
        LAB["Laboratorio educativo<br/>motor TypeScript separado"]
    end

    FUTURE["Fuera del alcance actual<br/>ejecución live · riesgo de cartera · drift"]

    CONTRACTS --> INGEST
    EXT --> INGEST
    INGEST --> QC
    QC --> LAKE
    LAKE --> FEAT
    CONTRACTS --> HYP
    FEAT --> HYP
    HYP --> CV
    CV --> SEARCH
    SEARCH --> BT
    BT --> EVAL
    SEARCH --> TRACK
    EVAL --> TRACK
    TRACK --> STORE
    STORE --> CAT
    STORE --> REPORT
    CAT --> API
    REPORT --> API
    API --> WEB
    WEB -. "simulación didáctica,<br/>no evidencia canónica" .-> LAB
    EVAL -. "extensión futura" .-> FUTURE

    classDef evidence fill:#fff7ed,stroke:#c2410c,color:#7c2d12
    classDef optional fill:#f3f4f6,stroke:#6b7280,color:#374151,stroke-dasharray:5 5
    class TRACK,STORE,CAT,REPORT evidence
    class FUTURE optional
```

**Pie sugerido.** Arquitectura lógica del monolito modular. El flujo científico
transforma contratos y datos en evidencia persistida; las interfaces consultan
esa evidencia sin intervenir en la selección de estrategias.

**Evidencia:** `src/perp_lab/`, `docs/methodology/pipeline_end_to_end.md`,
`docs/platform/README.md`.

### Figura 4.1A — Fronteras del monolito modular [complementaria]

**Finalidad.** Justificar por qué CLI, notebooks y web no son la ubicación de la
lógica científica canónica.

```mermaid
flowchart LR
    subgraph INTERFACES["Interfaces"]
        CLI["CLI"]
        NB["Notebooks"]
        API["FastAPI"]
        WEB["Next.js"]
    end

    subgraph CROSS["Contratos transversales"]
        CONFIG["config<br/>YAML y Pydantic"]
        UTILS["utils<br/>UTC, hashes y semillas"]
    end

    subgraph CORE["Núcleo científico importable"]
        DATA["data · validation"]
        FEATURES["features · labeling"]
        STRATEGIES["strategies · crt"]
        ENGINE["backtesting"]
        SEARCH["search · experiments"]
        EVALUATION["evaluation"]
    end

    subgraph EVIDENCE["Custodia de evidencia"]
        TRACKING["tracking"]
        REPORTING["reporting"]
        ARTIFACTS["Artefactos inmutables"]
        CATALOG["catalog"]
    end

    CLI --> CONFIG
    CLI --> CORE
    NB --> CONFIG
    NB --> CORE
    CONFIG --> CORE
    UTILS --> CORE
    CORE --> TRACKING
    CORE --> REPORTING
    TRACKING --> ARTIFACTS
    REPORTING --> ARTIFACTS
    ARTIFACTS --> CATALOG
    API --> CATALOG
    API --> ARTIFACTS
    WEB --> API

    NB -. "narra resultados;<br/>no redefine algoritmos" .-> ARTIFACTS
    API -. "no ejecuta búsqueda<br/>ni backtest" .-> CORE
```

**Pie sugerido.** Fronteras de responsabilidad. Las interfaces orquestan o
presentan; la lógica reutilizable permanece en módulos Python testeables.

### Figura 4.1B — Ciclo de vida de la configuración [complementaria]

**Finalidad.** Mostrar que el contrato ejecutado es la configuración resuelta,
no una llamada abreviada ni valores dispersos en código.

```mermaid
flowchart LR
    DATA_YAML["data_contract.yaml"]
    EXP_YAML["experiment.yaml"]
    CALL["Parámetros de invocación<br/>familia · activo · semilla · motor"]
    LOAD["Carga y normalización"]
    VALID{"Validación Pydantic<br/>e invariantes cruzados"}
    ERROR["Error explícito<br/>el run no comienza"]
    RESOLVED["Configuración resuelta<br/>completa y validada"]
    EXECUTE["Ejecución científica"]
    SNAPSHOT["resolved_experiment_config.yaml"]
    CONFIG_HASH["config_sha256"]
    IDENTITY["run_identity.json"]
    CATALOG["Configuración indexada<br/>en el catálogo"]

    DATA_YAML --> LOAD
    EXP_YAML --> LOAD
    CALL --> LOAD
    LOAD --> VALID
    VALID -->|"inválida"| ERROR
    VALID -->|"admisible"| RESOLVED
    RESOLVED --> EXECUTE
    RESOLVED --> SNAPSHOT
    RESOLVED --> CONFIG_HASH
    CONFIG_HASH --> IDENTITY
    SNAPSHOT --> CATALOG
    EXECUTE --> CATALOG
```

**Pie sugerido.** Ciclo config-as-code. La configuración se valida antes de
ejecutar y su forma resuelta queda incorporada a la evidencia del experimento.

---

## 4.2 Linaje, almacenamiento y calidad del dato

### Figura 4.2 — Linaje reproducible e integridad [principal]

**Finalidad.** Sustituir los diagramas separados de DAG y layout por una sola
figura que conecte transformación, particionado y manifiestos.

```mermaid
flowchart TB
    BV["data.binance.vision<br/>klines · mark price · funding"]
    CCXT["CCXT incremental"]
    RAW["data/raw<br/>bytes originales, sin modificación"]
    PARSE["Parseo canónico<br/>UTC · open_time · left-closed"]
    SCHEMA{"Esquema y contrato<br/>estructural válidos"}
    REJECT["Fallo explícito<br/>no se promociona el dataset"]
    QC["Informe QC<br/>huecos · duplicados · OHLC · extremos"]
    VALID["data/validated<br/>base de 5 minutos"]
    RESAMPLE["Agregación determinista<br/>5m → 15m y 1h"]
    SPLIT["Partición cronológica<br/>según contrato"]
    DEV["development<br/>entrada permitida al pipeline"]
    RESERVED["Partición originalmente reservada<br/>posteriormente consumida"]
    MANIFEST["Manifiesto por dataset<br/>periodo · filas · SHA-256 · procedencia"]
    VERIFY{"Rehash antes del uso"}
    ADMIT["Dataset admisible"]
    ABORT["Abortar run"]

    BV --> RAW
    CCXT --> RAW
    RAW --> PARSE
    PARSE --> SCHEMA
    SCHEMA -->|"no"| REJECT
    SCHEMA -->|"sí"| QC
    QC --> VALID
    VALID --> RESAMPLE
    VALID --> SPLIT
    RESAMPLE --> SPLIT
    SPLIT --> DEV
    SPLIT --> RESERVED
    DEV --> MANIFEST
    RESERVED --> MANIFEST
    DEV --> VERIFY
    MANIFEST --> VERIFY
    VERIFY -->|"coincide"| ADMIT
    VERIFY -->|"no coincide"| ABORT

    classDef consumed fill:#fee2e2,stroke:#b91c1c,color:#7f1d1d
    classDef failure fill:#fef2f2,stroke:#dc2626,color:#7f1d1d
    class RESERVED consumed
    class REJECT,ABORT failure
```

**Pie sugerido.** Linaje reproducible de los datos. Las transformaciones parten
de archivos originales inmutables y cada salida se vincula a un manifiesto cuyo
digest se vuelve a comprobar antes de utilizarla.

**Evidencia:** `configs/data_contract.yaml`, `src/perp_lab/data/`,
`src/perp_lab/validation/`, `data/manifests/`.

### Figura 4.2A — Política de control de calidad [complementaria]

**Finalidad.** Distinguir errores estructurales que bloquean el pipeline de
anomalías que se conservan y documentan.

```mermaid
flowchart TB
    INPUT["Dataset candidato"]
    STRICT{"Columnas, tipos y rangos<br/>cumplen el esquema estricto"}
    STOP["Detener validación"]
    DUP["Detectar timestamps duplicados"]
    ORDER["Comprobar monotonicidad temporal"]
    GAPS["Cuantificar huecos y cobertura"]
    OHLC["Comprobar invariantes OHLC"]
    EXTREME["Marcar observaciones extremas"]
    REPORT["QualityReport<br/>conteos, periodo y cobertura"]
    ADMISSIBLE{"Cumple el contrato<br/>de calidad"}
    VALIDATED["Registrar como validado"]
    FLAGS["Conservar flags para EDA"]
    NO_DROP["No auto-drop"]
    NO_FILL["No forward-fill"]
    NO_REPAIR["No reparación silenciosa"]

    INPUT --> STRICT
    STRICT -->|"no"| STOP
    STRICT -->|"sí"| DUP
    DUP --> ORDER
    ORDER --> GAPS
    GAPS --> OHLC
    OHLC --> EXTREME
    EXTREME --> REPORT
    REPORT --> ADMISSIBLE
    ADMISSIBLE -->|"no"| STOP
    ADMISSIBLE -->|"sí"| VALIDATED
    EXTREME --> FLAGS
    FLAGS -.-> NO_DROP
    FLAGS -.-> NO_FILL
    FLAGS -.-> NO_REPAIR
```

**Pie sugerido.** Política de control de calidad. Los errores de contrato
bloquean la promoción del dataset; las observaciones extremas se marcan y
conservan para no confundir eventos reales con errores de alimentación.

### Figura 4.2B — Modelo de almacenamiento científico [complementaria]

**Finalidad.** Explicar por qué conviven filesystem, Parquet, SQL y un backend
opcional de objetos.

```mermaid
flowchart TB
    PRODUCERS["Pipeline de datos y experimentos"]

    subgraph FILES["Fuente primaria de evidencia"]
        DATASETS["Parquet de datos<br/>raw · validated · processed"]
        RUNS["artifacts/runs/run_id<br/>config, ledgers y métricas"]
        REPORTS["reports<br/>figuras, tablas y cierres"]
        MANIFESTS["Manifiestos y receipts<br/>SHA-256"]
    end

    subgraph INDEX["Índice consultable"]
        SQLITE["SQLite + SQLAlchemy<br/>modo local"]
        DUCK["DuckDB<br/>consulta de Parquet"]
    end

    OBJECT["Object storage / Supabase<br/>backend opcional"]
    API["API de consulta"]

    PRODUCERS --> DATASETS
    PRODUCERS --> RUNS
    PRODUCERS --> REPORTS
    DATASETS --> MANIFESTS
    RUNS --> MANIFESTS
    MANIFESTS --> SQLITE
    RUNS --> SQLITE
    DATASETS --> DUCK
    RUNS --> DUCK
    RUNS -. "con credenciales" .-> OBJECT
    SQLITE --> API
    DUCK --> API

    NOTE["Regla: SQL indexa la evidencia;<br/>no sustituye los archivos originales"]
    SQLITE --> NOTE

    classDef optional fill:#f3f4f6,stroke:#6b7280,color:#374151,stroke-dasharray:5 5
    class OBJECT optional
```

**Pie sugerido.** Persistencia híbrida. Los archivos constituyen la evidencia
primaria; SQL mantiene metadatos consultables y DuckDB analiza los artefactos
Parquet sin duplicarlos.

---

## 4.3 Contrato temporal, validación y ejecución

### Figura 4.3 — Contrato temporal causal [principal]

**Finalidad.** Corregir la figura actual: una señal calculada al cierre de la
barra `t` se aplica desde la apertura de `t+1`, no desde `t+2`.

```mermaid
sequenceDiagram
    participant M as Mercado
    participant B as Constructor de barras
    participant F as Motor de features
    participant S as Estrategia
    participant E as Backtester
    participant L as Ledger

    M->>B: Observaciones dentro de la barra t
    Note over B: La barra aún no es observable como cerrada
    M->>B: Cierre de la barra t
    B->>F: OHLCV cerrado y disponible
    F->>F: Rolling o expanding usando pasado y presente cerrado
    F->>S: Features disponibles en signal_time
    S->>S: Calcula side_t al cierre de t
    S->>E: Posición objetivo para la barra siguiente
    M->>E: Apertura de t+1
    E->>E: position_t+1 = side_t
    E->>L: Retorno open_t+1 → open_t+2
    E->>L: Fees + slippage + funding realizado

    Note over F,S: El futuro no modifica valores históricos
    Note over E,L: La señal nunca se ejecuta en su propio cierre
```

**Pie sugerido.** Contrato temporal de agregación, decisión y ejecución. Una
barra solo se utiliza después de cerrarse; la posición resultante comienza en la
apertura inmediatamente posterior y obtiene el retorno open-to-open.

**Evidencia:** `src/perp_lab/data/bars.py`,
`src/perp_lab/features/causal.py`,
`src/perp_lab/backtesting/engine.py`.

### Figura 4.3A — Aislamiento walk-forward por fold [complementaria]

**Finalidad.** Mostrar dónde actúan purga, embargo, selección y test sin sugerir
retroalimentación entre folds.

```mermaid
flowchart LR
    subgraph FOLD_K["Fold exterior k"]
        TRAIN["TRAIN<br/>ajuste de transformaciones"]
        EMBARGO["EMBARGO<br/>separación derivada"]
        VAL["VALIDATION<br/>búsqueda y ranking"]
        FREEZE["Candidato congelado<br/>parámetros + fingerprint"]
        PURGE["PURGA<br/>sin solape de holdings"]
        TEST["TEST<br/>una evaluación OOS"]
    end

    NEXT["Fold k+1<br/>búsqueda nueva e independiente"]
    CONCAT["Concatenación OOS<br/>solo tras cerrar los folds"]
    RESERVED["Partición originalmente reservada<br/>ya consumida; no se reutiliza"]

    TRAIN --> EMBARGO
    EMBARGO --> VAL
    VAL --> FREEZE
    FREEZE --> PURGE
    PURGE --> TEST
    TEST --> CONCAT
    NEXT --> CONCAT

    TEST -. "sin realimentación" .-> VAL
    VAL -. "no observa otros folds" .- NEXT
    CONCAT -. "no crea un nuevo holdout" .-> RESERVED

    classDef consumed fill:#fee2e2,stroke:#b91c1c,color:#7f1d1d
    class RESERVED consumed
```

**Pie sugerido.** Validación walk-forward expandida. La búsqueda se repite de
forma independiente en cada fold, el candidato se congela antes del test y los
segmentos OOS solo se agregan después de cerrar la selección.

### Figura 4.3B — Contabilidad del backtest [complementaria]

**Finalidad.** Hacer auditable la formación del retorno neto y del ledger.

```mermaid
flowchart TB
    SIGNAL["side_t<br/>calculado al cierre"]
    SHIFT["position_t+1 = shift(side, 1)"]
    MARKET["Retorno open-to-open"]
    GROSS["gross_return<br/>position × oo_return"]
    TURNOVER["turnover<br/>|position - position anterior|"]
    FEE["fee<br/>turnover × tarifa"]
    SLIP["slippage<br/>turnover × deslizamiento"]
    FUND_RATE["Funding publicado<br/>as-of-past"]
    FUND["funding<br/>position × rate"]
    NET["net_return<br/>gross - fee - slippage - funding"]
    LEDGER["Ledger por barra"]
    EQUITY["Equity y drawdown"]
    METRICS["Métricas 24/7<br/>365 días"]
    LAST["Última barra eliminada<br/>retorno futuro indefinido"]

    SIGNAL --> SHIFT
    SHIFT --> GROSS
    MARKET --> GROSS
    SHIFT --> TURNOVER
    TURNOVER --> FEE
    TURNOVER --> SLIP
    SHIFT --> FUND
    FUND_RATE --> FUND
    GROSS --> NET
    FEE --> NET
    SLIP --> NET
    FUND --> NET
    NET --> LEDGER
    LEDGER --> EQUITY
    EQUITY --> METRICS
    MARKET --> LAST
```

**Pie sugerido.** Contabilidad del motor cost-aware. El ledger conserva por
separado retorno bruto, rotación, costes, funding y retorno neto, permitiendo
repricing y auditoría posterior.

---

## 4.4 Orquestación experimental reproducible

### Figura 4.4 — Búsqueda aislada y captura de evidencia [principal]

**Finalidad.** Integrar configuración, paridad RS/GA, selección, test y escritura
del paquete del run.

```mermaid
flowchart TB
    CONFIG["Configuración resuelta<br/>familia · activo · costes · presupuesto B"]
    PLAN["Plan walk-forward<br/>folds y calendario de semillas"]
    FOLD["Abrir exclusivamente el fold k"]
    BUNDLE["Bundle aislado<br/>train · validation · test sellado"]

    subgraph RS["Random Search"]
        RS_SEED["Stream RNG propio"]
        RS_LOOP["Proponer y evaluar<br/>solo en validation"]
        RS_LEDGER["Ledger de evaluaciones<br/>válidas, únicas y cacheadas"]
    end

    subgraph GA["Algoritmo genético"]
        GA_SEED["Stream RNG propio"]
        GA_LOOP["Evolucionar y evaluar<br/>solo en validation"]
        GA_LEDGER["Ledger de evaluaciones<br/>válidas, únicas y cacheadas"]
    end

    PARITY{"¿Presupuesto efectivo<br/>comparable?"}
    FAIL["Comparación no admisible"]
    SELECT["Seleccionar por validation"]
    FREEZE["Congelar candidato<br/>antes de abrir TEST"]
    TEST["Evaluar una vez en TEST"]
    MORE{"¿Quedan folds?"}
    OOS["Concatenar segmentos OOS"]

    PACKAGE["Paquete de evidencia del run"]
    DEFINITIONS["Config · folds · semillas<br/>espacio · objetivo"]
    RESULTS["Candidatos · ganadores<br/>equity · trades · métricas"]
    PROVENANCE["Datos · git · entorno<br/>identidad · warnings"]

    CONFIG --> PLAN
    PLAN --> FOLD
    FOLD --> BUNDLE
    BUNDLE --> RS_SEED
    BUNDLE --> GA_SEED
    RS_SEED --> RS_LOOP
    GA_SEED --> GA_LOOP
    RS_LOOP --> RS_LEDGER
    GA_LOOP --> GA_LEDGER
    RS_LEDGER --> PARITY
    GA_LEDGER --> PARITY
    PARITY -->|"no"| FAIL
    PARITY -->|"sí"| SELECT
    SELECT --> FREEZE
    FREEZE --> TEST
    TEST --> MORE
    MORE -->|"sí"| FOLD
    MORE -->|"no"| OOS
    OOS --> PACKAGE
    CONFIG --> PACKAGE
    PACKAGE --> DEFINITIONS
    PACKAGE --> RESULTS
    PACKAGE --> PROVENANCE
```

**Pie sugerido.** Orquestación aislada por fold. Ambos motores comparten espacio,
objetivo y presupuesto efectivo; la selección utiliza únicamente validación y
el test se consulta una vez después de congelar el candidato.

**Evidencia:** `src/perp_lab/search/runner.py`,
`src/perp_lab/search/evaluator.py`, `src/perp_lab/experiments/`,
`src/perp_lab/tracking/`.

### Figura 4.4A — Derivación determinista de semillas [complementaria]

**Finalidad.** Explicar independencia y reconstrucción de los flujos aleatorios
sin fijar valores numéricos que pertenezcan a un run concreto.

```mermaid
flowchart TB
    BASE["Semilla base registrada"]
    NAMESPACE["Namespace estable<br/>engine · regime · bootstrap"]
    KEYS["Claves ordenadas<br/>activo · timeframe · fold · seed"]
    LABEL["Etiqueta canónica"]
    DIGEST["BLAKE2b<br/>digest de 16 bytes"]
    SEQUENCE["NumPy SeedSequence<br/>entropy + spawn_key"]

    GLOBAL["Estado global<br/>Python · NumPy · PYTHONHASHSEED"]
    RS["Stream Random Search"]
    GA["Stream algoritmo genético"]
    REGIME["Stream de régimen por fold"]
    BOOT["Stream bootstrap"]
    RECORD["seed_schedule.json<br/>direcciones reproducibles"]

    BASE --> GLOBAL
    BASE --> SEQUENCE
    NAMESPACE --> LABEL
    KEYS --> LABEL
    LABEL --> DIGEST
    DIGEST --> SEQUENCE
    SEQUENCE --> RS
    SEQUENCE --> GA
    SEQUENCE --> REGIME
    SEQUENCE --> BOOT
    RS --> RECORD
    GA --> RECORD
    REGIME --> RECORD
    BOOT --> RECORD

    PROPERTY["Propiedad: añadir otro consumidor<br/>no desplaza streams existentes"]
    SEQUENCE --> PROPERTY
```

**Pie sugerido.** Árbol lógico de semillas. Cada stream queda direccionado por
una etiqueta estable y puede reconstruirse desde la semilla base sin acoplar
componentes independientes.

---

## 4.5 Identidad, catálogo y custodia de evidencia

### Figura 4.5 — Cadena de identidad y trazabilidad [principal]

**Finalidad.** Separar la dirección física del run de la identidad científica
del experimento.

```mermaid
flowchart TB
    RUN_ID["run_id<br/>dirección única y ordenable"]
    RUN_DIR["artifacts/runs/run_id"]

    CONFIG["Hash de configuración resuelta"]
    CONTRACT["Hash de contratos metodológicos"]
    DATA["Hash del mapa de datasets"]
    COMMIT["Commit ejecutado"]
    DIFF["Hash del diff relevante"]
    UNTRACKED["Hash de archivos no trackeados relevantes"]
    FINGERPRINT["Fingerprint experimental<br/>SHA-256 truncado a 16 caracteres"]

    COMPARE{"¿Fingerprints iguales?"}
    SAME["Mismo experimento"]
    DIFFERENT["Experimentos distintos"]
    PROVISIONAL["Run identificado exactamente,<br/>pero provisional si el worktree está sucio"]

    PACKAGE["Paquete del run"]
    CONFIG_FILE["Configuración y contratos"]
    DATA_FILE["Manifiestos de datos"]
    CODE_FILE["Git y entorno"]
    OUTPUTS["Candidatos, ledgers y métricas"]
    JOURNAL["Journal y checkpoint"]
    CATALOG["Catálogo SQL<br/>índice sobre el paquete"]

    RUN_ID --> RUN_DIR
    CONFIG --> FINGERPRINT
    CONTRACT --> FINGERPRINT
    DATA --> FINGERPRINT
    COMMIT --> FINGERPRINT
    DIFF --> FINGERPRINT
    UNTRACKED --> FINGERPRINT
    FINGERPRINT --> COMPARE
    COMPARE -->|"sí"| SAME
    COMPARE -->|"no"| DIFFERENT
    DIFF --> PROVISIONAL
    UNTRACKED --> PROVISIONAL

    RUN_DIR --> PACKAGE
    FINGERPRINT --> PACKAGE
    PACKAGE --> CONFIG_FILE
    PACKAGE --> DATA_FILE
    PACKAGE --> CODE_FILE
    PACKAGE --> OUTPUTS
    PACKAGE --> JOURNAL
    PACKAGE --> CATALOG
```

**Pie sugerido.** Cadena de identidad experimental. El `run_id` localiza una
ejecución, mientras que el fingerprint resume configuración, contratos, datos y
estado relevante del código; el catálogo indexa el paquete sin reemplazarlo.

**Evidencia:** `src/perp_lab/tracking/identity.py`,
`src/perp_lab/tracking/run.py`, `docs/decisions/0018-identity-diff-scoped-to-relevant-dirs.md`.

### Figura 4.5A — Modelo relacional del catálogo [complementaria]

**Finalidad.** Sustituir el ERD actual, cuyas relaciones no coinciden con las
claves foráneas de `catalog/models.py`.

```mermaid
erDiagram
    STUDY {
        int id PK
        string key
        string timeframe
        datetime holdout_start
        datetime holdout_end
    }
    EXPERIMENT_ROUND {
        int id PK
        int study_id FK
        string key
        int sequence
        string status
    }
    STRATEGY_FAMILY {
        int id PK
        int study_id FK
        string key
        string status
    }
    STRATEGY_SPEC {
        int id PK
        int family_id FK
        string spec_hash
        json params
    }
    RUN {
        int id PK
        string run_id
        int study_id FK
        int round_id FK
        int family_id FK
        string identity_fingerprint
        string status
    }
    RUN_SEED {
        int id PK
        int run_id FK
        int seed
        float sharpe
        string status
    }
    FOLD {
        int id PK
        int run_id FK
        int fold_index
        datetime train_start
        datetime test_end
        int purge_bars
        int embargo_bars
    }
    FOLD_RESULT {
        int id PK
        int fold_id FK
        int run_seed_id FK
        int spec_id FK
        float sharpe
        string status
    }
    SEARCH_EVALUATION {
        int id PK
        int run_id FK
        int spec_id FK
        int fold_index
        float objective
        string status
    }
    METRIC {
        int id PK
        int study_id FK
        string scope
        string metric_key
        float value
        string status
    }
    GATE_RESULT {
        int id PK
        int round_id FK
        int family_id FK
        string criterion_key
        string verdict
    }
    ARTIFACT {
        int id PK
        int run_id FK
        int study_id FK
        string uri
        string content_sha256
        string status
    }
    MONTE_CARLO_RUN {
        int id PK
        int study_id FK
        int family_id FK
        int artifact_id FK
        string method
        string status
    }
    HOLDOUT_REGISTRY {
        int id PK
        int study_id FK
        string candidate_fingerprint
        datetime opened_at
        boolean audited
        string status
    }

    STUDY ||--o{ EXPERIMENT_ROUND : contiene
    STUDY ||--o{ STRATEGY_FAMILY : define
    STUDY ||--o{ RUN : registra
    STUDY ||--o{ METRIC : agrega
    STUDY o|--o{ ARTIFACT : indexa
    STUDY ||--o{ MONTE_CARLO_RUN : agrupa
    STUDY ||--o{ HOLDOUT_REGISTRY : audita

    EXPERIMENT_ROUND o|--o{ RUN : clasifica
    EXPERIMENT_ROUND ||--o{ GATE_RESULT : aplica
    STRATEGY_FAMILY ||--o{ STRATEGY_SPEC : parametriza
    STRATEGY_FAMILY o|--o{ RUN : ejecuta
    STRATEGY_FAMILY ||--o{ GATE_RESULT : recibe
    STRATEGY_FAMILY ||--o{ MONTE_CARLO_RUN : analiza

    RUN ||--o{ RUN_SEED : deriva
    RUN ||--o{ FOLD : divide
    RUN ||--o{ SEARCH_EVALUATION : evalua
    RUN o|--o{ ARTIFACT : produce
    FOLD ||--o{ FOLD_RESULT : produce
    RUN_SEED ||--o{ FOLD_RESULT : obtiene
    STRATEGY_SPEC o|--o{ FOLD_RESULT : seleccionada
    STRATEGY_SPEC o|--o{ SEARCH_EVALUATION : candidata
    ARTIFACT o|--o{ MONTE_CARLO_RUN : almacena_trayectorias
```

**Pie sugerido.** Catálogo científico. Las tablas normalizan estudios, runs,
folds, métricas y procedencia; los resultados masivos permanecen en artefactos
externos identificados por URI y digest.

---

## 4.6 Gobernanza y quality gates

### Figura 4.6 — Puertas de calidad científica [principal]

**Finalidad.** Representar por separado la CI obligatoria y las comprobaciones
locales que dependen del lago de datos o de otros entornos.

```mermaid
flowchart LR
    CHANGE["Push o pull request"]

    subgraph CI["GitHub Actions · gate automático"]
        CHECKOUT["Checkout"]
        UV["uv sync --extra dev"]
        LINT["Ruff lint"]
        FORMAT["Ruff format --check"]
        CLAIMS["Stale-claims sweep"]
        TESTS["Pytest sin red"]
        RESULT{"¿Todos los pasos pasan?"}
    end

    GREEN["Check correcto"]
    RED["Check fallido"]

    subgraph LOCAL["Controles locales complementarios"]
        PYRIGHT["Pyright"]
        NOTEBOOKS["Determinismo de notebooks<br/>requiere lago local"]
        FRONT["Lint · tipos · tests · build web"]
    end

    ADR["ADRs y decisiones"]
    PROTOCOL["Contratos y protocolos"]
    ARTIFACTS["Artefactos verificables"]
    NARRATIVE["Afirmaciones documentales"]

    CHANGE --> CHECKOUT
    CHECKOUT --> UV
    UV --> LINT
    LINT --> FORMAT
    FORMAT --> CLAIMS
    CLAIMS --> TESTS
    TESTS --> RESULT
    RESULT -->|"sí"| GREEN
    RESULT -->|"no"| RED

    ADR --> NARRATIVE
    PROTOCOL --> NARRATIVE
    ARTIFACTS --> CLAIMS
    NARRATIVE --> CLAIMS

    CHANGE -.-> PYRIGHT
    CHANGE -.-> NOTEBOOKS
    CHANGE -.-> FRONT
```

**Pie sugerido.** Puertas de calidad del repositorio. La CI verifica entorno,
estilo, tests y coherencia entre afirmaciones y evidencia; otros controles
permanecen locales por sus dependencias operativas.

**Evidencia:** `.github/workflows/ci.yml`,
`scripts/check_stale_claims.py`, `scripts/verify_determinism.py`,
`apps/web/package.json`.

### Figura 4.6A — Ciclo de gobernanza de una afirmación [complementaria]

**Finalidad.** Explicar qué aporta el término “MLOps científico” más allá de
automatizar tests.

```mermaid
flowchart TB
    QUESTION["Pregunta de investigación"]
    PROTOCOL["Hipótesis y criterio<br/>pre-registrados"]
    IMPLEMENT["Implementación versionada"]
    TEST["Tests de propiedades<br/>causalidad · aislamiento · determinismo"]
    RUN["Run identificado"]
    EVIDENCE["Artefactos con procedencia"]
    GATE["Aplicación de gates"]
    CLAIM["Afirmación académica"]
    AUDIT{"¿La afirmación conserva<br/>evidencia vigente?"}
    PUBLISH["Publicable"]
    SUPERSEDE["Marcar como obsoleta<br/>o superseded"]
    ADR["ADR o registro de incidente"]

    QUESTION --> PROTOCOL
    PROTOCOL --> IMPLEMENT
    IMPLEMENT --> TEST
    TEST --> RUN
    RUN --> EVIDENCE
    EVIDENCE --> GATE
    GATE --> CLAIM
    CLAIM --> AUDIT
    EVIDENCE --> AUDIT
    AUDIT -->|"sí"| PUBLISH
    AUDIT -->|"no"| SUPERSEDE
    SUPERSEDE --> ADR
    ADR --> PROTOCOL
```

**Pie sugerido.** Ciclo de gobernanza científica. Una conclusión solo es
publicable si puede rastrearse hasta un protocolo, una implementación testeada y
artefactos vigentes; los resultados invalidados se conservan como evidencia
superseded.

---

## 4.7 Consulta y comunicación de evidencia

### Figura 4.7 — Serving de solo lectura [principal]

**Finalidad.** Mostrar cómo se publica la evidencia sin permitir que la capa web
modifique el proceso experimental.

```mermaid
flowchart LR
    RESEARCH["CLI y pipeline Python<br/>únicos productores canónicos"]

    subgraph SOURCES["Evidencia persistida"]
        RUNS["artifacts/runs"]
        MANIFESTS["data/manifests"]
        REPORTS["reports"]
        CATALOG["Catálogo SQL"]
        DEV["Partición development"]
    end

    subgraph API["FastAPI · adaptador de solo lectura"]
        VALIDATE["Validación de run_id<br/>y rutas permitidas"]
        LOAD["Loaders de artefactos"]
        MODELS["Respuestas Pydantic"]
        GET["Endpoints GET"]
    end

    WEB["Next.js<br/>panel y diagnóstico"]
    USER["Investigador o tribunal"]
    MUTATE["Búsqueda · backtest · tuning"]
    RESERVED["Datos de la partición consumida<br/>no servidos como development"]

    RESEARCH --> RUNS
    RESEARCH --> MANIFESTS
    RESEARCH --> REPORTS
    RESEARCH --> CATALOG
    RUNS --> LOAD
    MANIFESTS --> LOAD
    REPORTS --> LOAD
    CATALOG --> LOAD
    DEV --> LOAD
    VALIDATE --> LOAD
    LOAD --> MODELS
    MODELS --> GET
    GET --> WEB
    WEB --> USER

    GET -. "no invoca" .-> MUTATE
    WEB -. "sin acceso directo" .-> RUNS
    RESERVED -. "bloqueado para endpoints de mercado" .-> API

    classDef forbidden fill:#f3f4f6,stroke:#6b7280,color:#374151,stroke-dasharray:5 5
    classDef consumed fill:#fee2e2,stroke:#b91c1c,color:#7f1d1d
    class MUTATE forbidden
    class RESERVED consumed
```

**Pie sugerido.** Arquitectura de consulta. FastAPI adapta artefactos existentes
a modelos tipados y Next.js los presenta; ninguna de estas capas ejecuta la
búsqueda canónica ni modifica los runs.

**Evidencia:** `src/perp_lab/api/`, `apps/web/`,
`docs/platform/README.md`.

### Figura 4.7A — Portal de evidencia frente a laboratorio educativo [complementaria]

**Finalidad.** Resolver la aparente contradicción entre una plataforma de solo
lectura y la existencia de un motor TypeScript en el navegador.

```mermaid
flowchart TB
    USER["Usuario web"]

    subgraph PORTAL["Portal de evidencia"]
        PAGES["Panel · experimentos · resultados · diagnóstico"]
        API["FastAPI"]
        CANON["Artefactos canónicos<br/>producidos por Python"]
        CLAIMS["Cifras y conclusiones de la tesis"]
    end

    subgraph EDUCATIONAL["Laboratorio educativo"]
        INPUTS["Parámetros interactivos"]
        TS["Motor TypeScript<br/>simulación en navegador"]
        DISPLAY["Resultado didáctico"]
    end

    USER --> PAGES
    PAGES --> API
    API --> CANON
    CANON --> CLAIMS

    USER --> INPUTS
    INPUTS --> TS
    TS --> DISPLAY

    DISPLAY -. "no promociona estrategias" .-> CLAIMS
    DISPLAY -. "no escribe en artifacts/runs" .-> CANON
```

**Pie sugerido.** Separación entre comunicación y experimentación didáctica. El
portal presenta la evidencia canónica de Python; el laboratorio interactivo
explica mecanismos, pero sus simulaciones no sustentan conclusiones de la tesis.

---

## Selección editorial recomendada

Para el cuerpo principal:

1. Figura 4.1 — arquitectura lógica por planos.
2. Figura 4.2 — linaje reproducible e integridad.
3. Figura 4.3 — contrato temporal causal.
4. Figura 4.4 — búsqueda aislada y captura de evidencia.
5. Figura 4.5 — identidad y trazabilidad.
6. Figura 4.6 — quality gates científicos.
7. Figura 4.7 — serving de solo lectura.

Para subsecciones técnicas o anexo:

- 4.1A fronteras modulares;
- 4.1B configuración como código;
- 4.2A política QC;
- 4.2B persistencia híbrida;
- 4.3A walk-forward;
- 4.3B contabilidad del backtest;
- 4.4A árbol de semillas;
- 4.5A ERD del catálogo;
- 4.6A ciclo de gobernanza;
- 4.7A portal frente a laboratorio educativo.

La captura `fig_4_11_dashboard_es.png` puede conservarse como ilustración de la
interfaz, pero no debería sustituir la Figura 4.7 arquitectónica ni utilizarse
como fuente primaria de resultados.
