# Workflow and operating logic

```mermaid
flowchart TD
 A[Settled invoice detected] --> B[Load renewal form and booking request]
 B --> C[Match student to active reference]
 C --> D{All deterministic checks pass?}
 D -- Yes --> E[Same-batch candidate]
 E --> F[Final capacity and duplicate check]
 F --> G[Schedule-ready output]
 D -- No --> H[Reason-coded exception]
 H --> I[Assign teacher / Ops / Finance / Scheduling]
 I --> J[Correct evidence and rerun]
 G --> K[Human-controlled production write]
```

## Guardrails
1. Payment status is checked from the authoritative source.
2. A student match must be unique.
3. Same-batch continuation is the only proposed automatic path in this prototype.
4. Batch changes and ambiguous data are held.
5. Existing schedule records are reviewed to avoid duplicates.
6. No live schedule writes are performed by this repository.
