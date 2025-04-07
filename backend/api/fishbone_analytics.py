# -*- coding: utf-8 -*-
"""
Created on Fri Mar 25 11:16:58 2022

@author: ABhishankar Kumar, Karthikeyan R
"""

import os
import warnings
import plotly.express as px
import plotly.io as pio
import json
import pandas as pd
from api.helper_new import get_data_for_analysis, outlier_calc, find_outliers, product_mix_calculator
from api.helper_new import dist_plot,box_plot,correlation_plot
from database import connect_db, save_data_to_sql, save_chart_path, get_reference_period,insert_prepared_sand_data,save_analysis_data,create_analysis_table,insert_summary_to_db,insert_rejection_data


warnings.simplefilter("ignore")


foundry="Munjal"

engine = connect_db()

basepath = os.getcwd()
filepath = os.getcwd()
datapath = os.path.join(os.path.join(basepath,"Data"),foundry)
jsonpath=os.path.join(os.path.join(basepath,"Configfile"),foundry)
results_dir = os.path.join(os.path.join(basepath,"results"),foundry)

temp_dir = os.path.join(basepath,"results",foundry,"temp")

with open(os.path.join(jsonpath,"config.json")) as f:
    config_file = json.load(f)

for file in os.listdir(datapath):
    if file.endswith(".xlsx"):
        if "Prepared" in file:
            prepared_sand_data = pd.read_excel(os.path.join(datapath, file), skiprows=5)
        elif "Rejection" in file:
            rejection_data = pd.read_excel(os.path.join(datapath, file), skiprows=5)

        

if "Time" in prepared_sand_data.columns:
        prepared_sand_data.drop(columns=["Time"], inplace=True)


analysis_frequency = ["Date"]
if rejection_data["Shift"].isna().sum() <= 0.05*(rejection_data.shape[0]):
    analysis_frequency = ["Date", "Shift"]



################################################################################################################################################################

prodn_mix = product_mix_calculator(rejection_data, config_file, config_file["group"])

##########################################################################################################################################################

prepared_sand_data.fillna(method="ffill", inplace=True)
prepared_sand_data.fillna(method="bfill", inplace=True)

insert_rejection_data(foundry, engine, rejection_data)
insert_prepared_sand_data(foundry,engine, prepared_sand_data)



# if (config_file["group_wise_analysis"] == True) and (config_file["component_wise_analysis"] == True):
#     raise ValueError("Both group and component wise analysis cannot be set to True")


# if config_file["group_wise_analysis"]:
#     group = config_file["group_for_analysis"]
#     prepared_sand_data = prepared_sand_data[prepared_sand_data["Component Id"].astype(str).isin(config_file["group"][group])] 
#     rejection_data = rejection_data[rejection_data["Component Id"].astype(str).isin(config_file["group"][group])] 


# if config_file["component_wise_analysis"]:
#     comp = config_file["component_for_analysis"]
#     prepared_sand_data = prepared_sand_data[prepared_sand_data["Component Id"].astype(str).isin(comp)] 
#     rejection_data = rejection_data[rejection_data["Component Id"].astype(str).isin(comp)] 

# data_for_analysis, opt_bin =get_data_for_analysis(prepared_sand_data,rejection_data,config_data1, analysis_frequency)

# df = pd.concat([data_for_analysis["ref_data"], data_for_analysis["comp_data"]])
# df.sort_values(["Date","Shift"],ascending=True,inplace = True)
# df = df.round(2)
# df.to_excel(os.path.join(results_dir,config_file['component_for_analysis'][0]+"_"+config_file['defect_for_analysis']+".xlsx"),index = False)

# if (data_for_analysis["ref_data"].shape[0] <= config_file["data_sufficiency_check"]["ref_data"]):
#     raise RuntimeError("Less data points in reference period for statisitcal analysis") 

# if (data_for_analysis["comp_data"].shape[0] <= config_file["data_sufficiency_check"]["comp_data"]):
#     raise RuntimeError("Less data points in comparison period for statisitcal analysis") 

########################################################################################################################################################################################################  

with open(os.path.join(jsonpath, "config.json")) as f:
    config_file = json.load(f)

defect_type = config_file.get("defect_for_analysis", "Unknown Defect")

