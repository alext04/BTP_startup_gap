"""
Visualization Agent - Plot Engine
Transforms processed CSV data into the "Need vs Research Opportunity Map".
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable
from matplotlib.lines import Line2D
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple


# Configuration matching plot.py
CONFIG = {
    # Weighting constants
    "alpha_patents": 0.6,
    "beta_startups": 1.0,
    "epsilon": 1e-6,

    # Bubble scaling
    "max_bubble_size": 2200,
    "min_bubble_size": 250,
    "size_exponent": 1.7,

    # Color meaning: Green = high gap (underserved), Red = low gap (mature)
    "gap_cmap": "RdYlGn",

    # Plot styling
    "figsize": (11, 9),
    "font": "DejaVu Sans",
    "title": "Need vs Research Opportunity Map"
}


class VisualizationAgent:
    """
    The Visualization Agent transforms processed CSV data into visualizations.
    
    Responsibilities:
    - Load timestamped CSV files
    - Compute Z-scores (RG and TG) for bubble color and size
    - Generate the "Need vs Research Opportunity Map"
    - Save plots as PNG/PDF with matching timestamps
    """
    
    def __init__(
        self,
        output_dir: str = ".",
        logs_dir: str = "logs",
        config: Optional[Dict] = None
    ):
        """
        Initialize the Visualization Agent.
        
        Args:
            output_dir: Directory to save visualization files.
            logs_dir: Directory to save processing logs.
            config: Optional configuration override.
        """
        self.output_dir = output_dir
        self.logs_dir = logs_dir
        self.config = {**CONFIG, **(config or {})}
        os.makedirs(logs_dir, exist_ok=True)
    
    @staticmethod
    def safe_zscore(series: pd.Series) -> pd.Series:
        """
        Calculate Z-score, returning 0 if standard deviation is zero.
        
        Args:
            series: Pandas Series to standardize.
            
        Returns:
            Z-score normalized series.
        """
        std = series.std(ddof=0)
        if std == 0:
            return pd.Series(0.0, index=series.index)
        return (series - series.mean()) / std
    
    def compute_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute variables based on the Need vs Research Opportunity Map framework.
        
        Area A -> Research Intensity (RI)
        Area B -> Science-Industry Linkage (SIL)
        Area C -> Market Demand Score (MDS)
        
        Research Gap (RG) = MDS_z - RI_z  -> Bubble Color
        Translation Gap (TG) = RI_z - SIL_z -> Bubble Size
        
        Args:
            df: DataFrame with raw metrics (columns from CSV template).
            
        Returns:
            DataFrame with computed metrics added.
        """
        df = df.copy()
        
        # Column mapping based on CSV template
        area_a = [
            'Paper Count (3yr)',
            'Citation Intensity (3yr avg)',
            'Paper Growth Rate (YoY %)'
        ]
        area_b_sil = [
            'NPL Citation Rate (3yr %)',
            'Corporate Patent Share (3yr %)'
        ]
        area_c = [
            'SO Question Vol (12mo)',
            'SO Question Growth (12mo %)',
            'GitHub Repo Count (3Y)',
            'GitHub Star Growth (12mo %)'
        ]
        
        # 1. Standardize all base variables individually
        for col in area_a + area_b_sil + area_c:
            if col in df.columns:
                # Handle N/A values
                series = pd.to_numeric(df[col], errors='coerce').fillna(0)
                df[f"{col}_z"] = self.safe_zscore(series)
            else:
                df[f"{col}_z"] = 0.0
        
        # 2. Derived Base Scores (sum of z-scores)
        df["MDS_raw"] = df[[f"{c}_z" for c in area_c]].sum(axis=1)
        df["RI_raw"] = df[[f"{c}_z" for c in area_a]].sum(axis=1)
        df["SIL_raw"] = df[[f"{c}_z" for c in area_b_sil]].sum(axis=1)
        
        # 3. Standardize the derived scores
        df["MDS_z"] = self.safe_zscore(df["MDS_raw"])
        df["RI_z"] = self.safe_zscore(df["RI_raw"])
        df["SIL_z"] = self.safe_zscore(df["SIL_raw"])
        
        # 4. Compute Gaps
        df["RG"] = df["MDS_z"] - df["RI_z"]
        df["TG"] = df["RI_z"] - df["SIL_z"]
        
        # 5. Map to Plotting Variables
        df["Need"] = df["MDS_z"]
        
        # Scale ResearchIntensity so that np.log10(RI + 1) works correctly
        df["ResearchIntensity"] = np.exp(df["RI_z"]) * 100
        
        # Bubble Color Maps to Research Gap (RG)
        df["GapNorm"] = df["RG"]
        
        # Bubble Size Maps to Translation Gap (TG)
        tg = df["TG"]
        if tg.max() == tg.min():
            df["Opportunity"] = pd.Series(1.0, index=tg.index)
        else:
            df["Opportunity"] = ((tg - tg.min()) / (tg.max() - tg.min())) + 0.1
        
        return df
    
    def plot_need_vs_research(
        self,
        df: pd.DataFrame,
        save_path: Optional[str] = None,
        show_plot: bool = False
    ) -> Tuple[plt.Figure, plt.Axes]:
        """
        Create the Need vs Research Opportunity Map scatter plot.
        
        Encoding:
        - X = Need (demand proxy)
        - Y = Research intensity (log)
        - Bubble Size = Opportunity
        - Bubble Color = Gap Severity (Green = underserved)
        
        Args:
            df: DataFrame with computed metrics (from compute_metrics).
            save_path: Optional path to save the figure.
            show_plot: Whether to display the plot.
            
        Returns:
            Figure and Axes objects.
        """
        plt.rcParams["font.family"] = self.config["font"]
        
        fig, ax = plt.subplots(figsize=self.config["figsize"])
        
        # Axes values
        x = df["Need"].to_numpy()
        y = np.log10(df["ResearchIntensity"] + 1).to_numpy()
        
        # Bubble size scaling (Opportunity)
        opp = df["Opportunity"]
        opp_scaled = (opp / opp.max()) ** self.config["size_exponent"]
        
        sizes = (
            self.config["min_bubble_size"]
            + opp_scaled * (self.config["max_bubble_size"] - self.config["min_bubble_size"])
        )
        
        # Bubble color scaling (Gap Severity)
        gap = df["GapNorm"]
        norm = Normalize(vmin=gap.min(), vmax=gap.max())
        cmap = plt.colormaps[self.config["gap_cmap"]]
        colors = cmap(norm(gap))
        
        # Scatter plot
        ax.scatter(
            x, y,
            s=sizes,
            c=colors,
            edgecolors="black",
            linewidths=0.6,
            alpha=0.9
        )
        
        # Labels (label all subfields)
        for i, label in enumerate(df.index):
            ax.text(
                x[i], y[i],
                label,
                fontsize=9,
                ha="center",
                va="center"
            )
        
        # Quadrant guide lines (median split)
        x_med = np.median(x)
        y_med = np.median(y)
        
        ax.axvline(x_med, linestyle="--", linewidth=1, color="gray")
        ax.axhline(y_med, linestyle="--", linewidth=1, color="gray")
        
        # Quadrant Labels
        ax.text(
            x_med + 0.02, y_med + 0.15,
            "High Need\nHigh Research",
            fontsize=10, weight="bold", color="black"
        )
        
        ax.text(
            x_med - 0.28, y_med + 0.15,
            "Low Need\nHigh Research",
            fontsize=10, weight="bold", color="black"
        )
        
        ax.text(
            x_med + 0.02, y_med - 0.25,
            "High Need\nLow Research",
            fontsize=10, weight="bold", color="black"
        )
        
        ax.text(
            x_med - 0.28, y_med - 0.25,
            "Low Need\nLow Research",
            fontsize=10, weight="bold", color="black"
        )
        
        # Axis labels + title
        ax.set_xlabel("Need Score (Demand Proxy)")
        ax.set_ylabel("Research Intensity (log-scaled)")
        ax.set_title(self.config["title"], fontsize=15, weight="bold")
        
        # Colorbar legend (Gap Severity)
        sm = ScalarMappable(norm=norm, cmap=cmap)
        sm.set_array([])
        
        cbar = plt.colorbar(sm, ax=ax, fraction=0.035, pad=0.03)
        cbar.set_label("Gap Severity (Red = Under-commercialized, Green = Mature)")
        
        # Bubble Size Legend
        legend_elements = [
            Line2D(
                [0], [0],
                marker="o",
                color="w",
                label="Bubble Size = Opportunity",
                markerfacecolor="gray",
                markersize=10
            )
        ]
        
        ax.legend(
            handles=legend_elements,
            loc="lower right",
            frameon=False
        )
        
        # Clean infographic styling
        ax.tick_params(left=False, bottom=False)
        for spine in ax.spines.values():
            spine.set_visible(False)
        
        plt.tight_layout()
        
        # Save if path provided
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"[Visualization Agent] Plot saved to: {save_path}")
        
        if show_plot:
            plt.show()
        
        return fig, ax
    
    def generate_visualization(
        self,
        csv_file: str,
        output_format: str = "png"
    ) -> str:
        """
        Generate visualization from a processed CSV file.
        
        Args:
            csv_file: Path to processed CSV file.
            output_format: Output format ('png' or 'pdf').
            
        Returns:
            Path to saved visualization file.
        """
        print(f"\n[Visualization Agent] Loading CSV: {csv_file}")
        
        # Load CSV
        df = pd.read_csv(csv_file, thousands=',')
        
        if "Subfield" in df.columns:
            df.set_index("Subfield", inplace=True)
        
        # Force all columns to be numeric
        df = df.apply(lambda col: pd.to_numeric(col, errors='coerce')).fillna(0)
        
        # Compute metrics
        df = self.compute_metrics(df)
        
        # Log computed metrics
        self._log_metrics(df)
        
        # Generate timestamp for output
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        
        # Determine output path
        base_name = os.path.splitext(os.path.basename(csv_file))[0]
        output_filename = f"{base_name}_visualization.{output_format}"
        output_path = os.path.join(self.output_dir, output_filename)
        
        # Generate plot
        self.plot_need_vs_research(df, save_path=output_path)
        
        return output_path
    
    def _log_metrics(self, df: pd.DataFrame):
        """Log computed metrics for debugging."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        log_file = os.path.join(self.logs_dir, f"visualizer_{timestamp}.log")
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"Timestamp: {datetime.now(timezone.utc).isoformat()}\n")
            f.write(f"Subfields: {len(df)}\n")
            f.write(f"\nComputed Metrics Summary:\n")
            f.write(df[["MDS_z", "RI_z", "SIL_z", "RG", "TG"]].to_string())
            f.write(f"\n")


def main():
    """Example usage of the Visualization Agent."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Gap Mapping Visualization Agent")
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Path to processed CSV file"
    )
    parser.add_argument(
        "--output", "-o",
        default=".",
        help="Output directory for visualization"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["png", "pdf"],
        default="png",
        help="Output format (png or pdf)"
    )
    parser.add_argument(
        "--logs",
        default="logs",
        help="Directory for processing logs"
    )
    
    args = parser.parse_args()
    
    # Initialize agent
    agent = VisualizationAgent(output_dir=args.output, logs_dir=args.logs)
    
    # Generate visualization
    output_path = agent.generate_visualization(args.input, args.format)
    
    print(f"\n[Visualization Agent] Visualization complete: {output_path}")


if __name__ == "__main__":
    main()
