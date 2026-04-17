"""
SEC EDGAR Form-D Scraper - Area B: PE/VC Investment Activity
Extracts Form-D filing counts and capital deployment from SEC EDGAR EFTS API.

Two-phase approach:
  Phase 1: EFTS full-text search → filing count + accession numbers
  Phase 2: Parse primary_doc.xml → totalAmountSold, investors, entityType
"""

import requests
import time
import xml.etree.ElementTree as ET
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timezone


class EdgarFormDScraper:
    """Scraper for SEC EDGAR Form-D filings (PE/VC investment signals)."""

    EFTS_URL = "https://efts.sec.gov/LATEST/search-index"
    SEC_ARCHIVES = "https://www.sec.gov/Archives/edgar/data"

    def __init__(self, max_filings_to_parse: int = 20):
        """
        Initialize the Form-D scraper.

        Args:
            max_filings_to_parse: Max filings to fetch XML for capital data.
        """
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "BTP_Research_GapMap research@university.edu",
            "Accept": "application/json"
        })
        self.rate_limit_delay = 0.5  # EDGAR allows 10 req/sec
        self.max_filings_to_parse = max_filings_to_parse

    def _efts_search(self, query: str, start_date: str, end_date: str) -> Optional[Dict]:
        """
        Phase 1: Search EDGAR EFTS for Form-D filings.

        Args:
            query: Full-text search query.
            start_date: Start date (YYYY-MM-DD).
            end_date: End date (YYYY-MM-DD).

        Returns:
            EFTS JSON response or None on failure.
        """
        params = {
            "q": query,
            "forms": "D",
            "dateRange": "custom",
            "startdt": start_date,
            "enddt": end_date
        }
        try:
            time.sleep(self.rate_limit_delay)
            response = self.session.get(self.EFTS_URL, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"  EDGAR EFTS API error: {e}")
            return None

    def _parse_filing_xml(self, cik: str, accession: str) -> Optional[Dict]:
        """
        Phase 2: Parse a Form-D primary_doc.xml for financial data.

        Args:
            cik: CIK number (without leading zeros).
            accession: Accession number (with dashes removed).

        Returns:
            Dict with parsed financial fields or None on failure.
        """
        url = f"{self.SEC_ARCHIVES}/{cik}/{accession}/primary_doc.xml"
        try:
            time.sleep(self.rate_limit_delay)
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            root = ET.fromstring(response.text)

            total_offering = root.findtext(".//totalOfferingAmount", "0")
            total_sold = root.findtext(".//totalAmountSold", "0")
            num_investors = root.findtext(".//totalNumberAlreadyInvested", "0")
            entity_type = root.findtext(".//entityType", "Unknown")
            industry_group = root.findtext(".//industryGroup/industryGroupType", "Unknown")
            year_inc = root.findtext(".//yearOfInc/value", "Unknown")

            # Parse dollar amounts (handle "Indefinite")
            def parse_amount(val: str) -> float:
                if val in ("Indefinite", "Decline to Disclose", ""):
                    return 0.0
                try:
                    return float(val.replace(",", ""))
                except (ValueError, AttributeError):
                    return 0.0

            return {
                "total_offering": parse_amount(total_offering),
                "total_sold": parse_amount(total_sold),
                "num_investors": int(num_investors) if num_investors.isdigit() else 0,
                "entity_type": entity_type,
                "industry_group": industry_group,
                "year_inc": year_inc,
                "is_pooled_fund": industry_group == "Pooled Investment Fund"
            }
        except Exception as e:
            print(f"  Form-D XML parse error ({url}): {e}")
            return None

    def get_filing_count(
        self, core_term: str, secondary_term: str,
        start_date: str = "2023-01-01", end_date: str = "2025-12-31"
    ) -> Tuple[int, List[Dict]]:
        """
        Get Form-D filing count and hit metadata for a subfield.

        Uses OR logic: searches for core_term OR secondary_term.

        Args:
            core_term: Primary search term.
            secondary_term: Secondary search term.
            start_date: Range start.
            end_date: Range end.

        Returns:
            Tuple of (total_count, list_of_hit_metadata).
        """
        query = f'"{core_term}" OR "{secondary_term}"'
        result = self._efts_search(query, start_date, end_date)

        if not result:
            return 0, []

        total = result.get("hits", {}).get("total", {}).get("value", 0)
        hits = result.get("hits", {}).get("hits", [])

        hit_list = []
        for hit in hits:
            source = hit.get("_source", {})
            ciks = source.get("ciks", [])
            accession = source.get("adsh", "")
            if ciks and accession:
                hit_list.append({
                    "cik": ciks[0].lstrip("0"),
                    "accession": accession.replace("-", ""),
                    "file_date": source.get("file_date", ""),
                    "display_names": source.get("display_names", [])
                })

        return total, hit_list

    def get_capital_deployed(self, hits: List[Dict]) -> Dict:
        """
        Parse XML for up to max_filings_to_parse hits to get capital data.

        Args:
            hits: List of hit metadata from get_filing_count.

        Returns:
            Dict with aggregated capital metrics.
        """
        total_capital = 0.0
        total_offering = 0.0
        total_investors = 0
        filings_parsed = 0
        operating_company_filings = 0

        for hit in hits[:self.max_filings_to_parse]:
            parsed = self._parse_filing_xml(hit["cik"], hit["accession"])
            if parsed:
                filings_parsed += 1
                total_capital += parsed["total_sold"]
                total_offering += parsed["total_offering"]
                total_investors += parsed["num_investors"]
                if not parsed["is_pooled_fund"]:
                    operating_company_filings += 1

        return {
            "capital_deployed": total_capital,
            "total_offering": total_offering,
            "total_investors": total_investors,
            "filings_parsed": filings_parsed,
            "operating_company_filings": operating_company_filings
        }

    def get_filing_growth_rate(
        self, core_term: str, secondary_term: str
    ) -> Optional[float]:
        """
        Calculate YoY filing growth rate (2025 vs 2024).

        Args:
            core_term: Primary search term.
            secondary_term: Secondary search term.

        Returns:
            Growth rate percentage or None on failure.
        """
        count_2024, _ = self.get_filing_count(
            core_term, secondary_term,
            start_date="2024-01-01", end_date="2024-12-31"
        )
        count_2025, _ = self.get_filing_count(
            core_term, secondary_term,
            start_date="2025-01-01", end_date="2025-12-31"
        )

        if count_2024 == 0:
            return 0.0 if count_2025 == 0 else 100.0

        growth = ((count_2025 - count_2024) / count_2024) * 100
        return round(growth, 2)

    def scrape(self, core_term: str, secondary_term: str) -> Dict:
        """
        Scrape all Form-D PE/VC metrics for a subfield.

        Args:
            core_term: Primary search term.
            secondary_term: Secondary search term.

        Returns:
            Dictionary with Form-D metrics.
        """
        print(f"  [EDGAR Form-D] Scraping: '{core_term}' OR '{secondary_term}'")

        # Phase 1: Get filing count and hits
        filing_count, hits = self.get_filing_count(core_term, secondary_term)
        print(f"  [EDGAR Form-D] Found {filing_count} Form-D filings (3yr)")

        # Phase 2: Parse XML for capital data
        capital_data = {"capital_deployed": 0.0, "filings_parsed": 0}
        if hits:
            capital_data = self.get_capital_deployed(hits)
            deployed_m = capital_data["capital_deployed"] / 1_000_000
            print(f"  [EDGAR Form-D] Capital deployed: ${deployed_m:.1f}M "
                  f"(from {capital_data['filings_parsed']} parsed filings)")

        # Filing growth
        filing_growth = self.get_filing_growth_rate(core_term, secondary_term)

        return {
            "form_d_filing_count_3yr": filing_count,
            "form_d_capital_deployed_mil": round(
                capital_data["capital_deployed"] / 1_000_000, 2
            ),
            "form_d_filing_growth_yoy": filing_growth if filing_growth is not None else 0.0,
            "scrape_timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "edgar_form_d"
        }