defect_columns = config_file.get("defect_mapping", {}).get(defect_type, [])
if not defect_columns:
    raise KeyError(f"Defect '{defect_type}' not found in config.json Defect Mapping.")


# rejection_data["Total Rejection"] = rejection_data[defect_columns].sum(axis=1)


# monthly_rejection = rejection_data.groupby("Year-Month").agg({
#     "Total Rejection": "sum",
#     total_production_col: "sum"
# }).reset_index()

# monthly_rejection["Rejection Percentage"] = (monthly_rejection["Total Rejection"] / monthly_rejection[total_production_col]) * 100
# monthly_rejection["Year-Month"] = pd.to_datetime(monthly_rejection["Year-Month"], format="%b-%Y").dt.strftime("%Y-%m")

# monthly_rejection.rename(columns={
#     "Year-Month": "month_year",
#     "Total Rejection": "total_rejection",
#     total_production_col: "total_production",
#     "Rejection Percentage": "rejection_percentage"
# }, inplace=True)

# monthly_rejection["foundry_name"] = foundry
# monthly_rejection["defect_type"] = defect_type


# save_data_to_sql("rejection_analysis", monthly_rejection, engine)


# if not os.path.exists(temp_dir):
#     os.makedirs(temp_dir, exist_ok=True)

# fig = px.bar(
#     monthly_rejection,
#     x="month_year",
#     y="rejection_percentage",
#     text="rejection_percentage",
#     title=f"Rejection Percentage Trend [{defect_type}]",
#     color="rejection_percentage",
#     color_continuous_scale="Blues"
# )

# fig.update_traces(texttemplate='%{text:.2f}%', textposition="outside")
# plot_path = os.path.join(temp_dir, f"monthly_rejection_rate_{defect_type}.jpeg")
# pio.write_image(fig, plot_path, format="jpeg", scale=3, width=1000, height=600)


# save_chart_path(foundry, defect_type, "monthly_rejection", plot_path, engine)


# reference_period = get_reference_period(foundry, defect_type, engine)

# if reference_period:
#     # Ensure reference_period is a list with two valid dates
#     if isinstance(reference_period, list) and len(reference_period) == 2:
#         reference_start, reference_end = reference_period
#     else:
#         raise ValueError(f"Invalid reference period format: {reference_period}")

#     config_path = os.path.join(jsonpath, "config.json")
#     with open(config_path, "r") as f:
#         config_data = json.load(f)

#     config_data["data_selection"]["reference_period"] = [reference_start, reference_end]

#     with open(config_path, "w") as f:
#         json.dump(config_data, f, indent=4)

#     print(f"Updated reference period to: [{reference_start}, {reference_end}]")

# if reference_period:
   
#     reference_date = pd.to_datetime(reference_period, format="%Y-%m")
#     reference_start = reference_date.strftime("%Y-%m-01")
#     reference_end = (reference_date + pd.DateOffset(months=1) - pd.DateOffset(days=1)).strftime("%Y-%m-%d")

#     config_path = os.path.join(jsonpath, "config.json")
#     with open(config_path, "r") as f:
#         config_data = json.load(f)

#     config_data["data_selection"]["reference_period"] = [reference_start, reference_end]

#     with open(config_path, "w") as f:
#         json.dump(config_data, f, indent=4)

#     print(f" Updated reference period to: [{reference_start}, {reference_end}]")


total_production_col = config_file.get("total_produced_qty", "Total Quantity Produced (no)")


rejection_file = [file for file in os.listdir(datapath) if "Rejection" in file and file.endswith(".xlsx")]
if not rejection_file:
    raise FileNotFoundError("No Rejection Data file found.")

rejection_data = pd.read_excel(os.path.join(datapath, rejection_file[0]), skiprows=5)
rejection_data.columns = rejection_data.columns.str.strip()

date_column = "Production Date"
time_format = "%b-%Y"
rejection_data[date_column] = pd.to_datetime(rejection_data[date_column])
rejection_data["Year-Month"] = rejection_data[date_column].dt.strftime(time_format)

if total_production_col not in rejection_data.columns:
    raise KeyError(f"Missing required column: '{total_production_col}' in rejection data.")

for col in defect_columns:
    if col not in rejection_data.columns:
        raise KeyError(f"Missing required defect column: '{col}' in rejection data.")

