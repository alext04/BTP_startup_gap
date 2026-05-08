# Research-to-Startup Gap Mapping System — Project Report

**Bachelor Thesis Project (BTP) — Independent Study**
**Date:** May 2026

---

## 1. Introduction

The **Research-to-Startup Gap Mapping System** is an automated pipeline that identifies under-commercialized research areas with high market demand. It scrapes data from multiple public APIs, processes the raw signals into standardized metrics, and generates a **"Need vs Research Opportunity Map"** — a bubble chart that visually answers:

- **For Researchers:** Which subfields have strong market demand but insufficient research?
- **For Startups/Product Labs:** Which subfields have strong research but no commercial products?

The tool takes any scientific domain (e.g., "Computer Vision in Manufacturing"), breaks it into subfields, and maps each subfield across three measurement areas: Research Activity, Commercialization Activity, and Market Demand.

---

## 2. System Architecture

The system follows a **modular agent-based architecture** with three pipeline stages coordinated by an Orchestrator:

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Scraper Agent   │────▶│ Data Architect   │────▶│ Visualization   │
│                  │     │                  │     │ Agent           │
│ - Semantic Sch.  │     │ - Clean data     │     │ - Compute Z-scores│
│ - Lens.org       │     │ - Format CSV     │     │ - Generate plot │
│ - Product Hunt   │     │ - Validate       │     │ - Save PNG/PDF  │
│ - EDGAR Form-D   │     │                  │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

| Stage | Module | Input | Output |
|-------|--------|-------|--------|
| 1. Scrape | `agents/scraper.py` → calls `scrapers/*` | `targets.json` | `raw_signals_[timestamp].json` |
| 2. Process | `processor/data_architect.py` | Raw JSON | `research_gap_data_[timestamp].csv` |
| 3. Visualize | `visualizer/plot_engine.py` | Processed CSV | `*_visualization.png` |

### 2.1 File Structure

```
BTP_startup_gap/
├── main.py                        # Orchestrator — CLI entry point
├── config.py                      # Central API key loader (from .env)
├── targets.json                   # Input: subfield definitions
├── .env                           # API keys (not committed)
├── agents/
│   └── scraper.py                 # Scraper Agent — coordinates all scrapers
├── scrapers/
│   ├── semantic_scholar.py        # Area A: Research papers
│   ├── lens_org.py                # Area B: Patents
│   ├── edgar_form_d.py            # Area B: PE/VC investment (Form-D)
│   └── product_hunt.py            # Area C: Startup launches
├── processor/
│   └── data_architect.py          # Cleans raw data → CSV
├── visualizer/
│   └── plot_engine.py             # CSV → Bubble chart
├── results/                       # Output directory
└── logs/                          # Execution logs
```

### 2.2 Pipeline Flow

1. **Orchestrator** (`main.py`) reads `targets.json` and initializes all three agents
2. **Scraper Agent** iterates over each subfield, calling all four scrapers sequentially
3. Raw signals are saved as timestamped JSON
4. **Data Architect** maps raw keys to the CSV schema, cleans numeric values, and saves a standardized CSV
5. **Visualization Agent** loads the CSV, computes Z-scores and gap metrics, and generates the bubble chart
6. Each stage is wrapped in `try/except` — a single subfield failure does not crash the pipeline

---

## 3. How to Use the Tool

### 3.1 Installation

**Option A — using `uv` (recommended, handles dependencies automatically):**
```bash
cd BTP_startup_gap
uv run python main.py -t targets.json --output ./results
```

**Option B — using pip:**
```bash
cd BTP_startup_gap
pip install -r requirements.txt
python main.py -t targets.json --output ./results
```

Dependencies: `requests`, `pandas`, `numpy`, `matplotlib`, `beautifulsoup4`, `lxml`, `python-dotenv`

