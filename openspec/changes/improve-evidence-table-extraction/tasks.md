## 1. Extraction Rules

- [x] 1.1 Expand experiment-section detection to include dataset, benchmark, metric, empirical, and result-oriented headings.
- [x] 1.2 Add deterministic dataset extraction beyond the current allowlist, including benchmark-style names and dataset phrasing.
- [x] 1.3 Add deterministic metric extraction beyond the current allowlist, including acronym metrics and metric variants.

## 2. Evidence Table Output

- [x] 2.1 Generate compact Evidence Table rows with concrete support snippets.
- [x] 2.2 Preserve partial-evidence behavior when only metrics or only datasets are detected.

## 3. Verification And Documentation

- [x] 3.1 Add a smoke scenario covering non-allowlist datasets and metrics.
- [x] 3.2 Run local `uv run` checks for the evidence extraction scenario.
- [x] 3.3 Update completion documentation for the implemented change.
