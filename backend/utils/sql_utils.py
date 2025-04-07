from database import connect_db
engine = connect_db()
import os
import json
import calendar
import pandas as pd
from sqlalchemy import text
from utils.plot_generator import generate_summary_chart
from flask import jsonify
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

def fetch_sql_data(foundry, defect_type, months=None, year=None):
    base_query = """
        SELECT month_year, rejection_percentage 
        FROM rejection_analysis
        WHERE foundry_name = :foundry AND defect_type = :defect_type
    """
    query_params = {"foundry": foundry, "defect_type": defect_type}

    if months and year:
        month_years = [f"{m}-{year}" for m in months]
        base_query += " AND month_year IN ({})".format(
            ", ".join([f":month_{i}" for i in range(len(month_years))])
        )
        for i, my in enumerate(month_years):
            query_params[f"month_{i}"] = my

    elif months and not year:
        base_query += " AND (" + " OR ".join(
            [f"month_year LIKE :month_{i}" for i in range(len(months))]
        ) + ")"
        for i, m in enumerate(months):
            query_params[f"month_{i}"] = f"{m}-%"

    elif year and not months:
        month_years = [f"{calendar.month_abbr[i]}-{year}" for i in range(1, 13)]
        base_query += " AND month_year IN ({})".format(
            ", ".join([f":month_{i}" for i in range(len(month_years))])
        )
        for i, my in enumerate(month_years):
            query_params[f"month_{i}"] = my
    else:
        base_query=base_query

    base_query += " ORDER BY month_year DESC"

    with engine.connect() as conn:
        result = conn.execute(text(base_query), query_params).fetchall()

    return [{"month": row[0], "rejection_percentage": row[1]} for row in result] if result else None



def extract_chart_intent(user_query):
    chart_types = ["distribution", "box", "correlation"]
    known_parameters = {
        "moisture": "moisture",
        "moisture content": "moisture",
        "active clay": "active_clay",
        "compactability": "compactibility",
        "shatter index": "shatter_index",
        "gcs": "gcs",
        "gfn afs": "gfn_afs",
        "permeability": "permeability",
        "loi": "loi",
        "volatile matter": "volatile_matter",
        "split strength": "split_strength",
        "wet tensile strength": "wet_tensile_strength",
        "p h value": "pH_value",
        "ph": "pH_value",
    }

    query = user_query.lower()
    matched_charts = [ct.capitalize() for ct in chart_types if ct in query]
    matched_params = [known_parameters[k] for k in known_parameters if k in query]

    # If user says "show all three charts", assume all chart types
    if "all charts" in query or "all three charts" in query:
        matched_charts = ["Distribution", "Box", "Correlation"]

    # If user says "for loi", but doesn't specify chart type, assume all
    if matched_params and not matched_charts:
        matched_charts = ["Distribution", "Box", "Correlation"]

    return [(chart, param) for chart in matched_charts for param in matched_params]




def fetch_summary_data(foundry, defect_type):
    """Fetches summary data (absolute change) from the database for a given foundry & defect type."""
    response_messages = []

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT parameter, absolute_change 
            FROM summary_table
            WHERE foundry_name = :foundry_name AND defect_type = :defect_type
            ORDER BY absolute_change DESC;
        """), {"foundry_name": foundry, "defect_type": defect_type}).fetchall()

    if result:
        summary_data = [{"parameter": row[0], "absolute_change": row[1]} for row in result]
        
        summary_chart_path = generate_summary_chart(foundry, defect_type, summary_data)
        summary_chart_url = f"http://127.0.0.1:5000/{summary_chart_path}" if summary_chart_path else None

  
        response_messages.append(f"Summary data for `{defect_type}` in `{foundry}`:")
        table_data = {
            "columns": ["Parameter", "Absolute Change (%)"],
            "data": summary_data
        }
    else:
        response_messages.append(f"No summary data available for `{defect_type}` in `{foundry}`.")
        table_data = None
        summary_chart_url = None

    return {
        "messages": response_messages,
        "summary_table": table_data,
        "summary_chart": summary_chart_url if summary_chart_url else "No Summary Chart Available"
    }

