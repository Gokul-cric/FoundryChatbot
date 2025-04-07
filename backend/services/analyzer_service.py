# analyzer_service.py

import os
import json
import time
import pandas as pd
import requests
from sqlalchemy import text
from flask import jsonify
from database import connect_db
from services.config_service import update_defect_in_config

engine = connect_db()

def run_fishbone_analysis(foundry, route_type="/refcomp"):
    try:
        analyze_url = f"http://127.0.0.1:5000{route_type}"
        response = requests.post(
            analyze_url,
            json={"foundry": foundry},
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            if route_type == "/refcomp":
                return response.json()  
            else:
                return build_analysis_response(foundry)
        else:
            return jsonify({
                "response": {
                    "message": f"Failed to run analysis: {response.json().get('error', '')}",
                    "status": "failed"
                }
            })
    except Exception as e:
        return jsonify({"response": {"message": f"Error executing analysis: {str(e)}"}})


def build_analysis_response(foundry):
    base_url = "http://127.0.0.1:5000"
    results_dir = os.path.join("results", foundry)
    temp_dir = os.path.join(results_dir, "temp")
    fba_dir = os.path.join("results", "FBADiagrams")
    config_path = os.path.join("Configfile", foundry, "config.json")

    with open(config_path, "r") as f:
        config_data = json.load(f)

    defect = config_data["defect_for_analysis"]
    reference_period = config_data["data_selection"]["reference_period"]
    comparison_period = config_data["data_selection"]["comparison_period"]

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
        return jsonify({"error": "Summary table is empty"}), 400

    top_parameter = summary_table.iloc[0]["Parameters"]
    chart_list = []

    # 1. Monthly Rejection Chart
    monthly_chart = f"monthly_rejection_rate_{defect}.jpeg"
    monthly_chart_path = os.path.join(results_dir, monthly_chart)
    if os.path.exists(monthly_chart_path):
        chart_list.append(f"{base_url}/results/{foundry}/{monthly_chart}")

    # 2. Fishbone Diagram
    fba_diagram = f"{defect}.jpg"
    fishbone_chart = os.path.join(fba_dir, fba_diagram)
    if os.path.exists(fishbone_chart):
        chart_list.append(f"{base_url}/results/FBADiagrams/{fba_diagram}")

    # 3. Distribution, Box, Correlation Charts of Top Parameter
    for plot_type in ["Distribution", "Box", "Correlation"]:
        filename = f"{plot_type} plot of {top_parameter}.jpeg"
        file_path = os.path.join(temp_dir, filename)
        if os.path.exists(file_path):
            chart_list.append(f"{base_url}/results/{foundry}/temp/{filename}")

    # 4. Summary Chart
    summary_chart_path = os.path.join(results_dir, f"summary_table_plot_{defect}.jpeg")
    if os.path.exists(summary_chart_path):
        chart_list.append(f"{base_url}/results/{foundry}/summary_table_plot_{defect}.jpeg")

    return jsonify({
        "response": {
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
    })


def handle_analysis_intent(foundry):
    """
    Handles a regular Fishbone Analytics run for analysis intent.
    """
    return run_fishbone_analysis(foundry, route_type="/running")


def handle_companalysis_intent(foundry, defect_type):
    update_defect_in_config(foundry, defect_type)
    return run_fishbone_analysis(foundry, route_type="/refcomp")


def handle_trigger_analysis(foundry, defect_type, user_query):
    """
    Triggers full analysis on user command like 'run analysis', 'trigger analysis'.
    Calls the '/analyze' route and builds the response.
    """
    try:
        response = requests.post(
            "http://127.0.0.1:5000/analyze",
            json={"foundry": foundry},
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            return build_analysis_response(foundry)
        else:
            return jsonify({
                "response": {
                    "message": f"Failed to run analysis: {response.json().get('error', '')}",
                    "status": "failed"
                }
            })
    except Exception as e:
        return jsonify({"response": {"message": f"Error executing analysis: {str(e)}"}})