defect_rejection_col = f"Total {defect_type} Rejection"
rejection_data[defect_rejection_col] = rejection_data[defect_columns].sum(axis=1)


monthly_rejection = (
    rejection_data.groupby("Year-Month").agg({
        defect_rejection_col: "sum",
        total_production_col: "sum"
    }).reset_index()
)

monthly_rejection["Rejection Percentage"] = (
    (monthly_rejection[defect_rejection_col] / monthly_rejection[total_production_col]) * 100
)


# # monthly_rejection["Year-Month"] = pd.to_datetime(monthly_rejection["Year-Month"], format=time_format)
# monthly_rejection["Year-Month"] = pd.to_datetime(monthly_rejection["Year-Month"], format="%b-%Y").dt.strftime("%Y-%m")  
# monthly_rejection = monthly_rejection.sort_values("Year-Month")
# monthly_rejection["Year-Month"] = monthly_rejection["Year-Month"].dt.strftime(time_format)
monthly_rejection["Year-Month"] = pd.to_datetime(monthly_rejection["Year-Month"], errors="coerce", format="%b-%Y")

monthly_rejection = monthly_rejection.sort_values("Year-Month")

monthly_rejection["Year-Month"] = monthly_rejection["Year-Month"].dt.strftime("%b-%Y")

save_data_to_sql(foundry,"rejection_analysis", monthly_rejection, engine, config_file)


excel_path = os.path.join(results_dir, f"monthly_rejection_{defect_type}.xlsx")
monthly_rejection.to_excel(excel_path, index=False)

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
    labels={"Rejection Percentage": "Percentage of Total Production"},
    title=f"Sand Defects * Rejection (%) over Period [ {defect_type} ]",
    color="Rejection Percentage",
    color_continuous_scale="Blues"
)

fig.update_xaxes(title_text="Month", tickangle=-45)
fig.update_traces(texttemplate='%{text:.2f}%', textposition="outside")
# fig.show()

plot_path = os.path.join(results_dir, f"monthly_rejection_rate_{defect_type}.jpeg")
pio.write_image(fig, plot_path, format="jpeg", scale=3, width=1000, height=600)


save_chart_path(foundry, defect_type, "monthly_rejection", plot_path, engine)

#######################################################################################################################################################################

temp_dir = os.path.join(results_dir, "temp")
excel_path = os.path.join(results_dir, f"monthly_rejection_{defect_type}.xlsx")
monthly_rejection = pd.read_excel(excel_path)

if "Year-Month" not in monthly_rejection.columns or "Rejection Percentage" not in monthly_rejection.columns:
    raise KeyError("Missing required columns in monthly_rejection_data.xlsx")

lowest_rejection_month = monthly_rejection.loc[monthly_rejection["Rejection Percentage"].idxmin(), "Year-Month"]

lowest_rejection_date = pd.to_datetime(lowest_rejection_month, format="%b-%Y")
reference_start = lowest_rejection_date.strftime("%Y-%m-01")
reference_end = (lowest_rejection_date + pd.DateOffset(months=1) - pd.DateOffset(days=1)).strftime("%Y-%m-%d")

config_path = os.path.join(jsonpath, "config.json")
with open(config_path, "r") as f:
    config_data = json.load(f)

config_data["data_selection"]["reference_period"] = [reference_start, reference_end]

with open(config_path, "w") as f:
    json.dump(config_data, f, indent=4)

reference_period = get_reference_period(foundry, defect_type, engine)

with open(config_path, "w") as f:
    json.dump(config_data, f, indent=4)
#############################################################################################################################################################3


with open(config_path, "r") as f:
    config_data1 = json.load(f)  


data_for_analysis, opt_bin =get_data_for_analysis(prepared_sand_data,rejection_data,config_data1, analysis_frequency)

# create_analysis_table(engine)
# save_analysis_data(foundry, defect_type,data_for_analysis, engine)


df = pd.concat([data_for_analysis["ref_data"], data_for_analysis["comp_data"]])
df.sort_values(["Date","Shift"],ascending=True,inplace = True)
df = df.round(2)
df.to_excel(os.path.join(results_dir,config_file['component_for_analysis'][0]+"_"+config_file['defect_for_analysis']+".xlsx"),index = False)


