import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import os
import pandas as pd
import plotly.express as px
import plotly.io as pio
import plotly.graph_objects as go
import numpy as np


def generate_rejection_trend_chart(foundry, defect_type, sql_data):
    """Generates an enhanced bar chart using Plotly from SQL data."""

    if not sql_data:
        print(f"No data available to generate chart for {defect_type} in {foundry}.")
        return None

    # Convert SQL data (list of dicts) to DataFrame
    df = pd.DataFrame(sql_data)

    if "month" not in df.columns or "rejection_percentage" not in df.columns:
        print("Invalid data format for charting.")
        return None

    df["month"] = pd.to_datetime(df["month"], format="%b-%Y", errors="coerce")
    df = df.dropna(subset=["month"])
    df = df.sort_values("month")
    df["month"] = df["month"].dt.strftime("%b-%Y")

    fig = px.bar(
        df,
        x="month",
        y="rejection_percentage",
        text="rejection_percentage",
        hover_data=["month", "rejection_percentage"],
        labels={"rejection_percentage": "Percentage of Total Production"},
        title=f"Sand Defects * Rejection (%) over Period [ {defect_type} ]",
        color="rejection_percentage",
        color_continuous_scale="Reds"
    )

    fig.update_xaxes(title_text="Month", tickangle=-45)
    fig.update_yaxes(title_text="Rejection %", gridcolor="lightgrey")
    fig.update_traces(texttemplate='%{text:.2f}%', textposition="outside")
    fig.update_layout(margin=dict(l=40, r=40, t=60, b=80))
    # fig.show()

    chart_dir = os.path.join("results", foundry, "charts")
    os.makedirs(chart_dir, exist_ok=True)

    chart_path = os.path.join(chart_dir, f"monthly_rejection_rate_{defect_type}.jpeg").replace("\\", "/")
    pio.write_image(fig, chart_path, format="jpeg", scale=3, width=1000, height=600)

    return chart_path



def generate_summary_chart(foundry, defect_type, summary_data):
    """
    Generates a summary bar chart with Plotly showing absolute change (%) for parameters.
    
    Args:
        foundry (str): Foundry name.
        defect_type (str): Type of defect.
        summary_data (list of dicts): [{"parameter": "Moisture (%)", "absolute_change": 13.71}, ...]

    Returns:
        str: Path to saved summary chart image.
    """
    if not summary_data:
        print(f" No summary data available for {defect_type} in {foundry}.")
        return None

    df = pd.DataFrame(summary_data)


    df = df.dropna(subset=["absolute_change"])

    if df.empty:
        print(f" All values in `absolute_change` were None for {defect_type} in {foundry}.")
        return None

    df = df.sort_values(by="absolute_change", ascending=False)

    fig = px.bar(
        df,
        x="parameter",
        y="absolute_change",
        text="absolute_change",
        labels={"parameter": "Parameters", "absolute_change": "Absolute Change (%)"},
        title=f"Summary Table: Absolute Change (%) - {defect_type}",
        color="absolute_change",
        color_continuous_scale="Reds"
    )

    fig.update_traces(texttemplate='%{text:.2f}%', textposition="outside")
    fig.update_layout(
        xaxis_tickangle=-30,
        title_font=dict(size=18, family="Arial Black"),
        margin=dict(l=40, r=20, t=80, b=80)
    )
    # fig.show()

    chart_dir = f"results/{foundry}/"
    os.makedirs(chart_dir, exist_ok=True)
    chart_path = os.path.join(chart_dir, f"summary_table_plot_{defect_type}.jpeg").replace("\\", "/")
    pio.write_image(fig, chart_path, format="jpeg", scale=3, width=1000, height=600)

    return chart_path



# def generate_summary_plots(data_for_analysis_dict, foundry, config_file, opt_bin=None):
#     """
#     Generates and saves Distribution, Box, and Correlation plots using Plotly.
#     """
#     defect_type = config_file["defect_for_analysis"]
#     features = config_file["Defectwise sand properties based on fishbone"].get(defect_type, [])
#     output_dir = f"backend/results/{foundry}/temp/"
#     os.makedirs(output_dir, exist_ok=True)

#     for label, df in data_for_analysis_dict.items():
#         for feature in features:
#             if feature in df.columns:
                
#                 fig_dist = px.histogram(
#                     df,
#                     x=feature,
#                     nbins=opt_bin.get(feature, 20) if opt_bin else 20,
#                     marginal="box",
#                     opacity=0.75,
#                     title=f"{label} - Distribution Plot for {feature}",
#                     color_discrete_sequence=["#5DADE2"]
#                 )
#                 fig_dist.update_layout(bargap=0.1)
#                 dist_path = os.path.join(output_dir, f"{label}_Distribution plot of {feature}.jpeg")
#                 pio.write_image(fig_dist, dist_path, format="jpeg", scale=3, width=1000, height=600)
#                 print(f"Saved: {dist_path}")

#                 fig_box = px.box(
#                     df,
#                     y=feature,
#                     title=f"{label} - Box Plot for {feature}",
#                     color_discrete_sequence=["#2E86C1"]
#                 )
#                 box_path = os.path.join(output_dir, f"{label}_Box plot of {feature}.jpeg")
#                 pio.write_image(fig_box, box_path, format="jpeg", scale=3, width=800, height=500)
#                 print(f"Saved: {box_path}")

#         # Correlation Heatmap
#         feature_subset = [f for f in features if f in df.columns]
#         if len(feature_subset) >= 2:
#             corr = df[feature_subset].corr().round(2)
#             fig_corr = go.Figure(
#                 data=go.Heatmap(
#                     z=corr.values,
#                     x=corr.columns,
#                     y=corr.columns,
#                     colorscale="RdBu",
#                     zmin=-1,
#                     zmax=1,
#                     colorbar=dict(title="Correlation"),
#                     hoverongaps=False
#                 )
#             )
#             fig_corr.update_layout(
#                 title=f"{label} - Correlation Matrix",
#                 xaxis_nticks=len(corr.columns),
#                 yaxis_nticks=len(corr.columns)
#             )
#             corr_path = os.path.join(output_dir, f"{label}_Correlation plot of {defect_type}.jpeg")
#             pio.write_image(fig_corr, corr_path, format="jpeg", scale=3, width=1000, height=700)
#             print(f"Saved: {corr_path}")
