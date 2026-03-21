# Agent Roles: Gap Mapping System

## 1. The Scraper Agent (Module: `scrapers/`)
**Objective**: Extract raw numeric signals from Semantic Scholar, Lens.org, Stack Overflow, and GitHub.
**Responsibilities**:
* Execute precise queries using the string formats: `"[Core]" AND "[Secondary]"` for research and `"[Core]" "[Secondary]"` for patents.
* Navigate and parse search result counts for specific date ranges (2023–2025).
* **Output**: Produce a temporary `raw_signals_[TIMESTAMP].json` for the Analysis Agent.

## 2. The Data Architect Agent (Module: `processor/`)
**Objective**: Clean raw signals and format them into the finalized CSV structure.
**Responsibilities**:
* Calculate derived metrics: YoY Growth Rates and Citation Intensity averages.
* Ensure the output file strictly follows the `Market Research Excel Template.csv` headers.
* **Output**: Generate a timestamped CSV file (e.g., `research_gap_data_20250321_1430.csv`).

## 3. The Visualization Agent (Module: `visualizer/`)
**Objective**: Transform the processed CSV into the "Need vs Research Opportunity Map."
**Responsibilities**:
* Load the timestamped CSV and execute `plot.py` logic.
* [cite_start]Compute Z-scores ($RG$ and $TG$) to determine bubble color (Gap Severity) and size (Opportunity)[cite: 142, 145].
* **Output**: Save the plot as a PNG/PDF with a matching timestamp.

## 4. The Orchestrator (Main CLI Entry)
**Objective**: Sequence the modular pipeline.
**Responsibilities**:
* Accept a list of subfields (e.g., from a `targets.txt`).
* Trigger Scraper -> Data Architect -> Visualization in sequence.
* Log errors per subfield to ensure the pipeline doesn't crash on one failed scrape.