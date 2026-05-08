"""
Semantic Scholar Scraper - Area A: Research
Extracts paper counts and citation intensity from Semantic Scholar.
"""

import requests
import time
from typing import Dict, Optional
from datetime import datetime, timezone, date


class SemanticScholarScraper:
    """Scraper for Semantic Scholar research metrics."""
    
    BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the scraper.
        
        Args:
            api_key: Optional Semantic Scholar API key for higher rate limits.
        """
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({"x-api-key": api_key})
        # Standard API Key is 1 RPS. We use 2.0s to be safe and avoid burst triggers.
        # If no API key, we use 5.0s (Public limit is ~100 per 5 min).
        self.rate_limit_delay = 2.0 if api_key else 5.0
    
    def _make_request(self, params: Dict) -> Optional[Dict]:
        """Make a rate-limited request to Semantic Scholar API with retry."""
        max_retries = 3
        delay = self.rate_limit_delay

        for attempt in range(max_retries + 1):
            try:
                time.sleep(delay)
                if params.get("limit") == 0:
                    params["limit"] = 1
                response = self.session.get(self.BASE_URL, params=params, timeout=30)
                
                if response.status_code == 429:
                    # If rate limited, wait significantly longer
                    wait_time = 45 if attempt == 0 else 60
                    print(f"  [Semantic Scholar] Rate limited. Waiting {wait_time}s before retry {attempt+1}/{max_retries}...")
                    time.sleep(wait_time)
                    delay = self.rate_limit_delay * 2 # Increase base delay for remaining calls
                    continue
                    
                response.raise_for_status()
                return response.json()
            except requests.RequestException as e:
                if attempt < max_retries and isinstance(e, requests.HTTPError) and e.response is not None and e.response.status_code == 429:
                    continue
                print(f"Semantic Scholar API error: {e}")
                return None
        return None
    
    @staticmethod
    def _year_range() -> tuple:
        """Return (oldest_year, newest_year) for the last 3 complete calendar years."""
        current = date.today().year
        return current - 3, current - 1

    def get_paper_count(self, core_term: str, secondary_term: str) -> Optional[int]:
        """
        Get total paper count for the given terms across the last 3 complete calendar years.
        """
        yr_start, yr_end = self._year_range()
        query = f'"{core_term}" AND "{secondary_term}"'
        params = {
            "query": query,
            "year": f"{yr_start}-{yr_end}",
            "limit": 0  # We only need the count, not results
        }
        
        result = self._make_request(params)
        if result:
            return result.get("total", 0)
        return None
    
    def get_citation_intensity(self, core_term: str, secondary_term: str) -> Optional[float]:
        """
        Calculate citation intensity as the mean citation count of top 10 papers.
        """
        yr_start, yr_end = self._year_range()
        query = f'"{core_term}" AND "{secondary_term}"'
        params = {
            "query": query,
            "year": f"{yr_start}-{yr_end}",
            "limit": 10,
            "fields": "citationCount",
            "sort": "relevance"
        }
        
        result = self._make_request(params)
        if result and "data" in result:
            papers = result["data"]
            if not papers:
                return 0.0
            
            citation_counts = [paper.get("citationCount", 0) for paper in papers]
            avg_citations = sum(citation_counts) / len(citation_counts)
            return round(avg_citations, 2)
        return None
    
    def get_paper_growth_rate(self, core_term: str, secondary_term: str) -> Optional[float]:
        """
        Calculate YoY paper growth rate: most recent complete year vs the one before it.
        """
        _, yr_end = self._year_range()
        yr_prev = yr_end - 1  # e.g. 2024
        query = f'"{core_term}" AND "{secondary_term}"'

        result_prev = self._make_request({"query": query, "year": str(yr_prev), "limit": 0})
        count_prev = result_prev.get("total", 0) if result_prev else 0

        result_recent = self._make_request({"query": query, "year": str(yr_end), "limit": 0})
        count_recent = result_recent.get("total", 0) if result_recent else 0

        if count_prev == 0:
            return 0.0 if count_recent == 0 else 100.0

        return round(((count_recent - count_prev) / count_prev) * 100, 2)
    
    def scrape(self, core_term: str, secondary_term: str) -> Dict:
        """
        Scrape all research metrics for a subfield.
        
        Args:
            core_term: Primary search term
            secondary_term: Secondary search term
            
        Returns:
            Dictionary with research metrics or N/A for failures.
        """
        print(f"  [Semantic Scholar] Scraping: '{core_term}' AND '{secondary_term}'")
        
        paper_count = self.get_paper_count(core_term, secondary_term)
        citation_intensity = self.get_citation_intensity(core_term, secondary_term)
        growth_rate = self.get_paper_growth_rate(core_term, secondary_term)
        
        return {
            "paper_count_3yr": paper_count if paper_count is not None else "N/A",
            "citation_intensity_avg": citation_intensity if citation_intensity is not None else "N/A",
            "paper_growth_rate_yoy": growth_rate if growth_rate is not None else "N/A",
            "scrape_timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "semantic_scholar"
        }
