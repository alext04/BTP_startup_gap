"""
Product Hunt Scraper - Area C: Venture & Entrepreneurial Demand
Queries the Product Hunt V2 GraphQL API for startup launch volume and growth.
"""

import requests
from datetime import datetime, timezone
from typing import Dict, Optional


class ProductHuntScraper:
    """Scraper for Product Hunt launches (entrepreneurial signals)."""

    def __init__(self, product_hunt_token: Optional[str] = None):
        """
        Initialize the Product Hunt scraper.

        Args:
            product_hunt_token: Personal API token. Set PRODUCT_HUNT_TOKEN in .env.
        """
        self.token = product_hunt_token
        self.url = "https://api.producthunt.com/v2/api/graphql"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def scrape(self, core_term: str, secondary_term: str) -> Dict:
        """
        Query Product Hunt for post counts and calculate metrics.

        Args:
            core_term: Primary search term.
            secondary_term: Secondary search term.

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

        print(f"  [Product Hunt] Scraping: '{core_term} {secondary_term}'")
        search_terms = f"{core_term} {secondary_term}"
        
        query = """
        query($searchTerms: String, $cursor: String) {
          posts(order: RANKING, search: $searchTerms, after: $cursor) {
            edges {
              node {
                createdAt
              }
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
        }
        """
        
        all_dates = []
        has_next_page = True
        cursor = None
        
        while has_next_page:
            variables = {
                "searchTerms": search_terms,
                "cursor": cursor
            }
            
            try:
                response = requests.post(
                    self.url,
                    headers=self.headers,
                    json={"query": query, "variables": variables},
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()
                
                posts_data = data.get("data", {}).get("posts", {})
                if not posts_data:
                    break
                    
                edges = posts_data.get("edges", [])
                for edge in edges:
                    created_at = edge.get("node", {}).get("createdAt")
                    if created_at:
                        all_dates.append(created_at)
                
                page_info = posts_data.get("pageInfo", {})
                has_next_page = page_info.get("hasNextPage", False)
                cursor = page_info.get("endCursor")
                
                if not edges:
                    break
                    
            except Exception as e:
                print(f"  [Product Hunt] API error: {e}")
                break
        
        count_2023 = 0
        count_2024 = 0
        count_2025 = 0
        
        for date_str in all_dates:
            try:
                # Handle ISO format with Z or timezone offset
                if date_str.endswith('Z'):
                    dt = datetime.fromisoformat(date_str[:-1] + '+00:00')
                else:
                    dt = datetime.fromisoformat(date_str)
                
                year = dt.year
                if year == 2023:
                    count_2023 += 1
                elif year == 2024:
                    count_2024 += 1
                elif year == 2025:
                    count_2025 += 1
            except ValueError:
                continue
        
        ph_launches_3yr = count_2023 + count_2024 + count_2025
        
        if count_2024 == 0:
            ph_growth_yoy = 100.0 if count_2025 > 0 else 0.0
        else:
            ph_growth_yoy = ((count_2025 - count_2024) / count_2024) * 100.0
        
        print(f"  [Product Hunt] Found {ph_launches_3yr} launches (3yr)")
            
        return {
            "ph_launches_3yr": ph_launches_3yr,
            "ph_growth_yoy": round(ph_growth_yoy, 2),
            "scrape_timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "product_hunt"
        }
