import os
import warnings
import plotly.express as px
import plotly.io as pio
import json
from sqlalchemy import text
import pandas as pd
from api.helper import get_data_for_analysis, outlier_calc, find_outliers, product_mix_calculator
from api.helper import box_plot,correlation_plot,enhanced_dist_plot
from database import connect_db, insert_summary_to_db


warnings.simplefilter("ignore")

foundry = "Munjal"

engine = connect_db()

basepath = os.getcwd()
filepath = os.getcwd()
datapath = os.path.join(os.path.join(basepath,"Data"),foundry)
jsonpath=os.path.join(os.path.join(basepath,"Configfile"),foundry)
results_dir = os.path.join(os.path.join(basepath,"results"),foundry)

temp_dir = os.path.join(basepath,"results",foundry,"temp")

with open(os.path.join(jsonpath,"config.json")) as f:
    config_file = json.load(f)

prepared_table = "prepared_sand_data"
rejection_table = "rejection_data"

with engine.connect() as conn:
    prepared_sand_data = pd.read_sql(text(f"SELECT * FROM {prepared_table}"), con=conn)
    rejection_data = pd.read_sql(text(f"SELECT * FROM {rejection_table}"), con=conn)

prepared_sand_data.columns = prepared_sand_data.columns.str.lower()
rejection_data.columns = rejection_data.columns.str.lower()


if "time" in prepared_sand_data.columns:
    prepared_sand_data.drop(columns=["time"], inplace=True)

analysis_frequency = ["date"]
if rejection_data["shift"].isna().sum() <= 0.05*(rejection_data.shape[0]):
    analysis_frequency = ["date", "shift"]

defect_type = config_file.get("defect_for_analysis", "Unknown Defect")

config_path = os.path.join(jsonpath, "config.json")

with open(config_path, "r") as f:
    config_data1 = json.load(f)  
data_for_analysis, opt_bin =get_data_for_analysis(prepared_sand_data,rejection_data,config_data1, analysis_frequency)

df = pd.concat([data_for_analysis["ref_data"], data_for_analysis["comp_data"]])
df.sort_values(analysis_frequency,ascending=True,inplace = True)
df = df.round(2)
df.to_excel(os.path.join(results_dir,config_file['component_for_analysis'][0]+"_"+config_file['defect_for_analysis']+".xlsx"),index = False)

if (data_for_analysis["ref_data"].shape[0] <= config_file["data_sufficiency_check"]["ref_data"]):
    raise RuntimeError("Less data points in reference period for statisitcal analysis") 

if (data_for_analysis["comp_data"].shape[0] <= config_file["data_sufficiency_check"]["comp_data"]):
    raise RuntimeError("Less data points in comparison period for statisitcal analysis") 

result_dir=os.path.join(results_dir, "temp")

dist_dict, plot_data, dist_labels, div_data_dict, div_dict,mad_dict= enhanced_dist_plot(data_for_analysis,config_data1,analysis_frequency,show_plot=True,results_dir=result_dir)

box_dict, summary_dict = box_plot(data_for_analysis,config_data1,analysis_frequency, show_plot=True,results_dir=result_dir)

corr_dict, corr_labels = correlation_plot(data_for_analysis,config_data1,analysis_frequency, show_plot=True,results_dir=result_dir)


summary_table = pd.DataFrame(columns=["Parameters", "Absolute Change (%)"])
summary_table["Parameters"] = list(summary_dict.keys())
summary_table["Absolute Change (%)"] = list(summary_dict.values())
summary_table.sort_values(by="Absolute Change (%)", ascending=False, inplace=True)

top_param = summary_table.iloc[0]["Parameters"]
config_file["top_parameter"] = top_param
with open(config_path, "w") as f:
    json.dump(config_file, f, indent=4)

insert_summary_to_db(foundry, defect_type, summary_dict, engine)

outlier_dict = outlier_calc(box_dict)
outliers = find_outliers(outlier_dict, box_dict)
