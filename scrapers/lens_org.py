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
    API_URL = "https://api.lens.org/patent/search"
    DATE_RANGE_START = "2023-01-01"
    DATE_RANGE_END = "2025-12-31"
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the scraper with a session and optional API key."""
        self.api_key = api_key
        self._unauthorized = False  # set True on first 401 to skip remaining calls
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        if api_key:
            self.session.headers.update({
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            })
        self.rate_limit_delay = 2.0  # seconds between requests (Lens.org is stricter)
    
    def _build_query(self, core_term: str, secondary_term: str) -> str:
        """Build Lens.org Lucene query with date range baked in."""
        def term_to_bool(term: str) -> str:
            words = term.strip().split()
            if len(words) == 1:
                return words[0]
            return "(" + " AND ".join(words) + ")"
        text_part = f"{term_to_bool(core_term)} AND {term_to_bool(secondary_term)}"
        date_part = f"date_published:[{self.DATE_RANGE_START} TO {self.DATE_RANGE_END}]"
        return f"({text_part}) AND {date_part}"
    
    def _make_request(self, payload: Dict) -> Optional[Dict]:
        """Make a rate-limited POST request to Lens.org API."""
        if not self.api_key:
            print("  [Lens.org] No API key provided, skipping API call")
            return None
        if self._unauthorized:
            return None
        try:
            time.sleep(self.rate_limit_delay)
            response = self.session.post(self.API_URL, json=payload, timeout=30)
            if response.status_code == 401:
                self._unauthorized = True
                print("  [Lens.org] 401 Unauthorized ")
                return None
            if response.status_code == 429:
                print("  [Lens.org] Rate limited, waiting 10s...")
                time.sleep(10)
                response = self.session.post(self.API_URL, json=payload, timeout=30)
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
        query = self._build_query(core_term, secondary_term)
        
        payload = {
            "query": query,
            "size": 0,  # count only
        }

        result = self._make_request(payload)
        if result and "total" in result:
            return result["total"]
        return None
    
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
        query = self._build_query(core_term, secondary_term)
        
        payload = {
            "query": query,
            "size": limit,
            "include": ["biblio.parties"],
        }
        
        result = self._make_request(payload)
        if result and "data" in result:
            patents = result["data"]
            assignees = []
            for patent in patents:
                parties = patent.get("biblio", {}).get("parties", {})
                applicants = parties.get("applicants", [])
                name = "Unknown"
                if applicants:
                    first = applicants[0]
                    if isinstance(first, dict):
                        en = first.get("extracted_name", {})
                        name = en.get("value", "Unknown") if isinstance(en, dict) else str(en)
                    else:
                        name = str(first)
                assignee_info = {
                    "name": name,
                    "type": self._classify_assignee_type([name]),
                    "has_npl_citations": bool(patent.get("biblio", {}).get("references_cited", {}).get("npl_citations", []))
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
        query = self._build_query(core_term, secondary_term)
        
        payload = {
            "query": query,
            "size": 10,
            "include": ["biblio.references_cited"],
        }
        
        result = self._make_request(payload)
        if result and "data" in result:
            patents = result["data"]
            if not patents:
                return 0
            
            npl_count = 0
            for patent in patents:
                refs = patent.get("biblio", {}).get("references_cited", {})
                npl_citations = refs.get("npl_citations", []) if isinstance(refs, dict) else []
                if npl_citations:
                    npl_count += 1
            
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
