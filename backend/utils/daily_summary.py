# from sqlalchemy import text
# import pandas as pd
# import os

# def generate_daily_rejection_summary(engine, foundry, config_file):
#     rejection_df = pd.read_sql("SELECT * FROM rejection_data", con=engine)
#     rejection_df.columns = rejection_df.columns.str.strip().str.lower()

#     rejection_df["date"] = pd.to_datetime(rejection_df["date"])
#     total_production_col = config_file["total_produced_qty"]
#     defect_type = config_file["defect_for_analysis"]
#     component_col = "component_id"
#     group_map = config_file.get("group", {})
    
#     defect_cols = config_file.get("defect_mapping", {}).get(defect_type, [])
#     if not defect_cols:
#         raise ValueError(f"Missing defect mapping for: {defect_type}")

#     rejection_df[f"{defect_type}_rejection"] = rejection_df[defect_cols].sum(axis=1)

#     if config_file.get("group_wise_analysis"):
#         group = config_file["group_for_analysis"]
#         allowed_components = group_map.get(group, [])
#         rejection_df = rejection_df[rejection_df[component_col].astype(str).isin(allowed_components)]
#         rejection_df["group_name"] = group
#     else:
#         rejection_df["group_name"] = None

#     if config_file.get("component_wise_analysis"):
#         components = config_file["component_for_analysis"]
#         rejection_df = rejection_df[rejection_df[component_col].astype(str).isin(components)]
#     else:
#         rejection_df["component_id"] = None

#     grouped = rejection_df.groupby(
#         ["date", "group_name", "component_id"]
#     ).agg(
#         total_production=(total_production_col, "sum"),
#         total_rejection=(f"{defect_type}_rejection", "sum")
#     ).reset_index()

#     grouped["defect_type"] = defect_type
#     grouped["foundry_name"] = foundry
#     grouped["rejection_percentage"] = (grouped["total_rejection"] / grouped["total_production"]) * 100

#     final_cols = [
#         "foundry_name", "defect_type", "date", "group_name", "component_id",
#         "total_production", "total_rejection", "rejection_percentage"
#     ]
#     grouped = grouped[final_cols]

#     grouped.to_sql("daily_rejection_analysis", con=engine, if_exists="append", index=False)

#     return grouped
