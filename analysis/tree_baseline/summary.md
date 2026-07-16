# Decision-tree acceptability baseline (per-argument task)

Pool: 500 AAFs, 3000 argument rows, grouped 5-fold CV. Tree = CART (max_depth 6). Metric MCC (mean over folds). Noise q flips training labels; test on clean oracle.

| target | base rate | model | q=0 MCC | q=0.1 MCC | q=0.2 MCC | (q=0 acc) |
|---|---|---|---|---|---|---|
| cred_STB | 0.5003 | tree | 0.548 | 0.527 | 0.544 | 0.770 |
|  |  | tree_deep | 0.684 | 0.609 | 0.546 | 0.841 |
|  |  | rf | 0.721 | 0.714 | 0.665 | 0.860 |
|  |  | logreg | 0.660 | 0.669 | 0.653 | 0.828 |
|  |  | majority | 0.000 | 0.000 | 0.000 | 0.473 |
| skep_STB | 0.1766 | tree | 0.652 | 0.577 | 0.548 | 0.883 |
|  |  | tree_deep | 0.626 | 0.455 | 0.443 | 0.869 |
|  |  | rf | 0.670 | 0.611 | 0.542 | 0.892 |
|  |  | logreg | 0.655 | 0.622 | 0.592 | 0.877 |
|  |  | majority | 0.000 | 0.000 | 0.000 | 0.823 |
| cred_ADMfam | 0.5013 | tree | 0.551 | 0.533 | 0.542 | 0.771 |
|  |  | tree_deep | 0.689 | 0.615 | 0.544 | 0.843 |
|  |  | rf | 0.722 | 0.708 | 0.667 | 0.860 |
|  |  | logreg | 0.663 | 0.671 | 0.661 | 0.830 |
|  |  | majority | 0.000 | 0.000 | 0.000 | 0.472 |
| skep_PRF | 0.17 | tree | 0.650 | 0.542 | 0.528 | 0.882 |
|  |  | tree_deep | 0.592 | 0.465 | 0.405 | 0.859 |
|  |  | rf | 0.665 | 0.607 | 0.505 | 0.892 |
|  |  | logreg | 0.654 | 0.625 | 0.602 | 0.880 |
|  |  | majority | 0.000 | 0.000 | 0.000 | 0.830 |
| skep_CMP | 0.115 | tree | 0.815 | 0.715 | 0.654 | 0.952 |
|  |  | tree_deep | 0.857 | 0.509 | 0.451 | 0.967 |
|  |  | rf | 0.832 | 0.664 | 0.545 | 0.959 |
|  |  | logreg | 0.826 | 0.785 | 0.757 | 0.956 |
|  |  | majority | 0.000 | 0.000 | 0.000 | 0.885 |

_Best feature learner per target (q=0 MCC): cred_STB rf=0.721; skep_STB rf=0.670; cred_ADMfam rf=0.722; skep_PRF rf=0.665; skep_CMP tree_deep=0.857._

## Interpretation
- The tree solves per-argument credulous/skeptical acceptance (the AGNN task), NOT the labelling-level extension-membership task LAS solves; it cannot represent the set of extensions.
- LAS recovers the exact semantics on clean data (Thm 1 + the recovery surface), so its argument-level acceptance is ~1.0 by construction — the gap to the tree's MCC is the baseline's cost.
