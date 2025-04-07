import os
import json
import time
import glob
import requests
import subprocess
from flask import Flask, request, jsonify, Blueprint,send_from_directory
from flask_cors import CORS
from api.chatbot import chatbot_bp
import pandas as pd
from database import connect_db
from sqlalchemy import text
# from api.voice import voice_bp
# from api.chatbot import generate_summary_chart
from utils.plot_generator import generate_summary_chart
import pandas as pd

engine=connect_db()
print("Database connection established")


app = Flask(__name__)
app.secret_key = "b3c1f7a45d2e8e7d9a6c1f5b4d3e6c9f"


app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+mysqlconnector://root:Password%40123@localhost/foundry_db"  
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True



CORS(app, resources={r"/*": {"origins": "http://localhost:3000/"}}, supports_credentials=True)
app.register_blueprint(chatbot_bp, url_prefix="/chatbot")
# app.register_blueprint(voice_bp)



@app.after_request
def after_request(response):
    """Handle CORS for all API responses."""
    response.headers["Access-Control-Allow-Origin"] = "http://localhost:3000"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, PUT, DELETE"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response


CONFIG_PATH = "configfile/{}/config.json"



@app.route("/update_config", methods=["POST"])
def update_config():
    """Update comparison period, defect for analysis, and group for analysis in config.json"""
    data = request.json
    foundry = data.get("foundry")
    defect = data.get("defect")
    comparison_period = data.get("comparison_period")
    group_for_analysis = data.get("group")

    if not foundry or not defect or not comparison_period or not group_for_analysis:
        return jsonify({"error": "Foundry, defect, comparison period, and group are required"}), 400

    config_path = CONFIG_PATH.format(foundry)

    if not os.path.exists(config_path):
        return jsonify({"error": "Config file not found for the specified foundry"}), 404

    try:
        with open(config_path, "r") as file:
            config_data = json.load(file)

        config_data["data_selection"]["comparison_period"] = [comparison_period]
        config_data["defect_for_analysis"] = defect
        config_data["group_for_analysis"] = group_for_analysis

        with open(config_path, "w") as file:
            json.dump(config_data, file, indent=4)

        return jsonify({
            "message": "Config updated successfully",
            "comparison_period": comparison_period,
            "defect_for_analysis": defect,
            "group_for_analysis": group_for_analysis
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        foundry = request.json.get("foundry", "Munjal") 

    
        script_path = os.path.join(os.getcwd(), "fishbone_analytics_new.py")

        result = subprocess.run(["python", script_path], capture_output=True, text=True)

        if result.returncode != 0:
            print("Error executing Fishbone Analysis:", result.stderr)
            return jsonify({"error": "Failed to execute Fishbone Analysis", "details": result.stderr}), 500

        base_url = "http://127.0.0.1:5000"
        results_dir = os.path.join("results", foundry)
        temp_dir = os.path.join(results_dir, "temp")
        fba_dir=os.path.join("results","FBADiagrams")

        # Load config to fetch reference/comparison period
        config_path = os.path.join("Configfile", foundry, "config.json")
        with open(config_path, "r") as f:
            config_data = json.load(f)

        reference_period = config_data["data_selection"]["reference_period"]
        comparison_period = config_data["data_selection"]["comparison_period"]
        
       
        query = text("""
                    SELECT parameter AS `Parameters`, absolute_change AS `Absolute Change (%)`
                    FROM summary_table
                    WHERE foundry_name = :foundry_name AND defect_type = :defect_type
                    ORDER BY `Absolute Change (%)` DESC
                """)
        with engine.connect() as conn:
            result = conn.execute(query, {"foundry_name": foundry, "defect_type": config_data["defect_for_analysis"]})
            summary_table = pd.DataFrame(result.fetchall(), columns=result.keys())

        if summary_table.empty:
            return jsonify({"error": "Summary table is empty"}), 400

        top_parameter = summary_table.iloc[0]["Parameters"]
        timestamp = int(time.time())
        chart_list = []
        
        defect = config_data["defect_for_analysis"]
        fba_diagram=f"{defect}.jpg"
        fishbone_chart=os.path.join(fba_dir,fba_diagram)
        monthly_chart = f"monthly_rejection_rate_{defect}.jpeg"
        monthly_chart_path = os.path.join(results_dir, monthly_chart)
        if os.path.exists(monthly_chart_path):
            chart_list.append(f"{base_url}/results/{foundry}/{monthly_chart}?t={timestamp}")

        if os.path.exists(fishbone_chart):
            chart_list.append(f"{base_url}/results/FBADiagrams/{fba_diagram}")

        for plot_type in ["Distribution", "Box", "Correlation"]:
            filename = f"{plot_type} plot of {top_parameter}.jpeg"
            file_path = os.path.join(temp_dir, filename)
            if os.path.exists(file_path):
                chart_list.append(f"{base_url}/results/{foundry}/temp/{filename}")

        # summary_chart_path = os.path.join(results_dir, f"summary_table_plot_{defect}.jpeg")
        # if os.path.exists(summary_chart_path):
        #     chart_list.append(f"{base_url}/results/{foundry}/summary_table_plot_{defect}.jpeg")
        if not summary_table.empty:
            summary_dict = [{"parameter": row["Parameters"], "absolute_change": row["Absolute Change (%)"]} for _, row in summary_table.iterrows()]
            summary_chart_path = generate_summary_chart(foundry, defect, summary_dict)
            summary_chart_url = f"http://127.0.0.1:5000/{summary_chart_path}"
            chart_list.append(summary_chart_url)




        return jsonify({
            "message": f"Fishbone Analytics executed successfully for {foundry}!",
            "charts": chart_list,
            "top_parameter": top_parameter,
            "reference_period": reference_period,
            "comparison_period": comparison_period
        })
       

    except Exception as e:
        print("Exception in /analyze:", e)
        return jsonify({"error": str(e)}), 500


@app.route("/running", methods=["POST"])
def running():
    try:
        foundry = request.json.get("foundry", "")
        script_path = os.path.join(os.getcwd(), "fishbone_analytics_nu.py")

        result = subprocess.run(["python", script_path], capture_output=True, text=True)

        if result.returncode != 0:
            print("Error executing Fishbone Analysis:", result.stderr)
            return jsonify({"error": "Failed to execute Fishbone Analysis", "details": result.stderr}), 500

        base_url = "http://127.0.0.1:5000"
        results_dir = os.path.join("results", foundry)
        temp_dir = os.path.join(results_dir, "temp")
        fba_dir=os.path.join("results","FBADiagrams")

        # Load config to fetch reference/comparison period
        config_path = os.path.join("Configfile", foundry, "config.json")
        with open(config_path, "r") as f:
            config_data = json.load(f)

        reference_period = config_data["data_selection"]["reference_period"]
        comparison_period = config_data["data_selection"]["comparison_period"]

        query = text("""
                        SELECT parameter AS `Parameters`, absolute_change AS `Absolute Change (%)`
                        FROM summary_table
                        WHERE foundry_name = :foundry AND defect_type = :defect
                        ORDER BY `Absolute Change (%)` DESC
                    """)
        with engine.connect() as conn:
            result = conn.execute(query, {
                "foundry": foundry,
                "defect": config_data["defect_for_analysis"]
            })

            summary_table = pd.DataFrame(result.fetchall(), columns=result.keys())

        if summary_table.empty:
            return jsonify({"error": "Summary table is empty"}), 400

        top_parameter = summary_table.iloc[0]["Parameters"]

        timestamp = int(time.time())
        # Prepare selected chart paths (in order)
        chart_list = []
        
        
        # 1. Monthly Rejection
        defect = config_data["defect_for_analysis"]
        fba_diagram=f"{defect}.jpg"
        fishbone_chart=os.path.join(fba_dir,fba_diagram)
        monthly_chart = f"monthly_rejection_rate_{defect}.jpeg"
        monthly_chart_path = os.path.join(results_dir, monthly_chart)
        if os.path.exists(monthly_chart_path):
            chart_list.append(f"{base_url}/results/{foundry}/{monthly_chart}?t={timestamp}")

        if os.path.exists(fishbone_chart):
            chart_list.append(f"{base_url}/results/FBADiagrams/{fba_diagram}")

        # 2. Distribution, Box, Correlation plots of top varied parameter
        for plot_type in ["Distribution", "Box", "Correlation"]:
            filename = f"{plot_type} plot of {top_parameter}.jpeg"
            file_path = os.path.join(temp_dir, filename)
            if os.path.exists(file_path):
                chart_list.append(f"{base_url}/results/{foundry}/temp/{filename}")

        # 3. Summary Chart
        # summary_chart_path = os.path.join(results_dir, f"summary_table_plot_{defect}.jpeg")
        # if os.path.exists(summary_chart_path):
        #     chart_list.append(f"{base_url}/results/{foundry}/summary_table_plot_{defect}.jpeg")
        if not summary_table.empty:
            summary_dict = [{"parameter": row["Parameters"], "absolute_change": row["Absolute Change (%)"]} for _, row in summary_table.iterrows()]
            summary_chart_path = generate_summary_chart(foundry, defect, summary_dict)
            summary_chart_url = f"http://127.0.0.1:5000/{summary_chart_path}"
            chart_list.append(summary_chart_url)



        return jsonify({
            "message": f"Fishbone Analytics executed successfully for {foundry}!",
            "charts": chart_list,
            "top_parameter": top_parameter,
            "reference_period": reference_period,
            "comparison_period": comparison_period
        })

    except Exception as e:
        print("Exception in /running:", str(e))
        return jsonify({"error": str(e)}), 500



@app.route("/refcomp", methods=["POST"])
def refcomp():
    print("Triggered /refcomp route")
    try:
        foundry = request.json.get("foundry", "Munjal")
        script_path = os.path.join(os.getcwd(), "fishbone_ref_comp.py")

        result = subprocess.run(["python", script_path], capture_output=True, text=True)

        if result.returncode != 0:
            print("Error executing Fishbone Analysis:", result.stderr)
            return jsonify({"error": "Failed to execute Fishbone Analysis", "details": result.stderr}), 500

        base_url = "http://127.0.0.1:5000"
        results_dir = os.path.join("results", foundry)
        temp_dir = os.path.join(results_dir, "temp")
        fba_dir=os.path.join("results","FBADiagrams")

        # Load config to fetch reference/comparison period
        config_path = os.path.join("Configfile", foundry, "config.json")
        with open(config_path, "r") as f:
            config_data = json.load(f)

        reference_period = config_data["data_selection"]["reference_period"]
        comparison_period = config_data["data_selection"]["comparison_period"]

        # Load summary table from database
        query = text("""
                        SELECT parameter AS `Parameters`, absolute_change AS `Absolute Change (%)`
                        FROM summary_table
                        WHERE foundry_name = :foundry AND defect_type = :defect
                        ORDER BY `Absolute Change (%)` DESC
                    """)
        with engine.connect() as conn:
            result = conn.execute(query, {
                "foundry": foundry,
                "defect": config_data["defect_for_analysis"]
            })

            summary_table = pd.DataFrame(result.fetchall(), columns=result.keys())

        if summary_table.empty:
            return jsonify({"error": "Summary table is empty"}), 400

        top_parameter = summary_table.iloc[0]["Parameters"]

        timestamp = int(time.time())

        chart_list = []
        
        
        defect = config_data["defect_for_analysis"]
        fba_diagram=f"{defect}.jpg"
        fishbone_chart=os.path.join(fba_dir,fba_diagram)
        monthly_chart = f"monthly_rejection_rate_{defect}.jpeg"
        monthly_chart_path = os.path.join(results_dir, monthly_chart)
        if os.path.exists(monthly_chart_path):
            chart_list.append(f"{base_url}/results/{foundry}/{monthly_chart}?t={timestamp}")

        if os.path.exists(fishbone_chart):
            chart_list.append(f"{base_url}/results/FBADiagrams/{fba_diagram}")

        # 2. Distribution, Box, Correlation plots of top varied parameter
        for plot_type in ["Distribution", "Box", "Correlation"]:
            filename = f"{plot_type} plot of {top_parameter}.jpeg"
            file_path = os.path.join(temp_dir, filename)
            if os.path.exists(file_path):
                chart_list.append(f"{base_url}/results/{foundry}/temp/{filename}")

        # 3. Summary Chart
        if not summary_table.empty:
            summary_dict = [{"parameter": row["Parameters"], "absolute_change": row["Absolute Change (%)"]} for _, row in summary_table.iterrows()]
            summary_chart_path = generate_summary_chart(foundry, defect, summary_dict)
            summary_chart_url = f"http://127.0.0.1:5000/{summary_chart_path}"
            chart_list.append(summary_chart_url)


        return jsonify({
            "message": f"Fishbone Analytics executed successfully for {foundry}!",
            "charts": chart_list,
            "top_parameter": top_parameter,
            "reference_period": reference_period,
            "comparison_period": comparison_period
        })

    except Exception as e:
        print("Exception in /refcomp:", str(e))
        return jsonify({"error": str(e)}), 500
    

@app.route("/chart", methods=["POST"])
def charts():
    try:
        foundry = request.json.get("foundry", "Munjal")
        chart_type = request.json.get("chart_type", None)
        parameter = request.json.get("parameter", None)
        
        script_path = os.path.join(os.getcwd(), "Charts.py")
        result = subprocess.run(["python", script_path], capture_output=True, text=True)

        if result.returncode != 0:
            print("Error executing chart generation:", result.stderr)
            return jsonify({"error": "Failed to generate charts", "details": result.stderr}), 500

        temp_dir = os.path.join("results", foundry, "temp")
        base_url = f"http://127.0.0.1:5000/results/{foundry}/temp"
        matched = []

        config_path = os.path.join("Configfile", foundry, "config.json")
        if os.path.exists(config_path):
            with open(config_path) as f:
                config = json.load(f)
            if not parameter:
                parameter = config.get("top_parameter", None)

        for file in os.listdir(temp_dir):
            if file.endswith(".jpeg"):
                if chart_type and chart_type.lower() not in file.lower():
                    continue
                if parameter and parameter.lower() not in file.lower():
                    continue
                matched.append(f"{base_url}/{file}?t={int(time.time())}")

        return jsonify({
            "message": f"{chart_type or 'All'} charts returned successfully!",
            "charts": matched
        })

    except Exception as e:
        print("Exception in /chart:", e)
        return jsonify({"error": str(e)}), 500






@app.route("/update_analysis_selection", methods=["POST"])
def update_analysis_selection():
    """Update foundry, defect, group, component selection, and reference/comparison periods in config.json"""
    data = request.json
    foundry = data.get("foundry")
    defect = data.get("defect")
    group = data.get("group")
    selected_components = data.get("components", [])
    reference_period = data.get("reference_period", [])
    comparison_period = data.get("comparison_period", [])

    if not foundry or not defect or not group:
        return jsonify({"error": "Foundry, defect, and group are required"}), 400

    config_path = CONFIG_PATH.format(foundry)

    if not os.path.exists(config_path):
        return jsonify({"error": f"Config file not found for foundry: {foundry}"}), 404

    try:
        with open(config_path, "r") as file:
            config_data = json.load(file)

        default_components = config_data.get("group", {}).get(group, [])

        components_to_use = selected_components if selected_components else default_components

        config_data["defect_for_analysis"] = defect
        config_data["group_for_analysis"] = group
        config_data["component_for_analysis"] = components_to_use
        config_data["group_wise_analysis"] = bool(not selected_components)  
        config_data["component_wise_analysis"] = bool(selected_components)  

        
        if reference_period and comparison_period:
            config_data["data_selection"] = {
                "reference_period": reference_period,
                "comparison_period": comparison_period
            }

        
        with open(config_path, "w") as file:
            json.dump(config_data, file, indent=4)

        return jsonify({
            "message": "Config updated successfully",
            "defect_for_analysis": defect,
            "group_for_analysis": group,
            "component_for_analysis": components_to_use,
            "reference_period": reference_period,
            "comparison_period": comparison_period,
            "analysis_mode": "Component-Wise" if selected_components else "Group-Wise"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500



CONFIG_DIR="Configfile"
@app.route("/get_dropdown_options", methods=["GET"])
def get_dropdown_options():
    foundry = request.args.get("foundry")

    config_path = os.path.join(CONFIG_DIR, foundry, "config.json")
    if not os.path.exists(config_path):
        return jsonify({"error": f"Config file not found for {foundry}"}), 404

    with open(config_path, "r") as f:
        config_data = json.load(f)

    defect_options = list(config_data.get("defect_mapping", {}).keys())
    group_options = list(config_data.get("group", {}).keys())

    
    component_options = []
    for group, components in config_data.get("group", {}).items():
        selected_group = config_data.get("selected_group", "")
        component_options = config_data["group"].get(selected_group, [])

    return jsonify({
        "defectOptions": defect_options,
        "groupOptions": group_options,
        "componentOptions": component_options
    })



@app.route("/get_foundry_data", methods=["GET"])
def get_foundry_data():
    foundry = request.args.get("foundry")

    config_path = os.path.join(CONFIG_DIR, foundry, "config.json")
    if not os.path.exists(config_path):
        return jsonify({"error": f"Config file not found for {foundry}"}), 404

    with open(config_path, "r") as f:
        config_data = json.load(f)

    foundry_lines = config_data.get("foundry_lines", [])
    group_options = list(config_data.get("group", {}).keys())

    component_options = []
    for group in group_options:
        component_options.extend(config_data["group"].get(group, []))

    return jsonify({
        "foundryLines": foundry_lines,
        "groupOptions": group_options,
        "componentOptions": component_options
    })


@app.route('/results/<path:filename>')
def serve_chart(filename):
    """Serves saved chart images from the 'results' folder."""
    return send_from_directory("results", filename)


@app.route("/restart", methods=["POST"])
def restart_app():
    """Restarts the Flask application automatically after each query execution."""
    print(" Restarting Flask application...")

    subprocess.Popen(["python", "app.py"])  

    os._exit(0)



@app.route('/results/<path:filename>')
def serve_results(filename):
    return send_from_directory('results', filename)




if __name__ == "__main__":
    app.run(debug=True, port=5000)
