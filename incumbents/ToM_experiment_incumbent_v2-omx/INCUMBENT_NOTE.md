# Contextual-Right-Of-Way OMX Incumbent Note

This archive stores the narrower OMX-era `contextual_right_of_way_switch`
family that cleared the local 5-seed `800`-episode promotion gate on Variant 1
frozen ambiguous bottleneck.

Primary packaged promotion evidence:

- `/Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/omx_full_2_seed7`
- `/Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/omx_full_2_seed11`
- `/Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/omx_full_2_seed17`
- `/Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/omx_full_2_seed23`
- `/Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/omx_full_2_seed29`
- `/Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/omx_full_2_5seed_summary.md`

Equivalent packaged copies also exist under:

- `/Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/omx_promo_1_seed7`
- `/Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/omx_promo_1_seed11`
- `/Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/omx_promo_1_seed17`
- `/Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/omx_promo_1_seed23`
- `/Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/omx_promo_1_seed29`

## Gate Result

All five promotion seeds selected `keep` with:

- `ToMCoordScore`: `0.1109 -> 0.2265`
- `DeadlockRate`: `0.1000 -> 0.1000`
- `CollisionRate`: `0.3400 -> 0.2900`
- `SuccessRate`: `0.5600 -> 0.6100`
- `AmbiguityEfficiency`: `0.0900 -> 0.1433`
- `IntentionPredictionF1`: `0.0000 -> 0.4148`
- `StrategySwitchAccuracy`: `0.5000 -> 0.5200`

This is the archived local OMX family that cleared the 5-seed gate. It should
be kept separate from:

- `auxhead-lite`, which is an older archived incumbent line
- `auxhead-lite-v2-local800`, which is a 2-seed warm-start archive for seeds 7
  and 11 only
- later delayed-trust variants such as
  `ToM experiment incumbent v5-delayedtrust-split-candidate`

## Train Snapshot Provenance

The `train.py` stored here is copied from the archived OMX incumbent snapshot:

- `/Users/stephenbeale/Projects/ToM_AI_Research_Team/incumbents/ToM experiment incumbent v3-omx/train.py`

That snapshot preserves the narrower OMX-era policy family and intentionally
excludes later delayed-trust additions in the current repo `train.py`.
