"""
Market Demand Scraper - Area C: Stack Overflow & GitHub
Extracts question volumes, growth rates, repo counts, and star growth.
"""

import requests
import time
from typing import Dict, Optional, List
from datetime import datetime, timezone, timedelta


class StackOverflowScraper:
    """Scraper for Stack Overflow question metrics."""
    
    BASE_URL = "https://api.stackexchange.com/2.3/search/advanced"
    
    def __init__(self):
        """Initialize the SO scraper."""
        self.session = requests.Session()
        self.rate_limit_delay = 1.0
    
    def _make_request(self, params: Dict) -> Optional[Dict]:
        """Make a rate-limited request to SO API."""
        try:
            time.sleep(self.rate_limit_delay)
            response = self.session.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"  Stack Overflow API error: {e}")
            return None
    
    def get_question_volume(self, core_term: str, secondary_term: str) -> Optional[int]:
        """
        Get question volume for the last 12 months.

        Args:
            core_term: Primary search term
            secondary_term: Secondary search term

        Returns:
            Total question count or None if request fails.
        """
        # Calculate date range for last 12 months
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=365)

        # Use OR logic for better results
        query = f"{core_term} OR {secondary_term}"
        params = {
            "q": query,
            "fromdate": int(start_date.timestamp()),
            "todate": int(end_date.timestamp()),
            "site": "stackoverflow",
            "pagesize": 1  # We only need the count
        }

        result = self._make_request(params)
        if result:
            return result.get("total", 0)
        return None
    
    def get_question_growth_rate(self, core_term: str, secondary_term: str) -> Optional[float]:
        """
        Calculate YoY question growth rate (recent 6 months vs previous 6 months).

        Args:
            core_term: Primary search term
            secondary_term: Secondary search term

        Returns:
            Growth rate percentage or None if request fails.
        """
        now = datetime.now(timezone.utc)

        # Recent 6 months
        recent_end = now
        recent_start = now - timedelta(days=180)

        # Previous 6 months
        prev_end = recent_start
        prev_start = prev_end - timedelta(days=180)

        # Use OR logic for better results
        query = f"{core_term} OR {secondary_term}"

        # Get recent period count
        params_recent = {
            "q": query,
            "fromdate": int(recent_start.timestamp()),
            "todate": int(recent_end.timestamp()),
            "site": "stackoverflow",
            "pagesize": 1
        }
        result_recent = self._make_request(params_recent)
        count_recent = result_recent.get("total", 0) if result_recent else 0

        # Get previous period count
        params_prev = {
            "q": query,
            "fromdate": int(prev_start.timestamp()),
            "todate": int(prev_end.timestamp()),
            "site": "stackoverflow",
            "pagesize": 1
        }
        result_prev = self._make_request(params_prev)
        count_prev = result_prev.get("total", 0) if result_prev else 0
        
        if count_prev == 0:
            return 0.0 if count_recent == 0 else 100.0
        
        growth_rate = ((count_recent - count_prev) / count_prev) * 100
        return round(growth_rate, 2)
    
    def scrape(self, core_term: str, secondary_term: str) -> Dict:
        """Scrape all SO metrics."""
        print(f"  [Stack Overflow] Scraping: '{core_term}' '{secondary_term}'")
        
        volume = self.get_question_volume(core_term, secondary_term)
        growth = self.get_question_growth_rate(core_term, secondary_term)
        
        return {
            "so_question_volume": volume if volume is not None else 0,
            "so_question_growth": growth if growth is not None else 0.0,
            "scrape_timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "stack_overflow"
        }


