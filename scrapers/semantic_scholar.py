"""
Semantic Scholar Scraper - Area A: Research
Extracts paper counts and citation intensity from Semantic Scholar.
"""

import requests
import time
from typing import Dict, Optional
from datetime import datetime, timezone


class SemanticScholarScraper:
    """Scraper for Semantic Scholar research metrics."""
    
    BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
    DATE_RANGE_START = "2023-01-01"
    DATE_RANGE_END = "2025-12-31"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the scraper.
        
        Args:
            api_key: Optional Semantic Scholar API key for higher rate limits.
        """
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({"x-api-key": api_key})
        self.rate_limit_delay = 1.0  # seconds between requests
    
    def _make_request(self, params: Dict) -> Optional[Dict]:
        """Make a rate-limited request to Semantic Scholar API."""
        try:
            time.sleep(self.rate_limit_delay)
            response = self.session.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Semantic Scholar API error: {e}")
            return None
    
    def get_paper_count(self, core_term: str, secondary_term: str) -> Optional[int]:
        """
        Get total paper count for the given terms in the date range 2023-2025.
        
        Args:
            core_term: Primary search term (e.g., "solid-state battery")
            secondary_term: Secondary search term (e.g., "energy storage")
            
        Returns:
            Total paper count or None if request fails.
        """
        query = f'"{core_term}" AND "{secondary_term}"'
        params = {
            "query": query,
            "year": "2023-2025",
            "limit": 0  # We only need the count, not results
        }
        
        result = self._make_request(params)
        if result:
            return result.get("total", 0)
        return None
    
    def get_citation_intensity(self, core_term: str, secondary_term: str) -> Optional[float]:
        """
        Calculate citation intensity as the mean citation count of top 10 papers.
        
        Args:
            core_term: Primary search term
            secondary_term: Secondary search term
            
        Returns:
            Average citation count of top 10 papers or None if request fails.
        """
        query = f'"{core_term}" AND "{secondary_term}"'
        params = {
            "query": query,
            "year": "2023-2025",
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
        Calculate YoY paper growth rate (2025 vs 2024).
        
        Args:
            core_term: Primary search term
            secondary_term: Secondary search term
            
        Returns:
            Growth rate percentage or None if request fails.
        """
        query = f'"{core_term}" AND "{secondary_term}"'
        
        # Get 2024 count
        params_2024 = {
            "query": query,
            "year": "2024",
            "limit": 0
        }
        result_2024 = self._make_request(params_2024)
        count_2024 = result_2024.get("total", 0) if result_2024 else 0
        
        # Get 2025 count
        params_2025 = {
            "query": query,
            "year": "2025",
            "limit": 0
        }
        result_2025 = self._make_request(params_2025)
        count_2025 = result_2025.get("total", 0) if result_2025 else 0
        
        if count_2024 == 0:
            return 0.0 if count_2025 == 0 else 100.0
        
        growth_rate = ((count_2025 - count_2024) / count_2024) * 100
        return round(growth_rate, 2)
    
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