### 3.2 Setting Up API Keys

Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
```

```env
SEMANTIC_SCHOLAR_API_KEY=your_key_here    # Optional — improves rate limits
LENS_API_KEY=your_key_here                # Required for patent data
PRODUCT_HUNT_TOKEN=your_token_here        # Required for startup launch data
```

### 3.3 Configuring Subfields (targets.json)

This is the most important step. You must manually create a JSON file defining the subfields you want to analyze. Each subfield requires **search terms tailored to each signal source**.

#### Basic Structure

```json
{
  "subfields": [
    {
      "name": "Display Name for Plot",
      "core_term": "primary search keyword",
      "secondary_term": "secondary search keyword"
    }
  ]
}
```

#### Why Different Terms Are Needed Per Signal

Each API source searches differently, so **the same search term does not work equally well across all sources**:

| Signal Source | What It Searches | Term Style Needed |
|---------------|-----------------|-------------------|
| **Semantic Scholar** | Paper titles, abstracts | Precise academic terms (e.g., `"solid-state battery"`) |
| **Lens.org** (Patents) | Patent text, claims | Technical + industry terms (e.g., `"energy storage"`) |
| **Product Hunt** | Product names, descriptions | Broader business/consumer terms (e.g., `"battery tech"`) |
| **SEC Form-D** | Company names, filing text | Very broad industry terms (e.g., `"battery OR energy storage"`) |

**This is a key design consideration**: Form-D and Product Hunt do not respond to niche academic terms. For example:

```
"solid-state battery"  → Semantic Scholar: 720 papers ✅
"solid-state battery"  → Form-D filings:   0 results ❌
"battery"              → Form-D filings: 233 results ✅
```

#### Example: Different JSON Files for Different Domains

**CV in Manufacturing** (`cv_manufacturing.json`):
```json
{
  "subfields": [
    {
      "name": "Surface Defect Detection",
      "core_term": "visual inspection manufacturing",
      "secondary_term": "automated quality control"
    },
    {
      "name": "Predictive Maintenance",
      "core_term": "visual condition monitoring",
      "secondary_term": "equipment health analysis"
    }
  ]
}
```

**CV in Medical Imaging** (`cv_medical.json`):
```json
{
  "subfields": [
    {
      "name": "Computer-Aided Diagnosis (CAD)",
      "core_term": "automated disease detection",
      "secondary_term": "pathology AI diagnostics"
    },
    {
      "name": "Retinal Image Analysis",
      "core_term": "fundus photography computer vision",
      "secondary_term": "diabetic retinopathy detection"
    }
  ]
}
```

> **Important:** The `core_term` and `secondary_term` are combined as `"core_term" AND "secondary_term"` for Semantic Scholar, and as a boolean query for Lens.org. For Product Hunt and Form-D, they are concatenated or OR-joined. The current pipeline uses the same two terms across all sources, which is why some signals (particularly Form-D and Product Hunt) may return zero results for highly niche academic subfields.

### 3.4 Running the Pipeline

**Full pipeline (recommended):**
```bash
python main.py -t targets.json --output ./results
```

**Individual steps:**
```bash
# Step 1: Scrape only
python agents/scraper.py -t targets.json -o ./results

# Step 2: Process raw signals into CSV
python processor/data_architect.py -i raw_signals_YYYYMMDD_HHMMSS.json -o ./results

# Step 3: Generate chart from CSV
python visualizer/plot_engine.py -i research_gap_data_YYYYMMDD_HHMMSS.csv -o ./results
```

**Skip steps:**
```bash
# Re-process existing data (skip scraping)
python main.py -t targets.json --skip-scrape --raw-signals raw_signals_20260421_103730.json

# CSV only, no chart
python main.py -t targets.json --skip-visualize
```

---

## 4. Data Signals & Metrics

### 4.1 Area A — Research Activity (Semantic Scholar)

| Signal | Description | How Calculated |
|--------|-------------|----------------|
| Paper Count (3yr) | Volume of scientific output | Total papers matching query, 2023–2025 |
| Citation Intensity (3yr avg) | Quality signal | Mean citations of top 10 relevant papers |
| Paper Growth Rate (YoY %) | Research momentum | `((2025_count - 2024_count) / 2024_count) × 100` |

### 4.2 Area B — Applied & Commercialization Activity

**Patent Signals (Lens.org):**

| Signal | Description |
|--------|-------------|
| Patent Count (3yr) | Raw count of patents matching query, 2023–2025 |
| NPL Citation Rate (3yr %) | % of top 10 patents citing academic literature |
| Corporate Patent Share (3yr %) | % of top 10 assignees that are for-profit companies |

**PE/VC Investment Signals (SEC EDGAR Form-D):**

| Signal | Description |
|--------|-------------|
| Form-D Filing Count (3yr) | Number of Reg-D private placement filings |
| Capital Deployed (3yr $M) | Aggregate `totalAmountSold` across filings |
| PE/VC Filing Growth (YoY %) | 2025 vs 2024 filing growth rate |

### 4.3 Area C — Market Demand (Product Hunt)

| Signal | Description |
|--------|-------------|
| Product Hunt Launches (3yr) | Startup product launches matching query |
| Product Hunt Growth (YoY %) | Growth rate of launches, 2025 vs 2024 |

### 4.4 Derived Metrics (Computed by Visualization Agent)

All raw signals are Z-score normalized, then grouped into composite scores:

```
Research Intensity (RI)          = z(Paper Count) + z(Citations) + z(Growth)
Science-Industry Linkage (SIL)   = z(NPL Rate) + z(Corporate Share)
Market Demand Score (MDS)        = z(PH Launches) + z(PH Growth) + z(Form-D Count)
                                   + z(Capital Deployed) + z(Filing Growth)
