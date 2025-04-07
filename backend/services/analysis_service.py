import os
import json
import requests
import pandas as pd
from sqlalchemy import text
from database import connect_db

engine = connect_db()

def run_analysis(foundry, endpoint="/analyze"):
    """
    Calls the analysis API (analyze/running/refcomp), extracts chart and summary details.
    """
    base_url = "http://127.0.0.1:5000"
    response = requests.post(f"{base_url}{endpoint}", json={"foundry": foundry})
    
    if response.status_code != 200:
        return {
            "error": True,
            "message": f"Failed to run analysis: {response.json().get('error', '')}"
        }

    # Load config to extract periods and defect
    config_path = os.path.join("Configfile", foundry, "config.json")
    with open(config_path, "r") as f:
        config_data = json.load(f)

    reference_period = config_data["data_selection"]["reference_period"]
    comparison_period = config_data["data_selection"]["comparison_period"]
    defect = config_data["defect_for_analysis"]

    # Get top varied parameter from SQL
    query = text("""
        SELECT parameter AS `Parameters`, absolute_change AS `Absolute Change (%)`
        FROM summary_table
        WHERE foundry_name = :foundry_name AND defect_type = :defect_type
        ORDER BY `Absolute Change (%)` DESC
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {
            "foundry_name": foundry,
            "defect_type": defect
        })
        summary_table = pd.DataFrame(result.fetchall(), columns=result.keys())

    if summary_table.empty:
        return {
            "error": True,
            "message": "Summary table is empty"
        }

    top_parameter = summary_table.iloc[0]["Parameters"]
    chart_list = []

    # Chart Paths
    results_dir = os.path.join("results", foundry)
    temp_dir = os.path.join(results_dir, "temp")
    fba_dir = os.path.join("results", "FBADiagrams")
    
    monthly_chart = os.path.join(results_dir, f"monthly_rejection_rate_{defect}.jpeg")
    if os.path.exists(monthly_chart):
        chart_list.append(f"{base_url}/results/{foundry}/monthly_rejection_rate_{defect}.jpeg")

    fba_chart = os.path.join(fba_dir, f"{defect}.jpg")
    if os.path.exists(fba_chart):
        chart_list.append(f"{base_url}/results/FBADiagrams/{defect}.jpg")

    for plot_type in ["Distribution", "Box", "Correlation"]:
        file_path = os.path.join(temp_dir, f"{plot_type} plot of {top_parameter}.jpeg")
        if os.path.exists(file_path):
            chart_list.append(f"{base_url}/results/{foundry}/temp/{plot_type} plot of {top_parameter}.jpeg")

    summary_chart = os.path.join(results_dir, f"summary_table_plot_{defect}.jpeg")
    if os.path.exists(summary_chart):
        chart_list.append(f"{base_url}/results/{foundry}/summary_table_plot_{defect}.jpeg")

    return {
        "error": False,
        "messages": [
            f" Fishbone Analytics executed successfully for **{foundry}**.",
            f" Reference Period: **{reference_period[0]}** to **{reference_period[1]}**",
            f" Comparison Period: **{comparison_period[0]}** to **{comparison_period[1]}**",
            f" Top varied parameter: **{top_parameter}**"
        ],
        "charts": chart_list,
        "summary": {
            "reference_period": reference_period,
            "comparison_period": comparison_period,
            "top_parameter": top_parameter
        }
    }
