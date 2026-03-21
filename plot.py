import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable
from matplotlib.lines import Line2D

# ============================================================
# 1. CONFIGURATION (easy to modify later)
# ============================================================

CONFIG = {
    # Weighting constants
    "alpha_patents": 0.6,
    "beta_startups": 1.0,
    "epsilon": 1e-6,

    # Bubble scaling
    "max_bubble_size": 2200,
    "min_bubble_size": 250,
    "size_exponent": 1.7,

    # Color meaning:
    # Green = high gap (underserved opportunity)
    # Red   = low gap (already mature)
    "gap_cmap": "RdYlGn",

    # Plot styling
    "figsize": (11, 9),
    "font": "DejaVu Sans",
    "title": "Need vs Research Opportunity Map"
}

# ============================================================
# 2. DATA LOADING (Updated to read CSV)
# ============================================================


def load_data(filepath):
    """
    Load dataset from CSV and set the subfield as the index.
    """
    # thousands=',' tells pandas to ignore commas in numbers like "102,000"
    df = pd.read_csv(filepath, thousands=',')
    
    if "Subfield" in df.columns:
        df.set_index("Subfield", inplace=True)
        
    # Force all columns to be numeric, just in case there are hidden text characters
    df = df.apply(pd.to_numeric, errors='coerce').fillna(0)
    
    return df

# ============================================================
# 3. METRIC COMPUTATION (NEW MODEL)
# ============================================================

def safe_zscore(series):
    """Calculate Z-score, returning 0 if standard deviation is zero."""
    std = series.std(ddof=0)
    if std == 0:
        return pd.Series(0.0, index=series.index)
    return (series - series.mean()) / std

def compute_metrics(df, config):
    """
    Computes variables based on the Need vs Research Opportunity Map framework:
    
    Area A -> Research Intensity (RI)
    Area B -> Science-Industry Linkage (SIL)
    Area C -> Market Demand Score (MDS)
    
    Research Gap (RG) = MDS_z - RI_z  -> Bubble Color
    Translation Gap (TG) = RI_z - SIL_z -> Bubble Size
    """
    df = df.copy()

    # Column mapping based on the exact columns in the CSV template
    area_a = ['Paper Count (3yr)', 'Citation Intensity (3yr avg)', 'Paper Growth Rate (YoY %)']
    # Based on the PDF, SIL depends on NPL and Corporate Share
    area_b_sil = ['NPL Citation Rate (3yr %)', 'Corporate Patent Share (3yr %)'] 
    area_c = ['SO Question Vol (12mo)', 'SO Question Growth (12mo %)', 'GitHub Repo Count (3Y)', 'GitHub Star Growth (12mo %)']

    # 1. Standardize all base variables individually
    for col in area_a + area_b_sil + area_c:
        if col in df.columns:
            df[f"{col}_z"] = safe_zscore(df[col])
        else:
            df[f"{col}_z"] = 0.0

    # 2. Derived Base Scores (sum of z-scores)
    df["MDS_raw"] = df[[f"{c}_z" for c in area_c]].sum(axis=1)
    df["RI_raw"] = df[[f"{c}_z" for c in area_a]].sum(axis=1)
    df["SIL_raw"] = df[[f"{c}_z" for c in area_b_sil]].sum(axis=1)

    # 3. Standardize the derived scores to compute the final mapping gaps
    df["MDS_z"] = safe_zscore(df["MDS_raw"])
    df["RI_z"] = safe_zscore(df["RI_raw"])
    df["SIL_z"] = safe_zscore(df["SIL_raw"])

    # 4. Compute Gaps
    df["RG"] = df["MDS_z"] - df["RI_z"]
    df["TG"] = df["RI_z"] - df["SIL_z"]
    
    # ============================================================
    # 5. Map to Plotting Variables (Do NOT change original Plot Logic)
    # ============================================================
    
    df["Need"] = df["MDS_z"]
    
    # Scale ResearchIntensity so that np.log10(RI + 1) in the plotting function 
    # correctly and safely visualizes the Z-score as a linear transformation.
    df["ResearchIntensity"] = np.exp(df["RI_z"]) * 100
    
    # Bubble Color Maps to Research Gap (RG)
    df["GapNorm"] = df["RG"]
        
    # Bubble Size Maps to Translation Gap (TG).
    # Must be shifted to strictly positive values for size exponent math in plot.
    tg = df["TG"]
    if tg.max() == tg.min():
        df["Opportunity"] = pd.Series(1.0, index=tg.index)
    else:
        df["Opportunity"] = ((tg - tg.min()) / (tg.max() - tg.min())) + 0.1

    return df

# ============================================================
# 4. MAIN SCATTER PLOT FUNCTION (Unchanged)
# ============================================================

def plot_need_vs_research(df, config):
    """
    Scatter Plot Encoding:

    X = Need (demand proxy)
    Y = Research intensity (log)

    Bubble Size = Opportunity
    Bubble Color = Gap Severity (Green = underserved)
    """

    plt.rcParams["font.family"] = config["font"]

    fig, ax = plt.subplots(figsize=config["figsize"])

    # Axes values
    x = df["Need"].to_numpy()
    y = np.log10(df["ResearchIntensity"] + 1).to_numpy()

    # Bubble size scaling (Opportunity)
    opp = df["Opportunity"]
    opp_scaled = (opp / opp.max()) ** config["size_exponent"]

    sizes = (
        config["min_bubble_size"]
        + opp_scaled * (config["max_bubble_size"] - config["min_bubble_size"])
    )

    # Bubble color scaling (Gap Severity)
    gap = df["GapNorm"]
    norm = Normalize(vmin=gap.min(), vmax=gap.max())
    cmap = plt.colormaps[config["gap_cmap"]]
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

    # Labels (MVP: label all)
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

    # ============================================================
    # Quadrant Labels
    # ============================================================

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
    ax.set_title(config["title"], fontsize=15, weight="bold")

    # Colorbar legend (Gap Severity)
    sm = ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])

    cbar = plt.colorbar(sm, ax=ax, fraction=0.035, pad=0.03)
    cbar.set_label("Gap Severity (Red = Under-commercialized, Green = Mature)")


    # ============================================================
    # Bubble Size Legend (Opportunity)
    # ============================================================

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
    plt.show()

# ============================================================
# 5. MAIN EXECUTION (Updated)
# ============================================================

if __name__ == "__main__":

    # Reads directly from your uploaded file
    df = load_data('Market Research Excel Template.csv')
    df = compute_metrics(df, CONFIG)

    print("\nComputed Metrics Preview (New Model Framework):\n")
    print(df[["MDS_z", "RI_z", "SIL_z", "RG", "TG"]])

    plot_need_vs_research(df, CONFIG)