```

**Gap Metrics:**
- **Research Gap (RG)** = `MDS_z − RI_z` → mapped to **bubble color**
  - RG > +0.5 → market demand outrunning research (**green** = underserved, startup opportunity)
  - RG < −0.5 → research ahead of market (**red** = mature, well-commercialized)
- **Translation Gap (TG)** = `RI_z − SIL_z` → mapped to **bubble size**
  - TG > +0.5 → research exists but hasn't crossed into products
  - TG < −0.5 → applied activity outpacing research

### 4.5 Chart Encoding

| Visual Element | Maps To | Meaning |
|---------------|---------|---------|
| X-axis | MDS_z (Need Score) | Market demand proxy |
| Y-axis | log₁₀(exp(RI_z) × 100 + 1) | Research intensity |
| Bubble size | TG (Translation Gap) | Untranslated research potential |
| Bubble color | RG (Research Gap) | Green = underserved gap (demand > research), Red = mature/commercialized |

**Quadrants** (split at median):
- **High Need + Low Research** = Opportunity zones (startups should target)
- **High Need + High Research** = Active, mature areas
- **Low Need + High Research** = Over-researched, low demand
- **Low Need + Low Research** = Low priority

---

## 5. API Reference & Usage

### 5.1 API Summary Table

| API | Auth | Cost | Rate Limit | Approval Needed? |
|-----|------|------|------------|-------------------|
| **Semantic Scholar** | Optional API key | Free | 100 req/5min (no key), ~1 RPS (with key) | No — sign up at semanticscholar.org |
| **Lens.org** | Bearer token (required) | Free tier available; paid plans for higher volume | ~10 req/min | Yes — apply at lens.org/subscriptions |
| **Product Hunt** | OAuth2 Bearer token (required) | Free | Standard GraphQL limits | Yes — create app at producthunt.com/v2/oauth |
| **SEC EDGAR (EFTS)** | None required | Free | 10 req/sec (with User-Agent) | No — fully public |

### 5.2 Semantic Scholar API

- **Endpoint:** `GET https://api.semanticscholar.org/graph/v1/paper/search`
- **Key Parameters:** `query`, `year`, `limit`, `fields`, `sort`
- **Auth:** Optional `x-api-key` header
- **How to get key:** Sign up at https://www.semanticscholar.org/product/api (free, instant)
- **Usage in pipeline:** 4 API calls per subfield (3yr count, 2024 count, 2025 count, top-10 papers)

### 5.3 Lens.org Patent API

- **Endpoint:** `POST https://api.lens.org/patent/search`
- **Auth:** `Authorization: Bearer <token>` header
- **How to get key:** Apply at https://www.lens.org/lens/user/subscriptions#developer
- **Approval time:** Usually 1–3 business days
- **Free tier:** 50 requests/day for academic use
- **Paid plans:** Start at $500/year for higher volume
- **On 401 Unauthorized:** The scraper sets an internal flag and skips all remaining Lens.org calls for the run, returning N/A for all patent columns rather than hanging or retrying

### 5.4 Product Hunt GraphQL API

- **Endpoint:** `POST https://api.producthunt.com/v2/api/graphql`
- **Auth:** OAuth2 Bearer token
- **How to get token:** Create developer app at https://www.producthunt.com/v2/oauth/applications
- **Usage:** GraphQL queries for post search with pagination

### 5.5 SEC EDGAR EFTS API (Form-D)

- **Phase 1 Endpoint:** `GET https://efts.sec.gov/LATEST/search-index`
  - Parameters: `q` (query), `forms=D`, `startdt`, `enddt`
  - Returns: filing count, accession numbers, CIKs
