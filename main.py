#!/usr/bin/env python3
"""
The Orchestrator - Main CLI Entry Point
Sequences the modular pipeline: Scraper -> Data Architect -> Visualization
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.scraper import ScraperAgent
from processor.data_architect import DataArchitect
from visualizer.plot_engine import VisualizationAgent


class Orchestrator:
    """
    The Orchestrator coordinates the complete Gap Mapping pipeline.
    
    Pipeline Sequence:
    1. Scraper Agent: Collect data from all sources
    2. Data Architect: Process and format into CSV
    3. Visualization Agent: Generate Need vs Research Opportunity Map
    
    Features:
    - Accepts arbitrary number of subfields from targets.json
    - Error resilience: continues on individual failures
    - Detailed logging per subfield
    """
    
    def __init__(
        self,
        output_dir: str = ".",
        logs_dir: str = "logs",
        semantic_scholar_api_key: Optional[str] = None,
        github_token: Optional[str] = None
    ):
        """
        Initialize the Orchestrator.
        
        Args:
            output_dir: Directory for all output files.
            logs_dir: Directory for log files.
            semantic_scholar_api_key: Optional API key for Semantic Scholar.
            github_token: Optional GitHub token for higher rate limits.
        """
        self.output_dir = output_dir
        self.logs_dir = logs_dir
        
        # Create directories
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(logs_dir, exist_ok=True)
        
        # Setup logging
        self._setup_logging()
        
        # Initialize agents
        self.scraper = ScraperAgent(
            semantic_scholar_api_key=semantic_scholar_api_key,
            github_token=github_token,
            output_dir=output_dir
        )
        self.architect = DataArchitect(output_dir=output_dir, logs_dir=logs_dir)
        self.visualizer = VisualizationAgent(output_dir=output_dir, logs_dir=logs_dir)
        
        self.logger.info(f"Orchestrator initialized. Output dir: {output_dir}")
    
    def _setup_logging(self):
        """Setup logging configuration."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(self.logs_dir, f"orchestrator_{timestamp}.log")
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Logging to: {log_file}")
    
    def run_pipeline(
        self,
        targets_file: str,
        skip_scrape: bool = False,
        skip_visualization: bool = False,
        raw_signals_file: Optional[str] = None
    ) -> Dict:
        """
        Run the complete Gap Mapping pipeline.
        
        Args:
            targets_file: Path to targets.json file.
            skip_scrape: If True, skip scraping and use existing raw signals.
            skip_visualization: If True, skip visualization step.
            raw_signals_file: Path to existing raw signals (if skip_scrape=True).
            
        Returns:
            Dictionary with pipeline results and output file paths.
        """
        self.logger.info("=" * 60)
        self.logger.info("Starting Gap Mapping Pipeline")
        self.logger.info("=" * 60)
        
        pipeline_start = datetime.now(timezone.utc)
        results = {
            "pipeline_start": pipeline_start.isoformat(),
            "subfields_processed": 0,
            "errors": [],
            "outputs": {}
        }
        
        # Load targets
        self.logger.info(f"Loading targets from: {targets_file}")
        subfields = self._load_targets(targets_file)
        results["subfields_processed"] = len(subfields)
        self.logger.info(f"Found {len(subfields)} subfield(s) to process")
        
        # Step 1: Scrape
        if not skip_scrape:
            self.logger.info("\n" + "=" * 60)
            self.logger.info("STEP 1: Scraping Data Sources")
            self.logger.info("=" * 60)
            
            try:
                scraped_data = self.scraper.scrape_multiple_subfields(
                    subfields,
                    save_raw=True
                )
                results["outputs"]["raw_signals"] = "raw_signals_*.json (saved)"
            except Exception as e:
                self.logger.error(f"Scraping failed: {e}")
                results["errors"].append({"step": "scraping", "error": str(e)})
                scraped_data = None
        else:
            self.logger.info(f"Skipping scrape, using: {raw_signals_file}")
            with open(raw_signals_file, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
                scraped_data = raw_data.get("signals", [])
        
        if not scraped_data:
            self.logger.error("No data to process. Exiting.")
            return results
        
        # Step 2: Process
        self.logger.info("\n" + "=" * 60)
        self.logger.info("STEP 2: Processing Data (Data Architect)")
        self.logger.info("=" * 60)
        
        try:
            processed_df = self.architect.process_direct_results(scraped_data)
            results["outputs"]["processed_csv"] = "research_gap_data_*.csv (saved)"
            self.logger.info(f"Processed {len(processed_df)} subfield(s)")
        except Exception as e:
            self.logger.error(f"Processing failed: {e}")
            results["errors"].append({"step": "processing", "error": str(e)})
            return results
        
        # Step 3: Visualize
        if not skip_visualization:
            self.logger.info("\n" + "=" * 60)
            self.logger.info("STEP 3: Generating Visualization")
            self.logger.info("=" * 60)
            
            # Find the latest processed CSV
            csv_files = [f for f in os.listdir(self.output_dir) 
                        if f.startswith("research_gap_data_") and f.endswith(".csv")]
            
            if csv_files:
                latest_csv = sorted(csv_files)[-1]
                csv_path = os.path.join(self.output_dir, latest_csv)
                
                try:
                    viz_path = self.visualizer.generate_visualization(csv_path)
                    results["outputs"]["visualization"] = viz_path
                except Exception as e:
                    self.logger.error(f"Visualization failed: {e}")
                    results["errors"].append({"step": "visualization", "error": str(e)})
            else:
                self.logger.error("No processed CSV found for visualization")
                results["errors"].append({
                    "step": "visualization",
                    "error": "No processed CSV found"
                })
        
        # Pipeline complete
        pipeline_end = datetime.now(timezone.utc)
        duration = (pipeline_end - pipeline_start).total_seconds()
        
        results["pipeline_end"] = pipeline_end.isoformat()
        results["duration_seconds"] = duration
        
        self.logger.info("\n" + "=" * 60)
        self.logger.info("Pipeline Complete")
        self.logger.info("=" * 60)
        self.logger.info(f"Duration: {duration:.2f} seconds")
        self.logger.info(f"Subfields processed: {len(subfields)}")
        self.logger.info(f"Errors: {len(results['errors'])}")
        
        if results["errors"]:
            for err in results["errors"]:
                self.logger.warning(f"  - {err['step']}: {err['error']}")
        
        return results
    
    def _load_targets(self, targets_file: str) -> List[Dict]:
        """
        Load subfield targets from JSON file.
        
        Args:
            targets_file: Path to targets.json.
            
        Returns:
            List of subfield definitions.
        """
        with open(targets_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        subfields = data.get("subfields", [])
        
        # Validate subfield structure
        for i, subfield in enumerate(subfields):
            if "name" not in subfield:
                raise ValueError(f"Subfield {i} missing 'name' field")
            if "core_term" not in subfield:
                raise ValueError(f"Subfield {i} missing 'core_term' field")
            if "secondary_term" not in subfield:
                raise ValueError(f"Subfield {i} missing 'secondary_term' field")
        
        return subfields


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Gap Mapping Pipeline Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py -t targets.json
  python main.py -t targets.json --skip-visualize
  python main.py -t targets.json --skip-scrape --raw-signals raw_signals_20250321_1430.json
  python main.py -t targets.json --output ./results --logs ./my_logs
        """
    )
    
    parser.add_argument(
        "--targets", "-t",
        default="targets.json",
        help="Path to targets.json file (default: targets.json)"
    )
    parser.add_argument(
        "--output", "-o",
        default=".",
        help="Output directory for all files (default: current directory)"
    )
    parser.add_argument(
        "--logs",
        default="logs",
        help="Directory for log files (default: logs)"
    )
    parser.add_argument(
        "--semantic-scholar-key",
        help="Semantic Scholar API key (optional)"
    )
    parser.add_argument(
        "--github-token",
        help="GitHub personal access token (optional)"
    )
    parser.add_argument(
        "--skip-scrape",
        action="store_true",
        help="Skip scraping step (use existing raw signals)"
    )
    parser.add_argument(
        "--skip-visualize",
        action="store_true",
        help="Skip visualization step"
    )
    parser.add_argument(
        "--raw-signals",
        help="Path to existing raw signals JSON (use with --skip-scrape)"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.skip_scrape and not args.raw_signals:
        parser.error("--skip-scrape requires --raw-signals")
    
    if not os.path.exists(args.targets):
        parser.error(f"Targets file not found: {args.targets}")
    
    # Initialize and run orchestrator
    orchestrator = Orchestrator(
        output_dir=args.output,
        logs_dir=args.logs,
        semantic_scholar_api_key=args.semantic_scholar_key,
        github_token=args.github_token
    )
    
    results = orchestrator.run_pipeline(
        targets_file=args.targets,
        skip_scrape=args.skip_scrape,
        skip_visualization=args.skip_visualize,
        raw_signals_file=args.raw_signals
    )
    
    # Exit with error code if pipeline had errors
    if results["errors"]:
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
