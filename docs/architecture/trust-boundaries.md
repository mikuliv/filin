# Границы доверия

## Поток данных

```mermaid
flowchart LR
    A["Контролируемая capture-среда"] -->|"PCAP/Zeek"| B["Feature boundary"]
    B -->|"versioned vector"| C["Frozen candidate"]
    C -->|"shadow_event_v2"| D["Staging boundary"]
    D -->|"validated event"| E["Reconstruction boundary"]
    E -->|"card bundle"| F["Console read-only boundary"]
    F -->|"manual overlay"| G["Runtime SQLite"]
```

## Правила

- каждый переход валидирует schema version и identity anchors;
- неизвестный candidate, contract или schema отклоняется;
- source подтверждающие материалы не доверяет operator изменяемый слой;
- console token не превращает localhost в публичную службу;
- среда выполнения database не включается во Зафиксировано комплект автоматически;
- внешняя сторона получает только согласованный package область применимости.

## Не являющиеся доверием признаки

Label интерфейса, имя гипотезы, позиция на временная последовательность и графическое соседство не
создают доказательную силу. Она определяется только источниками, контрактами и
зафиксированными assessment rules.