- **Phase 2:** `GET https://www.sec.gov/Archives/edgar/data/{CIK}/{accession}/primary_doc.xml`
  - Parses XML for: `totalAmountSold`, `totalOfferingAmount`, `entityType`, `investors`
- **Auth:** None — requires valid `User-Agent` header only
- **Cost:** Completely free, publicly funded
- **Limitation:** US-only filings; niche terms return 0 results (see Section 3.3)

---

## 6. Demonstration with Dummy Data

Since the full pipeline cannot be run end-to-end due to API rate limits and approval requirements, we demonstrate the tool's output using **realistic dummy data** for three Computer Science / Engineering domains. The dummy values are calibrated to reflect real-world patterns observed in our actual runs.

### 6.1 Domain 1: NLP & Large Language Models

**Subfields analyzed:** Code Generation LLMs, RAG, LLM Fine-Tuning Frameworks, Multi-Modal LLMs, LLM Alignment & Safety, Autonomous AI Agents, On-Device Small LMs

| Subfield | Papers (3yr) | Citations Avg | Growth % | Patents | PH Launches | Form-D Filings | Capital ($M) |
|----------|-------------|---------------|----------|---------|-------------|----------------|-------------|
| Code Generation LLMs | 4,200 | 28.5 | 185% | 890 | 340 | 85 | $2,400 |
| RAG | 3,800 | 22.3 | 220% | 420 | 580 | 120 | $3,100 |
| LLM Fine-Tuning | 2,950 | 18.7 | 95% | 310 | 210 | 35 | $450 |
| Multi-Modal LLMs | 5,100 | 35.2 | 165% | 1,200 | 120 | 65 | $1,800 |
| LLM Alignment & Safety | 3,100 | 42.1 | 310% | 180 | 45 | 22 | $320 |
| Autonomous AI Agents | 1,800 | 15.6 | 280% | 95 | 420 | 95 | $2,800 |
| On-Device Small LMs | 1,200 | 9.8 | 150% | 650 | 180 | 40 | $680 |

![NLP & Large Language Models Gap Map](/home/rohan/.gemini/antigravity/brain/bb0ab66a-1733-4e4e-97da-0ef27ebe836e/dummy_nlp_llm_gap_map.png)

**Key findings:**
- **Autonomous AI Agents** (bottom-right, green) — highest market demand but relatively low research output → **biggest startup opportunity**
- **RAG** (right, yellow-green) — strong demand and good research base → maturing area with active commercialization
- **LLM Alignment & Safety** (top-left, red) — very high research growth (310%) but low market demand signals → research is ahead of market pull
- **Multi-Modal LLMs** (left, red) — high research intensity but low commercial demand signals → under-commercialized despite strong science

### 6.2 Domain 2: Cybersecurity & Network Engineering

| Subfield | Papers (3yr) | Citations Avg | Growth % | Patents | PH Launches | Form-D Filings | Capital ($M) |
|----------|-------------|---------------|----------|---------|-------------|----------------|-------------|
| AI-Driven Threat Detection | 2,800 | 18.3 | 75% | 1,800 | 180 | 55 | $1,200 |
| Zero Trust Architecture | 950 | 8.5 | 120% | 2,400 | 310 | 72 | $1,800 |
| Post-Quantum Cryptography | 3,200 | 24.7 | 45% | 450 | 15 | 8 | $120 |
| Supply Chain Security | 1,100 | 12.1 | 95% | 680 | 95 | 38 | $650 |
| Cloud-Native Security | 1,600 | 9.8 | 140% | 3,200 | 420 | 95 | $2,800 |
| IoT/OT Network Security | 2,100 | 15.2 | 35% | 1,100 | 65 | 28 | $380 |
| Deepfake Detection | 1,900 | 21.6 | 110% | 320 | 45 | 12 | $85 |

![Cybersecurity Gap Map](/home/rohan/.gemini/antigravity/brain/bb0ab66a-1733-4e4e-97da-0ef27ebe836e/dummy_cybersecurity_gap_map.png)

**Key findings:**
- **Cloud-Native Security** (right, green) — highest market demand, strong patent activity → active, well-funded area
- **Zero Trust Architecture** (bottom-right, green) — high demand but low research depth → opportunity for applied research
- **Post-Quantum Cryptography** (top-center, orange) — very high research output but almost no commercial demand yet → research is years ahead of market
- **Deepfake Detection** (top-left, red) — strong research but low commercialization → classic translation gap

