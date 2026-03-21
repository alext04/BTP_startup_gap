# Technical Operating Instructions

## I. Data Schema & File Management
1. **Output Format**: Every run MUST generate a CSV file with these exact columns:
   `Subfield, Paper Count (3yr), Citation Intensity (3yr avg), Paper Growth Rate (YoY %), Patent Count (3yr), NPL Citation Rate (3yr %), Corporate Patent Share (3yr %), SO Question Vol (12mo), SO Question Growth (12mo %), GitHub Repo Count (3Y), GitHub Star Growth (12mo %)`
2. **Naming Convention**: All output files must include a UTC timestamp: `[Subfield_Name]_[YYYYMMDD_HHMMSS].csv`.
3. **Storage**: Detail logs for each "field" (metric) should be kept in a `logs/` directory for debugging.

## II. Scraping Logic (Area-Specific)

### Area A: Research (Semantic Scholar)
* **Date Filters**: Set range to 2023–2025 for counts; use 2025 vs 2024 for growth.
* **Citation Calculation**: Sort by "Relevance," take the top 10 papers, and calculate the arithmetic mean of their citation counts.

### Area B: Patents (Lens.org)
* **Corporate Share**: Inspect the top 10 assignees; count for-profit companies and multiply by 10 to get a percentage (e.g., 7 companies = 70%).
* **NPL Rate**: Check the "Cited Works" of the top 10 patents. Count how many cite academic literature and multiply by 10.

### Area C: Market Demand (SO & GitHub)
* **Stack Overflow**: Use specific search syntax `is:q created:2023-01-01..2025-12-31`. Handle 0 results as 0.0, not null.
* **GitHub**: Count repositories created in the 3-year window and calculate YoY star growth for repos created in 2025 vs 2024.

## III. Pipeline Execution (Modularity Rules)
1. **Isolation**: The `plot.py` script must remain decoupled from the scraper. It should only interact with the final CSV.
2. **Error Resilience**: If a scraper fails (e.g., Lens.org blocks a request), the agent must record "N/A" for those specific columns and continue the pipeline.
3. **Data Integrity**: Before visualization, the Data Architect must ensure all numerical strings (e.g., "102,000") are stripped of commas for the Python `pd.to_numeric` function.