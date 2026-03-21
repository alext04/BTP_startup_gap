"""
Lens.org Scraper - Area B: Patents
Extracts patent counts, NPL citation rates, and corporate patent share.
"""

import requests
import time
from typing import Dict, Optional, List
from datetime import datetime, timezone
from bs4 import BeautifulSoup


class LensOrgScraper:
    """Scraper for Lens.org patent metrics."""
    
    BASE_URL = "https://www.lens.org/lens/search/patent/search"
    API_URL = "https://api.lens.org/patents"
    DATE_RANGE_START = "2023-01-01"
    DATE_RANGE_END = "2025-12-31"
    
    def __init__(self):
        """Initialize the scraper with a session."""
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        self.rate_limit_delay = 2.0  # seconds between requests (Lens.org is stricter)
    
    def _make_request(self, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make a rate-limited request."""
        try:
            time.sleep(self.rate_limit_delay)
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"  Lens.org API error: {e}")
            return None
    
    def _scrape_web_count(self, query: str) -> Optional[int]:
        """
        Scrape patent count from Lens.org web interface.
        Note: This is a fallback if API is not available.
        """
        try:
            time.sleep(self.rate_limit_delay)
            params = {
                "q": query,
                "publication_date": f"[{self.DATE_RANGE_START} TO {self.DATE_RANGE_END}]"
            }
            response = self.session.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            # Look for result count in the page
            # This selector may need adjustment based on actual page structure
            count_element = soup.find("span", class_="result-count")
            if count_element:
                count_text = count_element.get_text().replace(",", "")
                return int(count_text)
        except Exception as e:
            print(f"  Lens.org web scrape error: {e}")
        return None
    
    def get_patent_count(self, core_term: str, secondary_term: str) -> Optional[int]:
        """
        Get total patent count for the given terms in the date range 2023-2025.
        
        Args:
            core_term: Primary search term
            secondary_term: Secondary search term
            
        Returns:
            Total patent count or None if request fails.
        """
        query = f'"{core_term}" "{secondary_term}"'
        
        # Try API first
        params = {
            "query": query,
            "publication_date_min": self.DATE_RANGE_START,
            "publication_date_max": self.DATE_RANGE_END,
            "size": 0  # Get count only
        }
        
        result = self._make_request(self.API_URL, params)
        if result and "count" in result:
            return result["count"]
        
        # Fallback to web scraping
        return self._scrape_web_count(query)
    
    def get_top_assignees(self, core_term: str, secondary_term: str, limit: int = 10) -> List[Dict]:
        """
        Get top patent assignees for analysis.
        
        Args:
            core_term: Primary search term
            secondary_term: Secondary search term
            limit: Number of top assignees to retrieve
            
        Returns:
            List of assignee information or empty list if fails.
        """
        query = f'"{core_term}" "{secondary_term}"'
        
        params = {
            "query": query,
            "publication_date_min": self.DATE_RANGE_START,
            "publication_date_max": self.DATE_RANGE_END,
            "size": limit,
            "sort": "cited_by_count:desc"
        }
        
        result = self._make_request(self.API_URL, params)
        if result and "results" in result:
            patents = result["results"]
            assignees = []
            for patent in patents:
                assignee_info = {
                    "name": patent.get("applicant", ["Unknown"])[0] if isinstance(patent.get("applicant"), list) else patent.get("applicant", "Unknown"),
                    "type": self._classify_assignee_type(patent.get("applicant", [])),
                    "has_npl_citations": len(patent.get("cited_works", [])) > 0
                }
                assignees.append(assignee_info)
            return assignees
        
        return []
    
    def _classify_assignee_type(self, assignees: List[str]) -> str:
        """
        Classify if an assignee is a for-profit company.
        
        Returns:
            "company", "university", "government", or "unknown"
        """
        if not assignees:
            return "unknown"
        
        assignee = str(assignees[0]).lower() if isinstance(assignees, list) else str(assignees).lower()
        
        # Keywords for classification
        company_keywords = ["inc", "ltd", "llc", "corp", "corporation", "company", "gmbh", "co.", "co "]
        university_keywords = ["university", "college", "institute of technology", "school"]
        government_keywords = ["government", "agency", "department", "national", "institute"]
        
        for keyword in company_keywords:
            if keyword in assignee:
                return "company"
        
        for keyword in university_keywords:
            if keyword in assignee:
                return "university"
        
        for keyword in government_keywords:
            if keyword in assignee:
                return "government"
        
        return "unknown"
    
    def get_corporate_patent_share(self, core_term: str, secondary_term: str) -> Optional[int]:
        """
        Calculate corporate patent share as percentage.
        Inspect top 10 assignees; count for-profit companies and multiply by 10.
        
        Args:
            core_term: Primary search term
            secondary_term: Secondary search term
            
        Returns:
            Corporate share percentage (e.g., 7 companies = 70%) or None if fails.
        """
        assignees = self.get_top_assignees(core_term, secondary_term, limit=10)
        
        if not assignees:
            return None
        
        company_count = sum(1 for a in assignees if a["type"] == "company")
        # Multiply by 10 to get percentage (10 assignees = 100%)
        return company_count * 10
    
    def get_npl_citation_rate(self, core_term: str, secondary_term: str) -> Optional[int]:
        """
        Calculate NPL (Non-Patent Literature) citation rate.
        Check top 10 patents; count how many cite academic literature and multiply by 10.
        
        Args:
            core_term: Primary search term
            secondary_term: Secondary search term
            
        Returns:
            NPL citation rate percentage or None if fails.
        """
        query = f'"{core_term}" "{secondary_term}"'
        
        params = {
            "query": query,
            "publication_date_min": self.DATE_RANGE_START,
            "publication_date_max": self.DATE_RANGE_END,
            "size": 10,
            "sort": "cited_by_count:desc"
        }
        
        result = self._make_request(self.API_URL, params)
        if result and "results" in result:
            patents = result["results"]
            if not patents:
                return 0
            
            npl_count = 0
            for patent in patents:
                cited_works = patent.get("cited_works", [])
                # Check if any cited work appears to be academic (has DOI, journal, etc.)
                for work in cited_works:
                    if isinstance(work, dict):
                        if work.get("doi") or work.get("journal") or work.get("pmid"):
                            npl_count += 1
                            break
                    elif isinstance(work, str):
                        # Simple heuristic: academic citations often have DOI-like patterns
                        if "doi" in work.lower() or "journal" in work.lower():
                            npl_count += 1
                            break
            
            # Multiply by 10 to get percentage (10 patents = 100%)
            return npl_count * 10
        
        return None
    
    def scrape(self, core_term: str, secondary_term: str) -> Dict:
        """
        Scrape all patent metrics for a subfield.
        
        Args:
            core_term: Primary search term
            secondary_term: Secondary search term
            
        Returns:
            Dictionary with patent metrics or N/A for failures.
        """
        print(f"  [Lens.org] Scraping: '{core_term}' '{secondary_term}'")
        
        patent_count = self.get_patent_count(core_term, secondary_term)
        npl_rate = self.get_npl_citation_rate(core_term, secondary_term)
        corporate_share = self.get_corporate_patent_share(core_term, secondary_term)
        
        return {
            "patent_count_3yr": patent_count if patent_count is not None else "N/A",
            "npl_citation_rate": npl_rate if npl_rate is not None else "N/A",
            "corporate_patent_share": corporate_share if corporate_share is not None else "N/A",
            "scrape_timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "lens_org"
        }
