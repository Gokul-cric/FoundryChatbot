# -*- coding: utf-8 -*-
# encoding='utf-8'
"""
Created on Fri Mar 25 11:16:58 2022
@author: ABhishankar Kumar, Karthikeyan R
"""

import os
import warnings
import plotly.express as px
import plotly.io as pio
import json
from sqlalchemy import text
import pandas as pd
from api.helper import get_data_for_analysis, outlier_calc, find_outliers, product_mix_calculator
from api.helper import dist_plot,box_plot,correlation_plot,enhanced_dist_plot
from database import connect_db, save_data_to_sql, save_chart_path,insert_summary_to_db,insert_rejection_data,insert_prepared_sand_data,generate_daily_rejection_summary


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


##########################################################################################################################################################
prodn_mix = product_mix_calculator(rejection_data, config_file, config_file["group"])
##########################################################################################################################################################

prepared_sand_data.fillna(method="ffill", inplace=True)
prepared_sand_data.fillna(method="bfill", inplace=True)


if (config_file["group_wise_analysis"] == True) and (config_file["component_wise_analysis"] == True):
    raise ValueError("Both group and component wise analysis cannot be set to True")

if config_file["group_wise_analysis"]:
    group = config_file["group_for_analysis"]
    prepared_sand_data = prepared_sand_data[prepared_sand_data["component_id"].astype(str).isin(config_file["group"][group])] 
    rejection_data = rejection_data[rejection_data["component_id"].astype(str).isin(config_file["group"][group])] 

if config_file["component_wise_analysis"]:
    comp = config_file["component_for_analysis"]
    prepared_sand_data = prepared_sand_data[prepared_sand_data["component_id"].astype(str).isin(comp)] 
    rejection_data = rejection_data[rejection_data["component_id"].astype(str).isin(comp)] 

generate_daily_rejection_summary(engine, foundry, config_file)


# ########################################################################################################################################################################################################  
with open(os.path.join(jsonpath, "config.json")) as f:
    config_file = json.load(f)

defect_type = config_file.get("defect_for_analysis", "Unknown Defect")
defect_columns = config_file.get("defect_mapping", {}).get(defect_type, [])
if not defect_columns:
    raise KeyError(f"Defect '{defect_type}' not found in config.json Defect Mapping.")

total_production_col = config_file.get("total_produced_qty", "total_quantity_produced")

rejection_data.columns = rejection_data.columns.str.strip()

date_column = "date"
time_format = "%b-%Y"
component_col = "component_id"

rejection_data[date_column] = pd.to_datetime(rejection_data[date_column])
rejection_data["Year-Month"] = rejection_data[date_column].dt.strftime(time_format)

if total_production_col not in rejection_data.columns:
    raise KeyError(f"Missing required column: '{total_production_col}' in rejection data.")
if component_col not in rejection_data.columns:
    raise KeyError(f"Missing required column: '{component_col}' in rejection data.")

for col in defect_columns:
    if col not in rejection_data.columns:
        raise KeyError(f"Missing required defect column: '{col}' in rejection data.")


defect_rejection_col = f"Total {defect_type} Rejection"
rejection_data[defect_rejection_col] = rejection_data[defect_columns].sum(axis=1)


componentwise_enabled = config_file.get("component_wise_analysis", False)
groupwise_enabled = config_file.get("group_wise_analysis", False)

if componentwise_enabled:
    components = config_file.get("component_for_analysis", [])
    rejection_data = rejection_data[rejection_data[component_col].isin(components)]

elif groupwise_enabled:
    group_name = config_file.get("group_for_analysis", "")
    group_map = config_file.get("group", {})
    group_components = group_map.get(group_name, [])
    rejection_data = rejection_data[rejection_data[component_col].isin(group_components)]

monthly_rejection = (
    rejection_data.groupby("Year-Month").agg({
        defect_rejection_col: "sum",
        total_production_col: "sum"
    }).reset_index()
)

monthly_rejection["Rejection Percentage"] = (
    (monthly_rejection[defect_rejection_col] / monthly_rejection[total_production_col]) * 100
)
monthly_rejection["Year-Month"] = pd.to_datetime(monthly_rejection["Year-Month"], format="%b-%Y")
monthly_rejection = monthly_rejection.sort_values("Year-Month")
monthly_rejection["Year-Month"] = monthly_rejection["Year-Month"].dt.strftime("%b-%Y")

save_data_to_sql(foundry, "rejection_analysis", monthly_rejection, engine, config_file)
excel_path = os.path.join(results_dir, f"monthly_rejection_{defect_type}.xlsx")
monthly_rejection.to_excel(excel_path, index=False)

suffix = ""
if componentwise_enabled:
    suffix = f" - {config_file.get('component_for_analysis', '')}"
elif groupwise_enabled:
    suffix = f" - {config_file.get('group_for_analysis', '')}"

fig = px.bar(
    monthly_rejection,
    x="Year-Month",
    y="Rejection Percentage",
    text="Rejection Percentage",
    hover_data={
        "Year-Month": True,
        "Rejection Percentage": ":.2f",
        defect_rejection_col: True,
        total_production_col: True
    },
    title=f"Rejection (%) over Period - {defect_type}{suffix}",
    color="Rejection Percentage",
    color_continuous_scale="Reds"
)

fig.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
fig.update_layout(
    xaxis_title="Month",
    yaxis_title="Rejection %",
    xaxis_tickangle=-45
)
# fig.show()

