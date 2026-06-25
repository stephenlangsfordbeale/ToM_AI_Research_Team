# Campaign Index

Canonical map of demo-relevant and active experiment campaigns.  
**Folder names in `logs/` and historical `modal/` roots are legacy** — use this table to find meaning.

## Status legend

| Status | Meaning |
|--------|---------|
| **canonical** | Default demo / promotion evidence |
| **active** | Current working lane, not necessarily promoted |
| **archived** | Preserved; under `archive/modal/` or legacy `logs/` names |
| **exploratory** | Useful for comparison; not the main story |

## Local gate campaigns

| campaign_id | family | platform | gate | seeds | status | artifact root | summary |
|-------------|--------|----------|------|-------|--------|---------------|---------|
| `local-omx-full-2-promo` | auxhead-clear | local | promo | 7,11,17,23,29 | **canonical** | `logs/omx_full_2_seed{N}/` | `logs/omx_full_2_5seed_summary.md` |
| local-omx-full-1-promo | auxhead-clear | local | promo | 17,23 | archived | `logs/omx_full_1_seed*/` | `logs/omx_full_1_3seed_summary.md` |
| local-omx-quick-1 | auxhead-clear | local | quick | 7,11,17 | exploratory | `logs/omx_quick_1_seed*/` | `logs/omx_quick_1_summary.md` |

**Results Mode default:** `local-omx-full-2-promo` summary + `incumbents/ToM_experiment_incumbent/auxhead-clear/INCUMBENT_NOTE.md`

## Modal synced logs (`logs/modal/`)

| campaign_id | family | platform | gate | status | artifact root |
|-------------|--------|----------|------|--------|---------------|
| modal-auxhead-clear-20260416 | auxhead-clear | modal | longrun | active | `logs/modal/auxhead-clear-20260416/` |
| modal-auxhead-clear-rebus-20260621 | auxhead-clear | modal | longrun | exploratory | `logs/modal/auxhead-clear-rebus-20260621/` |
| modal-auxhead-clear-rebus-explicit-resolution | auxhead-clear | modal | longrun | exploratory | `logs/modal/auxhead-clear-rebus-explicit-resolution-20260621/` |
| modal-auxhead-clear-rebus-reflective | auxhead-clear | modal | longrun | exploratory | `logs/modal/auxhead-clear-rebus-reflective-20260621/` |
| modal-auxhead-clear-rebus-reflective-hybrid-explicit-mask | auxhead-clear | modal | longrun | exploratory | `logs/modal/auxhead-clear-rebus-reflective-hybrid-explicit-mask-20260621/` |
| modal-auxhead-clear-rebus-reflective-hybrid-repair-mask | auxhead-clear | modal | longrun | exploratory | `logs/modal/auxhead-clear-rebus-reflective-hybrid-repair-mask-20260621/` |
| modal-auxhead-clear-rebus-reflective-post-error-alpha-only | auxhead-clear | modal | longrun | exploratory | `logs/modal/auxhead-clear-rebus-reflective-post-error-alpha-only-20260621/` |

## Modal warm-starts (`modal/tom-experiment-incumbent/`)

| campaign_id | family | platform | role | status | artifact root |
|-------------|--------|----------|------|--------|---------------|
| modal-warmstart-auxhead-clear | auxhead-clear | modal | warm-start | **canonical** | `modal/tom-experiment-incumbent/auxhead-clear/` |
| modal-warmstart-auxhead-lite | auxhead-lite | modal | warm-start | active | `modal/tom-experiment-incumbent/auxhead-lite/` |

Benchmark-side mirror: `incumbents/ToM_experiment_incumbent/auxhead-clear/`

## Benchmark incumbent snapshots (`incumbents/`)

| campaign_id | family | status | artifact root | notes |
|-------------|--------|--------|---------------|-------|
| incumbent-auxhead-clear | auxhead-clear | **canonical** | `incumbents/ToM_experiment_incumbent/auxhead-clear/` | local 5-seed gate + `train.py` |
| incumbent-v6-omx-full2 | contextual_right_of_way_switch | active | `incumbents/ToM_experiment_incumbent_v6-omx-full2/` | promoted train snapshot + results table |
| incumbent-v6-baseline-f1zero | baseline warm-start lane | active | `incumbents/ToM_experiment_incumbent_v6-baseline-f1zero/` | baseline→130k continuation experiment |

Modal seed packages for v6 lanes remain under `archive/modal/tom-experiment-incumbent/v6-*/seed*/`.

## Archived Modal long-runs (`archive/modal/`)

| campaign_id | family | platform | target eps | status | artifact root |
|-------------|--------|----------|------------|--------|---------------|
| modal-v2-140k | contextual_right_of_way_switch (v2) | modal | 140k | archived | `archive/modal/tom-140k-modal-results-v2/` |
| modal-v2b-140k | v2 duplicate | modal | 140k | archived | `archive/modal/tom-140k-modal-results-v2b/` |
| modal-v5dt-140k | delayedtrust-split | modal | 140k | archived | `archive/modal/tom-140k-modal-results-v5dt/` |
| modal-v6-140k | omx-full2 promo | modal | 140k | archived | `archive/modal/tom-140k-modal-results-v6/` |
| modal-v6-ab130-f1zero | baseline f1zero | modal | 130k | archived | `archive/modal/tom-130000-modal-results-v6-baseline-f1zero/` |

Reports: `archive/modal/tom-140k-modal-results-v2/reports/` (when generated)

## Naming rules (new work only)

Do not add new flat names at `logs/` root. Use:

```
logs/local/<family>/<gate>/<campaign-slug>/seed<N>/     # local runner outputs
logs/modal/<family>/<campaign-slug>/                     # synced Modal logs
logs/summaries/<campaign-id>.md                          # gate summaries
```

Dimensions (separate, never combined into one opaque token):

1. **platform** — `local` | `modal`
2. **family** — e.g. `auxhead-clear`
3. **gate** — `smoke` | `quick` | `promo` | `longrun`
4. **campaign** — dated slug (`2026-06-rebus-reflective`)
5. **seed** — leaf folder when per-seed artifacts exist

## CLI pointers

| Mode | Points at |
|------|-----------|
| Results Mode (`tom-demo`) | `local-omx-full-2-promo` summary + incumbent note |
| Results Mode + `--modal` | Lists `logs/modal/` campaigns from this index |
| Test Mode (`tom-test`) | New runs under `logs/local/...` (schema TBD) |
| Modal status (menu 8) | Live Modal volume via `tom-modal-status` |
