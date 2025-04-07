# backend/api/analysis.py
from utils.plot_generator import generate_summary_plots
import os
from api.helper_new import get_data_for_analysis, dist_plot, box_plot, correlation_plot
import json

def generate_comparison_charts(foundry):
    # Paths
    basepath = os.getcwd()
    datapath = os.path.join(basepath, "Data", foundry)
    configpath = os.path.join(basepath, "Configfile", foundry, "config.json")
    results_dir = os.path.join(basepath, "results", foundry, "temp")
    os.makedirs(results_dir, exist_ok=True)

    # Load config
    with open(configpath, "r") as f:
        config_file = json.load(f)

    # Load from database
    from database import get_mysql_table
    prepared_sand = get_mysql_table(f"prepared_{foundry.lower()}")
    rejection = get_mysql_table(f"rejection_{foundry.lower()}")

    # Determine frequency
    analysis_frequency = ["Date"]
    if "Shift" in rejection.columns and rejection["Shift"].isna().sum() <= 0.05 * rejection.shape[0]:
        analysis_frequency = ["Date", "Shift"]

    # Clean sand data
    prepared_sand.fillna(method="ffill", inplace=True)
    prepared_sand.fillna(method="bfill", inplace=True)

    # Align data
    data_for_analysis, opt_bin = get_data_for_analysis(prepared_sand, rejection, config_file, analysis_frequency)
    generate_summary_plots(data_for_analysis, foundry, config_file, opt_bin)



    if data_for_analysis["ref_data"].empty or data_for_analysis["comp_data"].empty:
        raise RuntimeError("No data available in selected periods")

    dist_plot(data_for_analysis, config_file, analysis_frequency, results_dir, show_plot=True)

    box_plot(data_for_analysis, config_file, analysis_frequency, results_dir, show_plot=True)

    correlation_plot(data_for_analysis, config_file, analysis_frequency, results_dir, show_plot=True)

    dist_paths = [f for f in os.listdir(results_dir) if f.startswith("Distribution plot")]
    box_paths = [f for f in os.listdir(results_dir) if f.startswith("Box plot")]
    corr_paths = [f for f in os.listdir(results_dir) if f.startswith("Correlation plot")]

    return {
        "distribution": [os.path.join("results", foundry, "temp", f) for f in dist_paths],
        "box": [os.path.join("results", foundry, "temp", f) for f in box_paths],
        "correlation": [os.path.join("results", foundry, "temp", f) for f in corr_paths],
    }