df = pd.concat([data_for_analysis["ref_data"], data_for_analysis["comp_data"]])
df.sort_values(["Date", "Shift"], ascending=True, inplace=True)
df = df.round(2)

comparison_dir = os.path.join("data", foundry, "comparison")
os.makedirs(comparison_dir, exist_ok=True)

ref_data_path = os.path.join(comparison_dir, f"{config_file['component_for_analysis'][0]}_{config_file['defect_for_analysis']}_ref.xlsx")
comp_data_path = os.path.join(comparison_dir, f"{config_file['component_for_analysis'][0]}_{config_file['defect_for_analysis']}_comp.xlsx")

data_for_analysis["ref_data"].to_excel(ref_data_path, index=False)  
data_for_analysis["comp_data"].to_excel(comp_data_path, index=False) 



if (data_for_analysis["ref_data"].shape[0] <= config_file["data_sufficiency_check"]["ref_data"]):
    raise RuntimeError("Less data points in reference period for statisitcal analysis") 

if (data_for_analysis["comp_data"].shape[0] <= config_file["data_sufficiency_check"]["comp_data"]):
    raise RuntimeError("Less data points in comparison period for statisitcal analysis") 

result_dir = os.path.join(results_dir, "temp")

if data_for_analysis["ref_data"].empty or data_for_analysis["comp_data"].empty:
    print("No data available for plotting.")


dist_dict, plot_data, dist_labels, div_data_dict, div_dict= dist_plot(data_for_analysis,config_data1,analysis_frequency,results_dir=result_dir,show_plot=True)
                                                                              
box_dict, summary_dict = box_plot(data_for_analysis,config_data1,analysis_frequency, show_plot=True,results_dir=result_dir)

corr_dict, corr_labels = correlation_plot(data_for_analysis,config_data1,analysis_frequency, show_plot=True, results_dir=result_dir)


summary_table = pd.DataFrame(columns=["Parameters", "Absolute Change (%)"])
summary_table["Parameters"] = list(summary_dict.keys())
summary_table["Absolute Change (%)"] = list(summary_dict.values())
summary_table.sort_values(by="Absolute Change (%)", ascending=False, inplace=True)

insert_summary_to_db(foundry, defect_type, summary_dict, engine)
summary_table.to_excel(os.path.join(results_dir,"summary_table.xlsx"),index=False)


outlier_dict = outlier_calc(box_dict)
outliers = find_outliers(outlier_dict, box_dict)

df = pd.concat([data_for_analysis["ref_data"], data_for_analysis["comp_data"]])
# df.to_excel(os.path.join(results_dir,config_file['component_for_analysis']+"_"+config_file['defect_for_analysis']+".xlsx"))

component_name=config_file['component_for_analysis'][0] if isinstance(config_file['component_for_analysis'],list) else config_file['component_for_analysis']

df.to_excel(os.path.join(results_dir,f"{component_name}_{config_file['defect_for_analysis']}.xlsx"))

# ################################################################################################################################################################################

import pandas as pd
import plotly.express as px
import os
import plotly.io as pio

summary_table_path = os.path.join(results_dir, "summary_table.xlsx")
summary_table = pd.read_excel(summary_table_path)

if "Parameters" not in summary_table.columns or "Absolute Change (%)" not in summary_table.columns:
    raise KeyError("Missing required columns: 'Parameters' and 'Absolute Change (%)' in summary_table.xlsx")

summary_table = summary_table.sort_values(by="Absolute Change (%)", ascending=False)

fig = px.bar(
    summary_table,
    x="Parameters",
    y="Absolute Change (%)",
    orientation="v",
    text="Absolute Change (%)",
    hover_data={"Parameters": True, "Absolute Change (%)": ":.2f"},
    labels={"Absolute Change (%)": "Percentage Change"},
    title="Summary Table: Absolute Change (%) by Parameter",
    color="Absolute Change (%)",
    color_continuous_scale="Blues"
)

fig.update_traces(texttemplate='%{text:.2f}%', textposition="outside")
# fig.show()

temp_dir = os.path.join(results_dir, "temp")
os.makedirs(temp_dir, exist_ok=True)

summary_plot_path = os.path.join(result_dir, "summary_table_plot.jpeg")
pio.write_image(fig, summary_plot_path, format="jpeg", scale=3, width=1000, height=600)

# # # ##########################################################################################################################################################

