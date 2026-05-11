# Adaptive Routing and Learning

Purpose
- Route tasks to the right model depth
- Improve quality weekly through measured feedback

## Routing Matrix

| Route | Use When | Preferred Model | Reasoning |
|------|----------|-----------------|-----------|
| Fast | direct answer and routine operation | default model | off |
| Think | analysis and structured planning | analysis-tier model | on |
| Deep | long-context synthesis and publication-grade output | long-context model | off |
| Strategic | architecture and high-impact tradeoff decisions | strategic-tier model | on |

## Escalation Signals
- quality is shallow
- source conflict or high uncertainty
- multi-step tradeoff reasoning is required
- first draft is not publish-ready

## Weekly Metrics Source
`memory/learning-metrics.json`

## Visual Flow

```mermaid
flowchart TD
    A[New task] --> B{Complexity}
    B -->|Fast| R1[Default model\nReasoning off]
    B -->|Think| R2[Analysis-tier model\nReasoning on]
    B -->|Deep| R3[Long-context model\nReasoning off]
    B -->|Strategic| R4[Strategic-tier model\nReasoning on]

    R1 --> O[Output]
    R2 --> O
    R3 --> O
    R4 --> O

    O --> E{Feedback}
    E -->|Error| L1[Log ERRORS]
    E -->|Correction| L2[Log LEARNINGS]
    E -->|Missing capability| L3[Log FEATURE_REQUESTS]

    L1 --> W[Weekly review]
    L2 --> W
    L3 --> W

    W --> M[Update learning-metrics.json]
    W --> P[Promote one high-impact rule]
    P --> B
```
