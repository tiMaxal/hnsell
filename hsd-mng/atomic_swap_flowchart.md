# Atomic Swap Activity Flow

## Visual Text Flow

```text
[HSD Export (Live API)]
        |
        v
[hsd-mng.py -> hns_bob_tlds.csv]
        |
        v
[Update Truth (Live API or CSV)]
        |
        v
[Truth CSV: ownership + pricing + swap schema columns]
        |
        +------------------------------+
        |                              |
        v                              v
[Export for PageMaker]           [Swap setup by seller]
        |                              |
        v                              v
[pagemaker CSV with          [build lock script + lock tx]
 proof/disclosure fields]               |
        |                              v
        v                      [generate presigned proof]
[Generate Portfolio HTML]               |
        |                               v
        |                     [persist proof hash (+ proof store)]
        |                               |
        +---------------+---------------+
                        |
                        v
        [Buyer opens page and clicks fill]
                        |
                        v
      [Begin Fill UI requires explicit acknowledgements]
                        |
                        v
         [Fill intent JSON copied from browser]
                        |
                        v
[fill_endpoint.py POST /fill-intent]
   - verify proof hash against truth/proof store
   - verify required acknowledgements
   - execute SwapService.fill_swap
   - set truth.swap_state=filled_pending_maturity
   - persist fill_tx (+ buyer details)
                        |
                        v
         [Auto-finalize worker (HSD Manager)]
   - scans truth for filled_pending_maturity
   - resolves chain height (manual or live API)
   - calls SwapService.finalize_swap(actor=service)
   - submits sendfinalize (unless dry run)
   - updates truth.finalize_tx and swap_state=finalized
                        |
                        v
              [Domain transfer complete]
                        |
                        v
             [Re-export PageMaker / refresh page]
```

## Mermaid Equivalent

```mermaid
flowchart TD
    A[HSD Export Live API] --> B[hsd-mng.py writes hns_bob_tlds.csv]
    B --> C[Update Truth from API or CSV]
    C --> D[Truth CSV with swap schema]

    D --> E[Export for PageMaker]
    E --> F[PageMaker CSV with proof and disclosure fields]
    F --> G[Generate Portfolio HTML]

    D --> H[Seller swap setup]
    H --> I[Build lock script and lock tx]
    I --> J[Generate presigned proof]
    J --> K[Store proof hash and proof blob]

    G --> L[Buyer clicks fill on page]
    K --> L

    L --> M[Begin Fill requires explicit acknowledgements]
    M --> N[Fill intent JSON]

    N --> O[fill_endpoint POST fill-intent]
    O --> O1[Verify proof hash against truth and proof store]
    O1 --> O2[Verify required acknowledgements]
    O2 --> O3[Run SwapService.fill_swap]
    O3 --> O4[Set truth state to filled_pending_maturity and fill_tx]

    O4 --> P[Auto-finalize worker in HSD Manager]
    P --> P1[Resolve chain height manual or live]
    P1 --> P2[Run SwapService.finalize_swap as service actor]
    P2 --> P3[Submit sendfinalize unless dry run]
    P3 --> P4[Update truth finalize_tx and state finalized]

    P4 --> Q[Domain transfer complete]
    Q --> R[Re-export PageMaker and refresh sales page]
```
