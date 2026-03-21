"""
The Scraper Agent - Main Entry Point
Orchestrates all scrapers to collect data from all sources.
"""

import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

from scrapers.semantic_scholar import SemanticScholarScraper
from scrapers.lens_org import LensOrgScraper
from scrapers.market_demand import MarketDemandScraper


class ScraperAgent:
    """
    The Scraper Agent coordinates data collection from all sources:
    - Semantic Scholar (Research)
    - Lens.org (Patents)
    - Stack Overflow & GitHub (Market Demand)
    """
    
    def __init__(
        self,
        semantic_scholar_api_key: Optional[str] = None,
        github_token: Optional[str] = None,
        output_dir: str = "."
    ):
        """
        Initialize the Scraper Agent.
        
        Args:
            semantic_scholar_api_key: Optional API key for Semantic Scholar.
            github_token: Optional GitHub token for higher rate limits.
            output_dir: Directory to save raw signal files.
        """
        self.semantic_scholar = SemanticScholarScraper(semantic_scholar_api_key)
        self.lens_org = LensOrgScraper()
        self.market_demand = MarketDemandScraper(github_token)
        self.output_dir = output_dir
    
    def scrape_subfield(self, subfield_name: str, core_term: str, secondary_term: str) -> Dict:
        """
        Scrape all metrics for a single subfield.
        
        Args:
            subfield_name: Display name of the subfield.
            core_term: Primary search term.
            secondary_term: Secondary search term.
            
        Returns:
            Dictionary containing all scraped metrics.
        """
        print(f"\n[Scraper Agent] Processing: {subfield_name}")
        print(f"  Search terms: '{core_term}' + '{secondary_term}'")
        
        # Scrape from all sources
        research_data = self.semantic_scholar.scrape(core_term, secondary_term)
        patent_data = self.lens_org.scrape(core_term, secondary_term)
        market_data = self.market_demand.scrape(core_term, secondary_term)
        
        # Combine all data
        combined_data = {
            "subfield_name": subfield_name,
            "search_terms": {
                "core": core_term,
                "secondary": secondary_term
            },
            **research_data,
            **patent_data,
            **market_data
        }
        
        return combined_data
    
    def scrape_multiple_subfields(
        self,
        subfields: List[Dict],
        save_raw: bool = True
    ) -> List[Dict]:
        """
        Scrape metrics for multiple subfields.
        
        Args:
            subfields: List of subfield definitions with name, core_term, secondary_term.
            save_raw: Whether to save raw signals to JSON file.
            
        Returns:
            List of scraped data dictionaries.
        """
        results = []
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        
        for i, subfield in enumerate(subfields, 1):
            print(f"\n{'='*60}")
            print(f"[Scraper Agent] Subfield {i}/{len(subfields)}")
            print(f"{'='*60}")
            
            try:
                data = self.scrape_subfield(
                    subfield_name=subfield["name"],
                    core_term=subfield["core_term"],
                    secondary_term=subfield["secondary_term"]
                )
                results.append(data)
            except Exception as e:
                print(f"  [ERROR] Failed to scrape {subfield['name']}: {e}")
                # Record N/A for failed subfield
                results.append({
                    "subfield_name": subfield["name"],
                    "error": str(e),
                    "paper_count_3yr": "N/A",
                    "citation_intensity_avg": "N/A",
                    "paper_growth_rate_yoy": "N/A",
                    "patent_count_3yr": "N/A",
                    "npl_citation_rate": "N/A",
                    "corporate_patent_share": "N/A",
                    "so_question_volume": "N/A",
                    "so_question_growth": "N/A",
                    "github_repo_count_3y": "N/A",
                    "github_star_growth": "N/A",
                    "scrape_timestamp": datetime.now(timezone.utc).isoformat()
                })
        
        # Save raw signals if requested
        if save_raw and results:
            filename = f"raw_signals_{timestamp}.json"
            filepath = os.path.join(self.output_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({
                    "metadata": {
                        "generated_at": timestamp,
                        "subfield_count": len(results)
                    },
                    "signals": results
                }, f, indent=2, ensure_ascii=False)
            
            print(f"\n[Scraper Agent] Raw signals saved to: {filepath}")
        
        return results
    
    def load_targets(self, targets_file: str) -> List[Dict]:
        """
        Load subfield targets from JSON file.
        
        Args:
            targets_file: Path to targets.json file.
            
        Returns:
            List of subfield definitions.
        """
        with open(targets_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return data.get("subfields", [])


def main():
    """Example usage of the Scraper Agent."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Gap Mapping Scraper Agent")
    parser.add_argument(
        "--targets", "-t",
        default="targets.json",
        help="Path to targets.json file"
    )
    parser.add_argument(
        "--output", "-o",
        default=".",
        help="Output directory for raw signals"
    )
    parser.add_argument(
        "--semantic-scholar-key",
        help="Semantic Scholar API key (optional)"
    )
    parser.add_argument(
        "--github-token",
        help="GitHub personal access token (optional)"
    )
    
    args = parser.parse_args()
    
    # Initialize agent
    agent = ScraperAgent(
        semantic_scholar_api_key=args.semantic_scholar_key,
        github_token=args.github_token,
        output_dir=args.output
    )
    
    # Load targets
    print(f"[Scraper Agent] Loading targets from: {args.targets}")
    subfields = agent.load_targets(args.targets)
    print(f"[Scraper Agent] Found {len(subfields)} subfield(s) to process")
    
    # Scrape all subfields
    results = agent.scrape_multiple_subfields(subfields)
    
    print(f"\n[Scraper Agent] Scraping complete. Processed {len(results)} subfield(s).")


if __name__ == "__main__":
    main()