plot_path = os.path.join(results_dir, f"monthly_rejection_rate_{defect_type}.jpeg")
pio.write_image(fig, plot_path, format="jpeg", scale=3, width=1000, height=600)

save_chart_path(foundry, defect_type, "monthly_rejection", plot_path, engine)
####################################################################################################################################
temp_dir = os.path.join(results_dir, "temp")
excel_path = os.path.join(results_dir, f"monthly_rejection_{defect_type}.xlsx")
monthly_rejection = pd.read_excel(excel_path)

if "Year-Month" not in monthly_rejection.columns or "Rejection Percentage" not in monthly_rejection.columns:
    raise KeyError("Missing required columns in monthly_rejection_data.xlsx")


date_column = "date"
rejection_data[date_column] = pd.to_datetime(rejection_data[date_column])
rejection_data["Year-Month"] = rejection_data[date_column].dt.strftime("%b-%Y")

lowest_rejection_month = monthly_rejection.loc[monthly_rejection["Rejection Percentage"].idxmin(), "Year-Month"]
lowest_month_mask = rejection_data["Year-Month"] == lowest_rejection_month
lowest_month_dates = rejection_data.loc[lowest_month_mask, date_column]
reference_start = str(lowest_month_dates.min().date())
reference_end = str(lowest_month_dates.max().date())

latest_rejection_month = monthly_rejection["Year-Month"].iloc[-1]
latest_month_mask = rejection_data["Year-Month"] == latest_rejection_month
latest_month_dates = rejection_data.loc[latest_month_mask, date_column]
comparison_start = str(latest_month_dates.min().date())
comparison_end = str(latest_month_dates.max().date())

config_path = os.path.join(jsonpath, "config.json")
with open(config_path, "r") as f:
    config_data = json.load(f)

config_data["data_selection"]["reference_period"] = [reference_start, reference_end]
config_data["data_selection"]["comparison_period"] = [comparison_start, comparison_end]

with open(config_path, "w") as f:
    json.dump(config_data, f, indent=4)

print(f"Reference Period set to: {reference_start} , {reference_end}")
print(f"Comparison Period set to: {comparison_start} , {comparison_end}")



if config_data["data_selection"]["reference_period"] == config_data["data_selection"]["comparison_period"]:
    print(f" Great job! The latest month [{config_data['data_selection']['reference_period'][0]}] has the **lowest rejection rate** — no comparison needed.")


#############################################################################################################################################################3
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

dist_dict, plot_data, dist_labels, div_data_dict, div_dict,mad_dict= enhanced_dist_plot(data_for_analysis,config_data1,analysis_frequency,show_plot=False,results_dir=result_dir)

box_dict, summary_dict = box_plot(data_for_analysis,config_data1,analysis_frequency, show_plot=True,results_dir=result_dir)

corr_dict, corr_labels = correlation_plot(data_for_analysis,config_data1,analysis_frequency, show_plot=True,results_dir=result_dir)


summary_table = pd.DataFrame(columns=["Parameters", "Absolute Change (%)"])
summary_table["Parameters"] = list(summary_dict.keys())
summary_table["Absolute Change (%)"] = list(summary_dict.values())
summary_table.sort_values(by="Absolute Change (%)", ascending=False, inplace=True)

insert_summary_to_db(foundry, defect_type, summary_dict, engine)
summary_table.to_excel(os.path.join(results_dir,"summary_table.xlsx"),index=False)

outlier_dict = outlier_calc(box_dict)
outliers = find_outliers(outlier_dict, box_dict)

# df = pd.concat([data_for_analysis["ref_data"], data_for_analysis["comp_data"]])
# # df.to_excel(os.path.join(results_dir,config_file['component_for_analysis']+"_"+config_file['defect_for_analysis']+".xlsx"))

# component_name=config_file['component_for_analysis'][0] if isinstance(config_file['component_for_analysis'],list) else config_file['component_for_analysis']

# df.to_excel(os.path.join(results_dir,f"{component_name}_{config_file['defect_for_analysis']}.xlsx"))

# ################################################################################################################################################################################

# summary_table_path = os.path.join(results_dir, "summary_table.xlsx")
# summary_table = pd.read_excel(summary_table_path)

# if "Parameters" not in summary_table.columns or "Absolute Change (%)" not in summary_table.columns:
#     raise KeyError("Missing required columns: 'Parameters' and 'Absolute Change (%)' in summary_table.xlsx")

# summary_table = summary_table.sort_values(by="Absolute Change (%)", ascending=False)

# fig = px.bar(
#     summary_table,
#     x="Parameters",
#     y="Absolute Change (%)",
#     orientation="v",
#     text="Absolute Change (%)",
#     hover_data={"Parameters": True, "Absolute Change (%)": ":.2f"},
#     labels={"Absolute Change (%)": "Percentage Change"},
#     title="Summary Table: Absolute Change (%) by Parameter",
#     color="Absolute Change (%)",
#     color_continuous_scale="Blues"
# )

# fig.update_traces(texttemplate='%{text:.2f}%', textposition="outside")
# # fig.show()

# summary_plot_path = os.path.join(results_dir, f"summary_table_plot_{defect_type}.jpeg")
# pio.write_image(fig, summary_plot_path, format="jpeg", scale=3, width=1000, height=600)

# ##########################################################################################################################################################

