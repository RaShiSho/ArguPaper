## ADDED Requirements

### Requirement: Extract Experiment Evidence Fields
The system SHALL extract experiment evidence fields from Markdown experiment-related sections using deterministic local rules.

#### Scenario: Domain dataset and metric are present
- **WHEN** the Markdown contains an experiment or evaluation section that mentions a dataset such as GSM8K, HumanEval, MMLU, PubMedQA, or a similar benchmark-style name and a metric such as EM, mAP, AUROC, MAE, NDCG, or ROUGE-L
- **THEN** the evidence result SHALL include the dataset and metric names without requiring them to be present in a tiny fixed allowlist

#### Scenario: No experiment section exists
- **WHEN** the Markdown has no experiment-related section
- **THEN** extraction SHALL fall back to the full Markdown and retain explicit weakness messages when datasets or metrics cannot be found

### Requirement: Render Informative Evidence Table Rows
The system SHALL produce Evidence Table rows with dataset, metric, and support text when experiment evidence is detected.

#### Scenario: Dataset and metric evidence is detected
- **WHEN** datasets and metrics are extracted from experiment text
- **THEN** each Evidence Table row SHALL contain a concrete dataset, metric, and support snippet rather than a generic placeholder

#### Scenario: Partial evidence is detected
- **WHEN** metrics are detected but no dataset is confidently detected
- **THEN** the Evidence Table SHALL still include a row with dataset marked as `Not specified` and support text explaining the partial evidence