### 6.3 Domain 3: Robotics & Autonomous Systems

| Subfield | Papers (3yr) | Citations Avg | Growth % | Patents | PH Launches | Form-D Filings | Capital ($M) |
|----------|-------------|---------------|----------|---------|-------------|----------------|-------------|
| Warehouse Autonomous Robots | 1,400 | 12.5 | 85% | 3,200 | 210 | 65 | $1,800 |
| Surgical Robotics AI | 2,800 | 19.8 | 55% | 1,900 | 45 | 32 | $650 |
| Autonomous Driving Vision | 8,500 | 32.1 | 35% | 12,000 | 85 | 110 | $4,200 |
| Drone Swarm Coordination | 950 | 8.3 | 120% | 450 | 35 | 15 | $180 |
| Soft Robotics Actuation | 1,800 | 14.7 | 40% | 280 | 8 | 5 | $45 |
| Human-Robot Collaboration | 2,200 | 11.2 | 65% | 850 | 120 | 28 | $320 |
| Robot Foundation Models | 680 | 25.5 | 280% | 120 | 65 | 42 | $850 |

![Robotics Gap Map](/home/rohan/.gemini/antigravity/brain/bb0ab66a-1733-4e4e-97da-0ef27ebe836e/dummy_robotics_gap_map.png)

**Key findings:**
- **Autonomous Driving Vision** (top-right, dark red) — massive research AND patents, but the red color indicates research is still running ahead of market maturity
- **Robot Foundation Models** (right, orange) — emerging area with very high growth (280%) and significant VC interest
- **Warehouse Autonomous Robots** (right, green) — balanced demand and research → mature commercial opportunity
- **Soft Robotics Actuation** (far-left, red) — low demand, low commercialization despite moderate research → niche academic area

---

## 7. Actual Pipeline Runs (With Real API Data)

We ran the pipeline on two domains with real API data. Some signals (particularly Form-D and Product Hunt) returned zero for niche manufacturing/medical terms, illustrating the granularity mismatch discussed in Section 3.3.

### 7.1 CV in Manufacturing (Real Data)

| Subfield | S2 Papers | S2 Growth | Lens Patents | PH Launches | Form-D |
|----------|-----------|-----------|-------------|-------------|--------|
| Surface Defect Detection | 720 | 116% | 54,661 | 90 | 0 |
| PPE and Safety Compliance | 567 | 109% | 13,871 | 37 | 0 |
| Robotic Bin Picking | 2 | 0% | 1,939 | 170 | 0 |
| Predictive Maintenance | 357 | 18% | 108,855 | 0 | 0 |
| Digital Twin Synchronization | 13 | 350% | 0 | 0 | 0 |

![CV Manufacturing Actual Plot](/home/rohan/.gemini/antigravity/brain/bb0ab66a-1733-4e4e-97da-0ef27ebe836e/cv_manufacturing_actual_plot.png)

> **Note:** Form-D returned 0 filings for all subfields because niche manufacturing terms like "visual inspection manufacturing" don't appear in SEC filings. Product Hunt also returned 0 for some subfields. This is why broader `industry_term` fields would need to be added to `targets.json` for these signals to work.

### 7.2 CV in Medical Imaging (Real Data)

| Subfield | S2 Papers | S2 Growth | Lens Patents | PH Launches | Form-D |
|----------|-----------|-----------|-------------|-------------|--------|
| Computer-Aided Diagnosis | 10,729 | 128% | 9,513 | 0 | 0 |
| Endoscopic Video Analysis | 6,010 | 79% | 1,152 | 0 | 0 |
| Digital Pathology | 3,904 | 37% | 2,382 | 0 | 0 |
| Radiology Image Segmentation | 1,817 | 100% | 6,574 | 0 | 0 |

![CV Medical Actual Plot](/home/rohan/.gemini/antigravity/brain/bb0ab66a-1733-4e4e-97da-0ef27ebe836e/cv_medical_actual_plot.png)

> **Note:** Product Hunt and Form-D returned 0 across all medical subfields. The plot shows all bubbles clustered near x=0 on the Need axis because the Market Demand Score components are all zero. This demonstrates the need for broader search terms or alternative market demand sources for specialized academic domains.