class GitHubScraper:
    """Scraper for GitHub repository metrics."""
    
    BASE_URL = "https://api.github.com/search/repositories"
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize the GitHub scraper.
        
        Args:
            token: Optional GitHub personal access token for higher rate limits.
        """
        self.session = requests.Session()
        if token:
            self.session.headers.update({"Authorization": f"token {token}"})
        else:
            self.session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
        self.rate_limit_delay = 2.0  # GitHub has strict rate limits
    
    def _make_request(self, params: Dict) -> Optional[Dict]:
        """Make a rate-limited request to GitHub API."""
        try:
            time.sleep(self.rate_limit_delay)
            response = self.session.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"  GitHub API error: {e}")
            return None
    
    def get_repo_count(self, core_term: str, secondary_term: str) -> Optional[int]:
        """
        Get repository count created in the last 3 years.

        Args:
            core_term: Primary search term
            secondary_term: Secondary search term

        Returns:
            Total repo count or None if request fails.
        """
        # Search for repos created in 2023-2025 using OR logic for better results
        query = f'"{core_term}" OR "{secondary_term}" created:2023-01-01..2025-12-31'
        params = {
            "q": query,
            "per_page": 1  # We only need the count
        }

        result = self._make_request(params)
        if result and "total_count" in result:
            return result["total_count"]
        return None
    
    def get_star_growth_rate(self, core_term: str, secondary_term: str) -> Optional[float]:
        """
        Calculate YoY star growth for repos (2025 vs 2024).

        Args:
            core_term: Primary search term
            secondary_term: Secondary search term

        Returns:
            Star growth rate percentage or None if request fails.
        """
        # Get repos from 2024 using OR logic
        query_2024 = f'"{core_term}" OR "{secondary_term}" created:2024-01-01..2024-12-31'
        params_2024 = {
            "q": query_2024,
            "per_page": 10,
            "sort": "stars"
        }
        result_2024 = self._make_request(params_2024)

        # Get repos from 2025 using OR logic
        query_2025 = f'"{core_term}" OR "{secondary_term}" created:2025-01-01..2025-12-31'
        params_2025 = {
            "q": query_2025,
            "per_page": 10,
            "sort": "stars"
        }
        result_2025 = self._make_request(params_2025)
        
        if not result_2024 or not result_2025:
            return None
        
        repos_2024 = result_2024.get("items", [])
        repos_2025 = result_2025.get("items", [])
        
        if not repos_2024 and not repos_2025:
            return 0.0
        
        # Calculate average stars for each year
        avg_stars_2024 = sum(r.get("stargazers_count", 0) for r in repos_2024) / max(len(repos_2024), 1)
        avg_stars_2025 = sum(r.get("stargazers_count", 0) for r in repos_2025) / max(len(repos_2025), 1)
        
        if avg_stars_2024 == 0:
            return 0.0 if avg_stars_2025 == 0 else 100.0
        
        growth_rate = ((avg_stars_2025 - avg_stars_2024) / avg_stars_2024) * 100
        return round(growth_rate, 2)
    
    def scrape(self, core_term: str, secondary_term: str) -> Dict:
        """Scrape all GitHub metrics."""
        print(f"  [GitHub] Scraping: '{core_term}' '{secondary_term}'")
        
        repo_count = self.get_repo_count(core_term, secondary_term)
        star_growth = self.get_star_growth_rate(core_term, secondary_term)
        
        return {
            "github_repo_count_3y": repo_count if repo_count is not None else 0,
            "github_star_growth": star_growth if star_growth is not None else 0.0,
            "scrape_timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "github"
        }


class MarketDemandScraper:
    """Combined scraper for Stack Overflow and GitHub."""
    
    def __init__(self, github_token: Optional[str] = None):
        """
        Initialize the market demand scraper.
        
        Args:
            github_token: Optional GitHub token for higher rate limits.
        """
        self.so_scraper = StackOverflowScraper()
        self.github_scraper = GitHubScraper(github_token)
    
    def scrape(self, core_term: str, secondary_term: str) -> Dict:
        """
        Scrape all market demand metrics for a subfield.
        
        Args:
            core_term: Primary search term
            secondary_term: Secondary search term
            
        Returns:
            Dictionary with market demand metrics.
        """
        so_data = self.so_scraper.scrape(core_term, secondary_term)
        github_data = self.github_scraper.scrape(core_term, secondary_term)
        
        return {
            **so_data,
            **github_data,
            "combined_timestamp": datetime.now(timezone.utc).isoformat()
        }
