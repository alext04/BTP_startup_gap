# Gap Mapping System

A modular pipeline for mapping research gaps and innovation opportunities across scientific subfields.

## Overview

This system automates the collection and analysis of research metrics from multiple data sources to generate a **"Need vs Research Opportunity Map"** - a visualization that helps identify underserved research areas with high commercial potential.

## Architecture

The system follows a modular agent-based architecture:

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Scraper Agent  │────▶│ Data Architect   │────▶│ Visualization   │
│                 │     │                  │     │ Agent           │
│ - Semantic Sch. │     │ - Clean data     │     │ - Compute Z-scores│
│ - Lens.org      │     │ - Format CSV     │     │ - Generate plot │
│ - Stack Overflow│     │ - Validate       │     │ - Save PNG/PDF  │
│ - GitHub        │     │                  │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

## Installation

1. **Install dependencies:**
   ```bash
   cd BTP_startup_gap
   pip install -r requirements.txt
   ```

2. **Optional: Set up API keys for higher rate limits:**
   - Semantic Scholar API key: https://www.semanticscholar.org/product/api
   - GitHub personal access token: https://github.com/settings/tokens

## Configuration

### targets.json

Define the subfields you want to analyze in `targets.json`:

```json
{
  "subfields": [
    {
      "name": "Solid-State Batteries",
      "core_term": "solid-state battery",
      "secondary_term": "energy storage"
    },
    {
      "name": "Metal-Organic Frameworks",
      "core_term": "metal-organic framework",
      "secondary_term": "porous material"
    }
  ]
}
```

**Note:** You can add any number of subfields - there's no limit.

## Usage

### Full Pipeline (Recommended)

Run the complete pipeline (scrape → process → visualize):

```bash
python main.py -t targets.json --output ./results
```

### Individual Steps

**Step 1: Scrape only**
```bash
python agents/scraper.py -t targets.json -o ./results
```

**Step 2: Process raw signals**
```bash
python processor/data_architect.py -i raw_signals_20250321_1430.json -o ./results
```

**Step 3: Generate visualization**
```bash
python visualizer/plot_engine.py -i research_gap_data_20250321_1430.csv -o ./results
```

### Advanced Options

```bash
# Skip scraping (use existing raw signals)
python main.py -t targets.json --skip-scrape --raw-signals raw_signals_20250321_1430.json

# Skip visualization (CSV only)
python main.py -t targets.json --skip-visualize

# Use API keys for better rate limits
python main.py -t targets.json --semantic-scholar-key YOUR_KEY --github-token YOUR_TOKEN

# Custom output and log directories
python main.py -t targets.json --output ./my_results --logs ./my_logs
```

## Output Files

The pipeline generates the following files:

| File | Description |
|------|-------------|
| `raw_signals_[timestamp].json` | Raw scraped data from all sources |
| `research_gap_data_[timestamp].csv` | Processed data in template format |
| `[subfield]_[timestamp].csv` | Individual subfield CSV files |
| `research_gap_data_[timestamp]_visualization.png` | Need vs Research Opportunity Map |
| `logs/orchestrator_[timestamp].log` | Pipeline execution logs |
| `logs/processor_[timestamp].log` | Data processing logs |
| `logs/visualizer_[timestamp].log` | Visualization metrics logs |

## CSV Schema

The output CSV follows this exact schema:

| Column | Description |
|--------|-------------|
| Subfield | Name of the research subfield |
| Paper Count (3yr) | Total papers 2023-2025 |
| Citation Intensity (3yr avg) | Mean citations of top 10 papers |
| Paper Growth Rate (YoY %) | 2025 vs 2024 growth |
| Patent Count (3yr) | Total patents 2023-2025 |
| NPL Citation Rate (3yr %) | Non-patent literature citation rate |
| Corporate Patent Share (3yr %) | For-profit company patent share |
| SO Question Vol (12mo) | Stack Overflow questions (last 12mo) |
| SO Question Growth (12mo %) | YoY question growth |
| GitHub Repo Count (3Y) | Repos created 2023-2025 |
| GitHub Star Growth (12mo %) | Star growth rate |

## Visualization

The "Need vs Research Opportunity Map" uses:

- **X-axis**: Need Score (demand proxy from market data)
- **Y-axis**: Research Intensity (log-scaled)
- **Bubble Size**: Opportunity (Translation Gap)
- **Bubble Color**: Gap Severity
  - 🔴 Red = Under-commercialized (high gap)
  - 🟢 Green = Mature (low gap)

### Quadrants

| Quadrant | Description |
|----------|-------------|
| High Need, High Research | Active, mature research areas |
| Low Need, High Research | Over-researched, low demand |
| High Need, Low Research | **Opportunity zones** - underserved |
| Low Need, Low Research | Low priority areas |

## Data Sources

| Source | Metrics | API |
|--------|---------|-----|
| Semantic Scholar | Paper counts, citations, growth | https://api.semanticscholar.org |
| Lens.org | Patent counts, NPL rates, corporate share | https://api.lens.org |
| Stack Overflow | Question volume, growth | https://api.stackexchange.com |
| GitHub | Repo counts, star growth | https://api.github.com |

## Error Handling

The pipeline is designed for resilience:

- Failed scrapes record "N/A" for affected columns
- Individual subfield failures don't stop the pipeline
- All errors are logged to the `logs/` directory

## Troubleshooting

### Rate Limiting

If you encounter rate limiting errors:

1. Get API keys for Semantic Scholar and GitHub
2. Increase delays between requests in scraper configurations
3. Run the pipeline during off-peak hours

### Missing Data

If certain metrics show "N/A":

- Check the logs for specific error messages
- Some sources may block automated requests
- Try running with a VPN or different IP

## License

This project is part of the BTP (Bachelor Thesis Project) for research gap analysis.

## Contributing

To add new data sources:

1. Create a new scraper module in `scrapers/`
2. Implement the standard interface (`scrape()` method)
3. Update `agents/scraper.py` to include the new source