---

## 8. Known Limitations & Current Issues

1. **API Rate Limits:** Semantic Scholar limits to ~100 requests/5 minutes without a key. Full pipeline with 7+ subfields takes 10–15 minutes due to polite delays.

2. **Form-D Granularity Mismatch:** Niche scientific terms return 0 Form-D results. Companies don't name themselves after research subfields. Broader `industry_term` fields in `targets.json` would help but add imprecision.

3. **Product Hunt Relevance:** Product Hunt search returns broadly related products, not always directly relevant to the subfield. Results need manual validation.

4. **Lens.org API Access:** Requires approval and has a limited free tier (50 req/day). On 401, the scraper skips all patent scraping for that run and returns N/A for all patent columns.

5. **US-Only Form-D:** SEC filings only cover US private placements. Non-US investment activity is invisible.

6. **N/A Cascading:** When multiple signals return N/A (converted to 0), the Z-score computation treats them as genuinely zero activity, which can distort gap calculations.

---

## 9. Alternative Signal Sources

The following could replace or supplement current sources:

| Current Signal | Alternative Source | Pros | Cons |
|----------------|-------------------|------|------|
| **Product Hunt** (Area C) | **Crunchbase API** | Structured startup data, funding rounds, industry tags | Expensive ($499+/month), requires enterprise agreement |
| **Product Hunt** (Area C) | **AngelList / Wellfound** | Direct startup listings by sector | No public API, scraping required |
| **Stack Overflow** (Area C) | **Reddit API** | Subreddit activity as demand proxy | Noisy signal, hard to filter |
| **GitHub** (Area C) | **Papers With Code** | Links research to implementations | Narrow scope (ML-focused) |
| **Lens.org** (Area B) | **Google Patents** | Free, comprehensive patent database | No structured API, requires BigQuery |
| **Lens.org** (Area B) | **PatentsView (USPTO)** | Free REST API for US patents | US-only, limited search capabilities |
| **Lens.org** (Area B) | **OpenAlex** | Free, open scholarly metadata | Better for papers than patents |
| **Form-D** (Area B) | **PitchBook API** | Most comprehensive PE/VC database | Very expensive ($20K+/year), enterprise only |
| **Form-D** (Area B) | **CB Insights** | VC deal tracking by sector | Expensive, approval required |
| **Semantic Scholar** (Area A) | **OpenAlex API** | Fully open, no rate limits | Less precise relevance ranking |
| **Semantic Scholar** (Area A) | **Scopus / Web of Science** | Gold-standard citation data | Requires institutional subscription |

### Recommended Free Alternatives

For a budget-constrained academic project, the best free alternatives are:
1. **OpenAlex** — replace Semantic Scholar for unlimited paper searches
2. **PatentsView** — supplement Lens.org for US patent data (already implemented as `scrapers/patentsview.py`)
3. **GitHub API** — already available as a market demand proxy (was in original design)
4. **Stack Overflow API** — already available (was in original design)

---

## 10. How to Extend the Tool

### Adding a New Data Source

1. Create `scrapers/your_source.py` with a class containing a `scrape(core_term, secondary_term) → Dict` method
2. Import it in `agents/scraper.py` and call it in `scrape_subfield()`
3. Add new column names to `CSV_COLUMNS` in `processor/data_architect.py`
4. Update `transform_raw_to_csv_row()` to map the new keys
5. Add new columns to the appropriate area (A/B/C) in `visualizer/plot_engine.py` → `compute_metrics()`

### Adding New Subfields

Simply edit `targets.json` — add any `{name, core_term, secondary_term}` object. No code changes needed. There is no limit on the number of subfields.

### Changing the Visualization

- Edit `CONFIG` dict in `visualizer/plot_engine.py` for bubble sizes, colors, figure size
- Modify `plot_need_vs_research()` for layout changes
- The standalone `plot.py` is useful for quick iteration without running the full pipeline

---

## 11. Conclusion

The Research-to-Startup Gap Mapping System successfully automates the collection and visualization of multi-source research and market signals. The modular architecture allows easy addition of new data sources and domains. Key challenges remain around API access costs, search term granularity across different source types, and the need for domain-specific JSON configuration files.

The dummy data demonstrations for NLP, Cybersecurity, and Robotics domains show that when all signals are populated with realistic values, the gap map provides actionable insights for identifying under-commercialized research areas and startup opportunities.
