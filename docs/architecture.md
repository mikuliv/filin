# Архитектура

## Реализованная архитектура

```mermaid
flowchart LR
  S[Безопасный сценарий] --> T[traffic-client]
  T --> M[Start/end markers]
  T --> C[capture-sidecar]
  C --> P[PCAP: Docker named volume]
  P --> Z[Offline Zeek]
  Z --> L[Zeek logs]
  L --> N[Нормализация]
  M --> I[Sensor-aligned interval]
  N --> R[Корреляция]
  I --> R
  R --> F[Feature builder]
  F --> D[Dataset]
  D --> A[Audits и ML evaluation]
```

`traffic-client` выполняет безопасные действия в изолированной сети. Capture-sidecar наблюдает тот же network namespace; PCAP является первичным источником sensor observations. Zeek logs нормализуются до корреляции. Execution markers используются только для временной привязки и исключаются из feature aggregation.

В v0.3.7 internal validation каждый execution дополнительно захватывается в отдельный PCAP внутри namespace `traffic-client`. Такая изоляция сохраняет marker-семантику, но не позволяет откату Docker wall-clock смешать соседние окна. Marker control journal служит только аудитируемым источником границ; labels и control records не агрегируются в model features.

## Campaign separation

```mermaid
flowchart TB
  C[Campaign] --> TR[Независимые train runs]
  C --> TE[Независимые test runs]
  TR --> SEL[Model selection]
  TE --> EXT[External evaluation]
  EXT --> FR[Зафиксированная модель]
  FR --> RB[Robustness runs: только predict/evaluation]
```

## Концептуальная будущая архитектура

```mermaid
flowchart LR
  D[Проверенный sensor dataset] --> M[Модель]
  M -. будущая работа .-> IC[Incident card]
  IC -. будущая работа .-> MA[MITRE ATT&CK mapping]
  MA -. будущая работа .-> SG[Sigma draft]
  SG -. будущая работа .-> SIEM[SIEM integration]
  IC -. будущая работа .-> UI[Analyst interface]
```

Концептуальная архитектура. На текущем этапе полностью не реализована.

## network_sensor_v0_5_hierarchical

```mermaid
flowchart LR
  W["Текущее окно и causal asset history"] --> F["Temporal/contextual features"]
  F --> G["Calibrated benign/suspicious gate"]
  F --> O["Benign-only OOD guard"]
  G --> U["Abstention policy"]
  O --> U
  U -->|"достаточно evidence"| S["Calibrated attack subtype"]
  U -->|"недостаточно evidence"| I["insufficient_evidence"]
  S --> T["Causal temporal accumulator"]
  T --> D["benign / suspicious_unclassified / attack_candidate"]
```

Detection отделён от subtype classification: benign gate не вызывает subtype model. OOD не конвертируется в attack автоматически. Asset state сбрасывается между runs и folds; warm-up инициализирует state, но исключён из support и metrics.

## Class-conditional evidence v0.3.8

```mermaid
flowchart LR
  W["Causal window features"] --> G["Calibrated benign/attack gate"]
  G --> S["Calibrated subtype probabilities"]
  S --> C["Mondrian conformal set"]
  W --> K["Per-class robust-scaled kNN support"]
  C --> E["Evidence reconciliation"]
  K --> E
  E --> A["Causal episode accumulator"]
  A --> D["benign / review / attack candidate"]
```

Conformal scores и support thresholds обучаются только на group-aware training OOF. Решение класса требует согласования вероятности, conformal membership и support; отсутствие support ведёт к review, а не автоматически к атаке. Episode state изолирован по run и asset и использует только текущие/предыдущие окна.
