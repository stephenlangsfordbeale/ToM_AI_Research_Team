# Check3 Consistency Note
Compared with `check2`, `check3` is directionally consistent but weaker overall.
Branch mean `ToMCoordScore` fell from `0.4425` to `0.3712`, with `SuccessRate` falling from `0.625` to `0.575`.
The main regression is `seed11`, where `DeadlockRate` rose from `0.10` to `0.35` and `assert_or_yield` worsened to `4` deadlocks.
Keep `check2` as the stronger branch and treat `check3` as evidence that the line is real but still variance-sensitive.
