"""
Product Hunt Scraper - Area C: Venture & Entrepreneurial Demand
Queries the Product Hunt V2 GraphQL API for launch volume and growth by search term.
"""

import time
import requests
from datetime import datetime, timezone, date
from typing import Dict, Optional


MAX_PAGES = 15       # cap pagination to avoid very long runs
REQUEST_DELAY = 0.5  # seconds between page requests


class ProductHuntScraper:
    """Scraper for Product Hunt launches (entrepreneurial signals)."""

    def __init__(self, product_hunt_token: Optional[str] = None):
        """
        Args:
            product_hunt_token: Personal API token. Set PRODUCT_HUNT_TOKEN in .env.
        """
        self.token = product_hunt_token
        self.url = "https://api.producthunt.com/v2/api/graphql"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _year_range() -> tuple:
        """Return (oldest_year, newest_year) for the last 3 complete calendar years."""
        current = date.today().year
        return current - 3, current - 1

    def scrape(self, core_term: str, secondary_term: str,
               search_term: Optional[str] = None,
               topic: Optional[str] = None) -> Dict:
        """
        Query Product Hunt for post counts by search term and calculate metrics.

        Args:
            core_term: Fallback search query if search_term is not set.
            secondary_term: Kept for interface compatibility.
            search_term: Primary query — set via product_hunt_term in targets.json.
            topic: Unused — kept for interface compatibility.

        Returns:
            Dictionary with Product Hunt metrics.
        """
        if not self.token:
            print("  [Product Hunt] No token configured — set PRODUCT_HUNT_TOKEN in .env")
            return {
                "ph_launches_3yr": "N/A",
                "ph_growth_yoy": "N/A",
                "scrape_timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "product_hunt",
            }

        query = search_term or core_term
        print(f"  [Product Hunt] Scraping: '{query}'")

        yr_start, yr_end = self._year_range()
        posted_after  = f"{yr_start}-01-01T00:00:00+00:00"
        posted_before = f"{yr_end + 1}-01-01T00:00:00+00:00"

        gql = """
        query($term: String!, $cursor: String, $postedAfter: DateTime, $postedBefore: DateTime) {
          posts(search: $term, order: NEWEST, after: $cursor,
                postedAfter: $postedAfter, postedBefore: $postedBefore, first: 20) {
            edges {
              node { createdAt }
            }
            pageInfo { hasNextPage endCursor }
          }
        }
        """

        all_dates = []
        cursor = None
        pages = 0

        while pages < MAX_PAGES:
            variables = {
                "term": query,
                "cursor": cursor,
                "postedAfter": posted_after,
                "postedBefore": posted_before,
            }
            time.sleep(REQUEST_DELAY)
            try:
                response = requests.post(
                    self.url,
                    headers=self.headers,
                    json={"query": gql, "variables": variables},
                    timeout=30,
                )
                if response.status_code == 429:
                    reset_in = response.headers.get("x-rate-limit-reset", "unknown")
                    print(f"  [Product Hunt] Rate limited. Reset in {reset_in}s — returning N/A.")
                    return {
                        "ph_launches_3yr": "N/A",
                        "ph_growth_yoy": "N/A",
                        "scrape_timestamp": datetime.now(timezone.utc).isoformat(),
                        "source": "product_hunt",
                    }
                response.raise_for_status()
                data = response.json()

                if "errors" in data:
                    for err in data["errors"]:
                        print(f"  [Product Hunt] GraphQL error: {err.get('message')}")
                    break

                posts_data = data.get("data", {}).get("posts", {})
                if not posts_data:
                    break

                edges = posts_data.get("edges", [])
                for edge in edges:
                    created_at = edge.get("node", {}).get("createdAt")
                    if created_at:
                        all_dates.append(created_at)

                page_info = posts_data.get("pageInfo", {})
                if not page_info.get("hasNextPage") or not edges:
                    break

                cursor = page_info.get("endCursor")
                pages += 1

            except Exception as e:
                print(f"  [Product Hunt] API error: {e}")
                break

        # Count by year
        yr_mid = yr_end - 1
        counts = {yr_start: 0, yr_mid: 0, yr_end: 0}

        for date_str in all_dates:
            try:
                if date_str.endswith("Z"):
                    dt = datetime.fromisoformat(date_str[:-1] + "+00:00")
                else:
                    dt = datetime.fromisoformat(date_str)
                if dt.year in counts:
                    counts[dt.year] += 1
            except ValueError:
                continue

        ph_launches_3yr = sum(counts.values())

        if counts[yr_mid] == 0:
            ph_growth_yoy = 100.0 if counts[yr_end] > 0 else 0.0
        else:
            ph_growth_yoy = round(((counts[yr_end] - counts[yr_mid]) / counts[yr_mid]) * 100.0, 2)

        print(
            f"  [Product Hunt] {yr_start}: {counts[yr_start]}  {yr_mid}: {counts[yr_mid]}  "
            f"{yr_end}: {counts[yr_end]}  → 3yr total: {ph_launches_3yr}, "
            f"growth: {ph_growth_yoy}%  ({pages + 1} page(s))"
        )

        return {
            "ph_launches_3yr": ph_launches_3yr,
            "ph_growth_yoy": ph_growth_yoy,
            "scrape_timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "product_hunt",
        }
