# chart_service.py

import os
import requests
from sqlalchemy import text
from flask import jsonify
from database import connect_db

engine = connect_db()

def handle_chart_request(foundry, defect_type, chart_request, user_query):
    chart_blocks = []

    for chart_type, param in chart_request:
        chart_response = requests.post("http://127.0.0.1:5000/chart", json={
            "foundry": foundry,
            "chart_type": chart_type,
            "parameter": param
        })

        if chart_response.ok:
            chart_json = chart_response.json()
            chart_list = chart_json.get("charts", [])
            if chart_list:
                for chart_url in chart_list:
                    chart_blocks.append({
                        "message": f"Here is the **{chart_type}** chart for **{param}**.",
                        "image": chart_url
                    })
            else:
                chart_blocks.append({
                    "message": f"Sorry, no {chart_type} chart found for {param}.",
                    "image": None
                })
        else:
            chart_blocks.append({
                "message": f"Failed to generate {chart_type} chart for {param}.",
                "image": None
            })

    return jsonify({
        "response": {
            "chart_blocks": chart_blocks
        }
    })


def generate_fallback_charts(foundry, defect_type):
    fallback_charts = []
    fallback_messages = []

    try:
        query = text("""
            SELECT parameter
            FROM summary_table
            WHERE foundry_name = :foundry_name AND defect_type = :defect_type
            ORDER BY absolute_change DESC
            LIMIT 1
        """)
        with engine.connect() as conn:
            result = conn.execute(query, {
                "foundry_name": foundry,
                "defect_type": defect_type
            })
            row = result.fetchone()
            if row:
                fallback_param = row[0]

                for chart_type in ["Distribution", "Box", "Correlation"]:
                    chart_response = requests.post("http://127.0.0.1:5000/chart", json={
                        "foundry": foundry,
                        "chart_type": chart_type,
                        "parameter": fallback_param
                    })

                    if chart_response.ok:
                        chart_json = chart_response.json()
                        chart_list = chart_json.get("charts", [])
                        if chart_list:
                            fallback_charts.extend(chart_list)
                        else:
                            fallback_messages.append(f"Sorry, no {chart_type} chart found for {fallback_param}.")
                    else:
                        fallback_messages.append(f"Failed to generate {chart_type} chart for {fallback_param}.")

                return jsonify({
                    "response": {
                        "messages": fallback_messages,
                        "charts": fallback_charts
                    }
                })
            else:
                return jsonify({
                    "response": {
                        "messages": ["Unable to determine top varied parameter for fallback charts."],
                        "charts": []
                    }
                })
    except Exception as e:
        print("Error generating fallback charts:", e)
        return jsonify({
            "response": {
                "messages": ["Unable to generate charts for the given defect."],
                "charts": []
            }
        })


def handle_chart_intent(user_query, foundry, defect_type, memory):
    from utils.sql_utils import extract_chart_intent

    chart_request = extract_chart_intent(user_query)
    
    if chart_request and all(isinstance(item, tuple) and len(item) == 2 for item in chart_request):
        return handle_chart_request(foundry, defect_type, chart_request, user_query)
    else:
        return generate_fallback_charts(foundry, defect_type)
