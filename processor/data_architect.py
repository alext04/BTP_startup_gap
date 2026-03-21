"""
Data Architect Agent - Processor Module
Cleans raw signals and formats them into the finalized CSV structure.
"""

import json
import os
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, List, Optional, Union


# Exact column schema as per Market Research Excel Template.csv
CSV_COLUMNS = [
    "Subfield",
    "Paper Count (3yr)",
    "Citation Intensity (3yr avg)",
    "Paper Growth Rate (YoY %)",
    "Patent Count (3yr)",
    "NPL Citation Rate (3yr %)",
    "Corporate Patent Share (3yr %)",
    "SO Question Vol (12mo)",
    "SO Question Growth (12mo %)",
    "GitHub Repo Count (3Y)",
    "GitHub Star Growth (12mo %)"
]


class DataArchitect:
    """
    The Data Architect Agent processes raw signals into the final CSV format.
    
    Responsibilities:
    - Calculate derived metrics (YoY Growth Rates, Citation Intensity averages)
    - Clean and validate numerical data
    - Generate timestamped CSV files matching the template schema
    """
    
    def __init__(self, output_dir: str = ".", logs_dir: str = "logs"):
        """
        Initialize the Data Architect.
        
        Args:
            output_dir: Directory to save processed CSV files.
            logs_dir: Directory to save processing logs.
        """
        self.output_dir = output_dir
        self.logs_dir = logs_dir
        os.makedirs(logs_dir, exist_ok=True)
    
    def _clean_numeric(self, value: Union[str, int, float, None]) -> Union[float, str]:
        """
        Clean numeric values by removing commas and converting to float.
        
        Args:
            value: Raw value that may contain commas or be None.
            
        Returns:
            Cleaned numeric value or "N/A" for invalid data.
        """
        if value is None:
            return "N/A"
        
        if isinstance(value, (int, float)):
            return float(value)
        
        if isinstance(value, str):
            if value.upper() == "N/A":
                return "N/A"
            try:
                # Remove commas and convert
                cleaned = value.replace(",", "").strip()
                return float(cleaned)
            except (ValueError, AttributeError):
                return "N/A"
        
        return "N/A"
    
    def _format_numeric(self, value: Union[float, str], decimals: int = 2) -> Union[str, float]:
        """
        Format numeric values for CSV output.
        
        Args:
            value: Numeric value to format.
            decimals: Number of decimal places.
            
        Returns:
            Formatted value (string with commas for large numbers, float for decimals).
        """
        if value == "N/A":
            return "N/A"
        
        try:
            num_val = float(value)
            
            # For large integers (> 1000), format with commas
            if num_val >= 1000 and num_val == int(num_val):
                return f"{int(num_val):,}"
            
            # For decimals, round to specified places
            return round(num_val, decimals)
        
        except (ValueError, TypeError):
            return "N/A"
    
    def transform_raw_to_csv_row(self, raw_data: Dict) -> Dict:
        """
        Transform raw scraped data into a CSV row format.
        
        Args:
            raw_data: Dictionary containing scraped metrics.
            
        Returns:
            Dictionary with keys matching CSV_COLUMNS.
        """
        # Map raw data keys to CSV columns
        row = {
            "Subfield": raw_data.get("subfield_name", "Unknown"),
            "Paper Count (3yr)": self._clean_numeric(raw_data.get("paper_count_3yr")),
            "Citation Intensity (3yr avg)": self._clean_numeric(raw_data.get("citation_intensity_avg")),
            "Paper Growth Rate (YoY %)": self._clean_numeric(raw_data.get("paper_growth_rate_yoy")),
            "Patent Count (3yr)": self._clean_numeric(raw_data.get("patent_count_3yr")),
            "NPL Citation Rate (3yr %)": self._clean_numeric(raw_data.get("npl_citation_rate")),
            "Corporate Patent Share (3yr %)": self._clean_numeric(raw_data.get("corporate_patent_share")),
            "SO Question Vol (12mo)": self._clean_numeric(raw_data.get("so_question_volume")),
            "SO Question Growth (12mo %)": self._clean_numeric(raw_data.get("so_question_growth")),
            "GitHub Repo Count (3Y)": self._clean_numeric(raw_data.get("github_repo_count_3y")),
            "GitHub Star Growth (12mo %)": self._clean_numeric(raw_data.get("github_star_growth"))
        }
        
        return row
    
    def process_raw_signals(
        self,
        raw_signals_file: str,
        save_individual: bool = True
    ) -> pd.DataFrame:
        """
        Process raw signals JSON file into CSV format.
        
        Args:
            raw_signals_file: Path to raw_signals_*.json file.
            save_individual: Whether to save individual subfield CSVs.
            
        Returns:
            DataFrame with all processed data.
        """
        # Load raw signals
        with open(raw_signals_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        signals = data.get("signals", [])
        metadata = data.get("metadata", {})
        
        print(f"\n[Data Architect] Processing {len(signals)} subfield(s) from raw signals")
        
        # Transform each subfield
        rows = []
        for signal in signals:
            row = self.transform_raw_to_csv_row(signal)
            rows.append(row)
            
            # Log processing details
            self._log_processing(signal.get("subfield_name", "Unknown"), row)
        
        # Create DataFrame
        df = pd.DataFrame(rows, columns=CSV_COLUMNS)
        
        # Generate timestamp for output files
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        
        # Save combined CSV
        combined_filename = f"research_gap_data_{timestamp}.csv"
        combined_filepath = os.path.join(self.output_dir, combined_filename)
        
        # Format large numbers with commas for CSV output
        df_to_save = df.copy()
        for col in df_to_save.columns:
            if col != "Subfield":
                df_to_save[col] = df_to_save[col].apply(
                    lambda x: f"{int(x):,}" if isinstance(x, (int, float)) and x >= 1000 and x == int(x) else x
                )
        
        df_to_save.to_csv(combined_filepath, index=False)
        print(f"[Data Architect] Combined CSV saved to: {combined_filepath}")
        
        # Save individual subfield CSVs if requested
        if save_individual:
            for _, row in df.iterrows():
                subfield_name = row["Subfield"].replace(" ", "_").replace("/", "_")
                individual_filename = f"{subfield_name}_{timestamp}.csv"
                individual_filepath = os.path.join(self.output_dir, individual_filename)
                
                row_df = pd.DataFrame([row])
                row_df.to_csv(individual_filepath, index=False)
        
        return df
    
    def process_direct_results(
        self,
        scraped_results: List[Dict],
        subfield_override: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Process scraped results directly (without intermediate JSON file).
        
        Args:
            scraped_results: List of scraped data dictionaries.
            subfield_override: Optional override for subfield name (for single subfield).
            
        Returns:
            DataFrame with processed data.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        
        rows = []
        for result in scraped_results:
            row = self.transform_raw_to_csv_row(result)
            rows.append(row)
            self._log_processing(result.get("subfield_name", "Unknown"), row)
        
        df = pd.DataFrame(rows, columns=CSV_COLUMNS)
        
        # Save CSV
        filename = f"research_gap_data_{timestamp}.csv"
        filepath = os.path.join(self.output_dir, filename)
        
        # Format for CSV output
        df_to_save = df.copy()
        for col in df_to_save.columns:
            if col != "Subfield":
                df_to_save[col] = df_to_save[col].apply(
                    lambda x: f"{int(x):,}" if isinstance(x, (int, float)) and x >= 1000 and x == int(x) else x
                )
        
        df_to_save.to_csv(filepath, index=False)
        print(f"\n[Data Architect] CSV saved to: {filepath}")
        
        return df
    
    def _log_processing(self, subfield_name: str, row: Dict):
        """
        Log processing details for debugging.
        
        Args:
            subfield_name: Name of the subfield.
            row: Processed row data.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        log_file = os.path.join(self.logs_dir, f"processor_{timestamp}.log")
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"Subfield: {subfield_name}\n")
            f.write(f"Timestamp: {datetime.now(timezone.utc).isoformat()}\n")
            f.write(f"Processed Data:\n")
            for key, value in row.items():
                f.write(f"  {key}: {value}\n")
            
            # Check for N/A values
            na_fields = [k for k, v in row.items() if v == "N/A"]
            if na_fields:
                f.write(f"WARNING: N/A values in fields: {na_fields}\n")
    
    def validate_csv_schema(self, df: pd.DataFrame) -> bool:
        """
        Validate that DataFrame matches the expected schema.
        
        Args:
            df: DataFrame to validate.
            
        Returns:
            True if schema matches, False otherwise.
        """
        missing_cols = set(CSV_COLUMNS) - set(df.columns)
        extra_cols = set(df.columns) - set(CSV_COLUMNS)
        
        if missing_cols:
            print(f"[Data Architect] WARNING: Missing columns: {missing_cols}")
            return False
        
        if extra_cols:
            print(f"[Data Architect] WARNING: Extra columns: {extra_cols}")
        
        return True


def main():
    """Example usage of the Data Architect."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Gap Mapping Data Architect")
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Path to raw_signals_*.json file"
    )
    parser.add_argument(
        "--output", "-o",
        default=".",
        help="Output directory for processed CSV"
    )
    parser.add_argument(
        "--logs",
        default="logs",
        help="Directory for processing logs"
    )
    
    args = parser.parse_args()
    
    # Initialize architect
    architect = DataArchitect(output_dir=args.output, logs_dir=args.logs)
    
    # Process raw signals
    df = architect.process_raw_signals(args.input)
    
    print(f"\n[Data Architect] Processing complete. Generated {len(df)} row(s).")


if __name__ == "__main__":
    main()
