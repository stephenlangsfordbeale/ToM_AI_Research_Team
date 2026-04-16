Promoted from OMX train.py-only pass.
Benchmark: Variant 1 frozen ambiguous bottleneck
Reason: - deadlock not worsened (0.1 vs baseline 0.1)
        - higher ToMCoordScore
        - lower collision
        - higher success
        - much better ambiguity/intention metrics
Patch: One logical change to the post-evidence decision prior in ToMPolicy._apply_decision_prior:
        - tightened late_yield in non-narrow contexts so it only prefers yielding when the partner is actually pressing
        - added a soft_reengage path to bias PROCEED/PROBE over WAIT/YIELD when evidence is out, margin is not narrow, the partner stays soft, and belief is no longer strongly assertive
