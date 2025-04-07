import os
import json
import pandas as pd
from sqlalchemy import text
from database import connect_db
from flask import jsonify
from utils.plot_generator import generate_summary_chart

engine = connect_db()

def fetch_summary_data(foundry, defect_type):
    """
    Fetches summary data (absolute change) from the database for a given foundry and defect type.
    Generates a summary chart.
    Returns: dictionary with messages, summary table, and summary chart URL.
    """
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
        "summary_chart": summary_chart_url or "No Summary Chart Available"
    }


def handle_summary_intent(foundry, defect_type):
    summary_data = fetch_summary_data(foundry, defect_type)
    return {
        "messages": summary_data["messages"],
        "summary": {
            "summary_table": summary_data["summary_table"],
            "summary_chart": summary_data["summary_chart"]
        }
    }
