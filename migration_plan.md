# Area C Migration Plan: Venture & Entrepreneurial Demand

**Context for the Agent:**
We are restructuring the "Area C" metrics in our Gap Mapping System. We are dropping developer demand metrics (Stack Overflow, GitHub) and replacing them with startup and venture capital metrics. You must execute the following phases sequentially. Do not modify `Instructions.md` or `README.md`.

## Phase 1: Clean Up Old Architecture

* **Delete** the file `scrapers/market_demand.py`.

---

## Phase 2: Create `scrapers/product_hunt.py`

Create a new file at `scrapers/product_hunt.py` containing a `ProductHuntScraper` class.

* **Initialization:** It should accept a `product_hunt_token` (string) to authenticate via `Authorization: Bearer <token>`.
* **API Endpoint:** `POST https://api.producthunt.com/v2/api/graphql`
* **GraphQL Query:** Implement a pagination loop using `hasNextPage` and `endCursor` to query `posts(order: RANKING, search: $searchTerms)`. Extract the `createdAt` date from the node edges.
* **Metric 1 (`ph_launches_3yr`):** Count all posts where `createdAt` is between `2023-01-01` and `2025-12-31`.
* **Metric 2 (`ph_growth_yoy`):** Count posts in 2024 and 2025. Calculate YoY percentage growth: `((count_2025 - count_2024) / count_2024) * 100`. (Return `100.0` if 2024 is 0 and 2025 > 0; return `0.0` if both are 0).
* **Return Format:** The `scrape(self, core_term, secondary_term)` method should return a dictionary:

    ```python
    {
        "ph_launches_3yr": ph_launches_3yr,
        "ph_growth_yoy": ph_growth_yoy,
        "scrape_timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "product_hunt"
    }
    ```

---

## Phase 3: Update Pipeline Wiring

**File:** `agents/scraper.py`
* Replace `from scrapers.market_demand import MarketDemandScraper` with `from scrapers.product_hunt import ProductHuntScraper`.
* In `__init__`, replace `github_token` with `product_hunt_token` and instantiate `self.product_hunt = ProductHuntScraper(product_hunt_token)`.
* In `scrape_subfield()`, replace the `market_data` logic with `ph_data = self.product_hunt.scrape(core_term, secondary_term)` and merge `**ph_data` into `combined_data`.
* In `scrape_multiple_subfields()` error handling, replace the four old SO/GitHub keys with `"ph_launches_3yr": "N/A",` and `"ph_growth_yoy": "N/A",`.

**File:** `main.py`
* In `Orchestrator.__init__`, change `github_token` to `product_hunt_token`. Update the `ScraperAgent` instantiation to match.
* In `main()`, change the ArgumentParser argument from `--github-token` to `--product-hunt-token` and update the variable passing to the Orchestrator.

---

## Phase 4: Update Data Architect

**File:** `processor/data_architect.py`
* Update the `CSV_COLUMNS` list to exactly this:

    ```python
    CSV_COLUMNS = [
        "Subfield",
        "Paper Count (3yr)",
        "Citation Intensity (3yr avg)",
        "Paper Growth Rate (YoY %)",
        "Patent Count (3yr)",
        "NPL Citation Rate (3yr %)",
        "Corporate Patent Share (3yr %)",
        "Product Hunt Launches (3yr)",
        "Product Hunt Growth (YoY %)",
        "Form-D Filing Count (3yr)",
        "Capital Deployed (3yr $M)",
        "PE/VC Filing Growth (YoY %)"
    ]
    ```

* In `transform_raw_to_csv_row()`, remove the old SO/GitHub mappings and update the dictionary to map the new layout:

    ```python
    "Product Hunt Launches (3yr)": self._clean_numeric(raw_data.get("ph_launches_3yr")),
    "Product Hunt Growth (YoY %)": self._clean_numeric(raw_data.get("ph_growth_yoy")),
    # Note: The three Form-D keys remain the same but are conceptually moved to Area C in the plot engine.
    ```

---

## Phase 5: Update Plot Engine & Standalone Plotter

**Files:** `visualizer/plot_engine.py` AND `plot.py`
* In BOTH files, locate the `compute_metrics(df)` function.
* Update the variable grouping arrays exactly as follows so the Z-score calculation maps correctly:

    ```python
        area_a = [
            'Paper Count (3yr)', 
            'Citation Intensity (3yr avg)', 
            'Paper Growth Rate (YoY %)'
        ]
        
        area_b_sil = [
            'NPL Citation Rate (3yr %)', 
            'Corporate Patent Share (3yr %)'
        ] 
        
        area_c = [
            'Product Hunt Launches (3yr)', 
            'Product Hunt Growth (YoY %)', 
            'Form-D Filing Count (3yr)', 
            'Capital Deployed (3yr $M)', 
            'PE/VC Filing Growth (YoY %)'
        ]
    ```