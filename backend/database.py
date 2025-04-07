from sqlalchemy import create_engine, text
from datetime import datetime
from dateutil.relativedelta import relativedelta
from sqlalchemy import text, inspect
import pandas as pd 
import numpy as np
import re
import os
import json
from dateutil.relativedelta import relativedelta

DATABASE_URI = "mysql+mysqlconnector://root:Password%40123@localhost/foundry_db"

def get_engine():
    return create_engine(DATABASE_URI)

def connect_db():
    try:
        engine = get_engine()
        conn = engine.connect()
        return engine
    except Exception as e:
        raise ValueError(f"SQLAlchemy Connection Failed: {e}")

def close_db(connection):
    connection.close()
 

def get_mysql_table(table_name):
    """
    Reads a table from MySQL database using SQLAlchemy and returns a DataFrame.
    
    Args:
        table_name (str): The name of the MySQL table to fetch.

    Returns:
        pd.DataFrame: DataFrame containing the data from the MySQL table.
    """
    try:
        engine = connect_db()
        df = pd.read_sql_table(table_name, con=engine)
        return df
        
    except Exception as e:
        raise RuntimeError(f"Error reading table '{table_name}': {e}")



def insert_data_to_mysql(df, foundry, defect, table_type):
    engine = get_engine()
    table_name = f"{table_type}_analysis_data"

    df = df.copy()
    df["Foundry"] = foundry
    df["DefectType"] = defect

    if "Shift" not in df.columns:
        df["Shift"] = "NA"

    for col in df.columns:
        if df[col].astype(object).map(lambda x: isinstance(x, pd._libs.interval.Interval)).any():
            df[col] = df[col].astype(str)

    inspector = inspect(engine)

    with engine.begin() as connection:
        if not inspector.has_table(table_name):
            df.to_sql(table_name, con=connection, index=False, if_exists='replace')
            print(f" Table created and data inserted: {table_name}")
        else:
            existing_columns = [col["name"] for col in inspector.get_columns(table_name)]

            new_columns = [col for col in df.columns if col not in existing_columns]

            for col in new_columns:
                dtype = "TEXT"
                sample = df[col].dropna().iloc[0] if not df[col].dropna().empty else ""
                if isinstance(sample, (int, float, np.integer, np.floating)):
                    dtype = "DOUBLE"
                elif isinstance(sample, pd.Timestamp) or "Date" in col:
                    dtype = "DATE"
                alter_stmt = text(f"ALTER TABLE `{table_name}` ADD COLUMN `{col}` {dtype}")
                try:
                    connection.execute(alter_stmt)
                    print(f" Added column `{col}` to `{table_name}`")
                except Exception as e:
                    print(f"Could not add column `{col}`: {e}")

            try:
                dedup_query = f"SELECT Foundry, DefectType, Date, Shift FROM `{table_name}`"
                with engine.connect() as conn:
                    existing_df = pd.read_sql(text(dedup_query), con=conn)

                df = df[~df.set_index(["Foundry", "DefectType", "Date", "Shift"]).index.isin(
                    existing_df.set_index(["Foundry", "DefectType", "Date", "Shift"]).index
                )]

                if not df.empty:
                    df.to_sql(table_name, con=connection, index=False, if_exists='append')
                    print(f" New rows inserted into: {table_name}")
                else:
                    print(f" No new rows to insert for: {table_name}")
            except Exception as e:
                raise RuntimeError(f" Failed inserting into MySQL: {e}")

def insert_mad_data( foundry, defect_type,mad_values_dict, engine):
    rows = []

    for parameter, value in mad_values_dict.items():
        rows.append({
            "Parameter": parameter,
            "Value": value,
            "Period": None,  # or set the period if you want to track it
            "Foundry": foundry,
            "Defect": defect_type
        })

    mad_df = pd.DataFrame(rows)
    mad_df.to_sql("mad_analysis_data", con=engine, if_exists="append", index=False)
    print("MAD data inserted successfully.")


def save_data_to_sql(foundry, table_name, data, engine, config_file):
    defect_type = config_file.get("defect_for_analysis", "Unknown Defect")
    groupwise_enabled = config_file.get("group_wise_analysis", False)
    componentwise_enabled = config_file.get("component_wise_analysis", False)
    group_name = config_file.get("group_for_analysis", "")
    component_list = config_file.get("component_for_analysis", [])

    with engine.connect() as conn:
        for _, row in data.iterrows():
            group_value = None
            component_value = None

            if groupwise_enabled:
                group_value = group_name or None
            if componentwise_enabled:
                component_value = row.get("component_id", None) or (
                    component_list[0] if len(component_list) == 1 else component_list
                )

            sql = text(f"""
                INSERT INTO {table_name} (
                    foundry_name, defect_type, month_year,
                    group_name, component_id,
                    total_rejection, total_production, rejection_percentage
                ) VALUES (
                    :foundry_name, :defect_type, :month_year,
                    :group_name, :component_id,
                    :total_rejection, :total_production, :rejection_percentage
                )
                ON DUPLICATE KEY UPDATE 
                    total_rejection = VALUES(total_rejection),
                    total_production = VALUES(total_production),
                    rejection_percentage = VALUES(rejection_percentage),
                    group_name = VALUES(group_name),
                    component_id = VALUES(component_id)
            """)

            conn.execute(sql, {
                "foundry_name": foundry,
                "defect_type": defect_type,
                "month_year": row["Year-Month"],
                "group_name": group_value,
                "component_id": component_value,
                "total_rejection": row["Total " + defect_type + " Rejection"],
                "total_production": row["total_quantity_produced"],
                "rejection_percentage": row["Rejection Percentage"]
            })

        conn.commit()



def save_chart_path(foundry, defect_type, chart_type, file_path, engine):
    with engine.connect() as conn:
        sql = text("""
            INSERT INTO chart_paths (foundry_name, defect_type, chart_type, file_path)
            VALUES (:foundry, :defect_type, :chart_type, :file_path)
            ON DUPLICATE KEY UPDATE 
                file_path = VALUES(file_path),
                created_at = CURRENT_TIMESTAMP;
        """)
        conn.execute(sql, {
            "foundry": foundry,
            "defect_type": defect_type,
            "chart_type": chart_type,
            "file_path": file_path
        })
        conn.commit()



def get_comparison_period(foundry, defect_type, engine):
    """Retrieve the latest rejection month from the database and return start & end dates."""
    try:
        query = text("""
            SELECT month_year FROM rejection_analysis
            WHERE foundry_name = :foundry AND defect_type = :defect_type
            ORDER BY STR_TO_DATE(month_year, '%b-%Y') DESC LIMIT 1
        """)

        with engine.connect() as conn:
            result = conn.execute(query, {"foundry": foundry, "defect_type": defect_type}).fetchone()

        if result:
            latest_month = result[0]
            latest_date = datetime.strptime(latest_month, "%b-%Y")
            comparison_start = latest_date.strftime("%Y-%m-01")
            comparison_end = (latest_date + relativedelta(months=1) - relativedelta(days=1)).strftime("%Y-%m-%d")
            return [comparison_start, comparison_end]

    except Exception as e:
        raise ValueError(f"Error retrieving comparison period: {e}")


def get_reference_period(foundry, defect_type, engine):
    """Retrieve the lowest rejection month from the database and return start & end dates."""
    try:
        query = text("""
            SELECT month_year FROM rejection_analysis
            WHERE foundry_name = :foundry AND defect_type = :defect_type
            ORDER BY rejection_percentage ASC LIMIT 1
        """)

        with engine.connect() as conn:
            result = conn.execute(query, {"foundry": foundry, "defect_type": defect_type}).fetchone()

        if result:
            reference_month = result[0]  

            reference_date = datetime.strptime(reference_month, "%b-%Y")
            reference_start = reference_date.strftime("%Y-%m-01")
            reference_end = (reference_date + relativedelta(months=1) - relativedelta(days=1)).strftime("%Y-%m-%d")
            return [reference_start, reference_end]  

    except Exception as e:
        raise ValueError(f"Error retrieving reference period: {e}")

#######################################################################################################################


def insert_prepared_sand_data(foundry, engine, df):
    table_name = "prepared_sand_data"

    df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]
    df.columns = [col.replace("(", "").replace(")", "").replace(",", "").replace("%", "").replace("-", "_").strip("_") for col in df.columns]

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    if "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"], format="%H:%M:%S", errors="coerce").dt.time

    with engine.connect() as conn:
        result = conn.execute(text(f"SHOW COLUMNS FROM {table_name}"))
        sql_columns = [row[0] for row in result.fetchall() if row[0] != "pkey"]

    for col in sql_columns:
        if col not in df.columns:
            df[col] = None

    df = df[[col for col in df.columns if col in sql_columns]]

    for col in df.columns:
        if col not in ["date", "time", "shift", "heat_no", "component_id", "created_by", "last_updated_by", "created_on", "last_updated_on"]:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        elif col in ["created_on", "last_updated_on"]:
            df[col] = pd.to_datetime(df[col], errors='coerce')
        elif col == "deleted":
            df[col] = df[col].fillna(0).astype(int)

    for col in df.select_dtypes(include=["float64", "int64"]).columns:
        df[col] = df[col].fillna(0.0)

    insert_cols = ", ".join(f"`{col}`" for col in df.columns)
    insert_vals = ", ".join(f":{col}" for col in df.columns)

    insert_sql = text(f"INSERT INTO {table_name} ({insert_cols}) VALUES ({insert_vals})")

    try:
        with engine.begin() as conn:
            conn.execute(insert_sql, df.to_dict(orient="records"))
            print(f"Inserted {len(df)} rows into {table_name}")
    except Exception as e:
        print(f"Error inserting into {table_name}: {e}")


#####################################################################################################################


def insert_rejection_data(foundry, engine, rejection_data):
    """
    Inserts cleaned rejection data into the `rejection_data` SQL table.

    Parameters:
    - foundry: str, name of the foundry (not used directly here but reserved for filtering)
    - engine: SQLAlchemy engine
    - rejection_data: DataFrame loaded from Excel with columns matching the rejection_data table
    """

    table_name = "rejection_data"


    rejection_data.columns = [re.sub(r"[^a-zA-Z0-9_]", "_", col).strip("_") for col in rejection_data.columns]


    if "pkey" in rejection_data.columns:
        rejection_data.drop(columns=["pkey"], inplace=True)

    with engine.connect() as conn:
        result = conn.execute(text(f"SHOW COLUMNS FROM {table_name}"))
        sql_columns = [row[0] for row in result.fetchall()]

    sql_columns = [col for col in sql_columns if col != "pkey"] 

    for col in sql_columns:
        if col not in rejection_data.columns:
            rejection_data[col] = None

    rejection_data = rejection_data[sql_columns]

    for col in rejection_data.columns:
        if rejection_data[col].dtype in [float, int]:
            rejection_data[col] = rejection_data[col].fillna(0)
        else:
            rejection_data[col] = rejection_data[col].fillna("")

    insert_cols = ", ".join([f"`{col}`" for col in sql_columns])
    insert_vals = ", ".join([f":{col}" for col in sql_columns])

    insert_sql = text(f"""
        INSERT INTO {table_name} ({insert_cols})
        VALUES ({insert_vals})
    """)

    # Insert data
    with engine.begin() as conn:
        conn.execute(insert_sql, rejection_data.to_dict(orient="records"))

    print(f"Successfully inserted {len(rejection_data)} rows into '{table_name}'.")


#####################################################################################################################



def generate_daily_rejection_summary(engine, foundry, config_file):
    from sqlalchemy import text
    import pandas as pd

    # Step 1: Load data
    with engine.connect() as conn:
        rejection_df = pd.read_sql(text("SELECT * FROM rejection_data"), con=conn)

    rejection_df.columns = rejection_df.columns.str.strip().str.lower()
    rejection_df["date"] = pd.to_datetime(rejection_df["date"])

    # Step 2: Pull config params
    defect_type = config_file["defect_for_analysis"]
    defect_cols = config_file["defect_mapping"].get(defect_type, [])
    component_col = "component_id"
    group_map = config_file.get("group", {})
    total_production_col = config_file["total_produced_qty"]

    # Step 3: Calculate defect rejection
    rejection_df[f"{defect_type}_rejection"] = rejection_df[defect_cols].sum(axis=1)

    # Step 4: Filter by group/component
    if config_file.get("group_wise_analysis"):
        group_name = config_file["group_for_analysis"]
        allowed_components = group_map.get(group_name, [])
        rejection_df = rejection_df[rejection_df[component_col].astype(str).isin(allowed_components)]
        rejection_df["group_name"] = group_name
    else:
        rejection_df["group_name"] = None

    if config_file.get("component_wise_analysis"):
        components = config_file.get("component_for_analysis", [])
        rejection_df = rejection_df[rejection_df[component_col].astype(str).isin(components)]
    # Note: Do NOT drop component_id. It’s still used for group analysis.

    # Ensure shift exists
    if "shift" not in rejection_df.columns:
        rejection_df["shift"] = None

    # Step 5: Group and aggregate
    grouped = rejection_df.groupby(["date", "shift", "group_name", "component_id"]).agg(
        total_production=(total_production_col, "sum"),
        total_rejection=(f"{defect_type}_rejection", "sum")
    ).reset_index()

    # Step 6: Additional fields
    grouped["defect_type"] = defect_type
    grouped["foundry_name"] = foundry
    grouped["rejection_percentage"] = (grouped["total_rejection"] / grouped["total_production"]) * 100

    # Final Column Order
    final_cols = [
        "foundry_name", "defect_type", "date", "shift", "group_name", "component_id",
        "total_production", "total_rejection", "rejection_percentage"
    ]
    grouped = grouped[final_cols]

    # Step 7: Insert into DB
    with engine.begin() as conn:
        for _, row in grouped.iterrows():
            row_data = row.to_dict()
            conn.execute(text("""
                INSERT INTO daily_rejection_analysis (
                    foundry_name, defect_type, date, shift, group_name, component_id,
                    total_production, total_rejection, rejection_percentage
                ) VALUES (
                    :foundry_name, :defect_type, :date, :shift, :group_name, :component_id,
                    :total_production, :total_rejection, :rejection_percentage
                )
                ON DUPLICATE KEY UPDATE
                    total_production = VALUES(total_production),
                    total_rejection = VALUES(total_rejection),
                    rejection_percentage = VALUES(rejection_percentage)
            """), row_data)

    print(f"[S] Inserted {len(grouped)} rows into daily_rejection_analysis.")
    return grouped


####################################################################################################################3


def update_config_periods(foundry, defect_type, jsonpath, results_dir, user_query):
    config_path = os.path.join(jsonpath, "config.json")

    with open(config_path, "r") as f:
        config_data = json.load(f)

    excel_path = os.path.join(results_dir, f"monthly_rejection_{defect_type}.xlsx")
    monthly_rejection = pd.read_excel(excel_path)

    if "Year-Month" not in monthly_rejection.columns or "Rejection Percentage" not in monthly_rejection.columns:
        raise KeyError("Missing required columns in monthly_rejection_data.xlsx")
    

    lowest_rejection_month = monthly_rejection.loc[monthly_rejection["Rejection Percentage"].idxmin(), "Year-Month"]
    lowest_rejection_date = pd.to_datetime(lowest_rejection_month, format="%b-%Y")
    reference_start = lowest_rejection_date.strftime("%Y-%m-01")
    reference_end = (lowest_rejection_date + pd.DateOffset(months=1) - pd.DateOffset(days=1)).strftime("%Y-%m-%d")

    comparison_start, comparison_end = None, None

    if user_query and "compare" in user_query.lower():
        words = user_query.split()
        for i, word in enumerate(words):
            try:
                comparison_date = datetime.strptime(f"{words[i]}-{words[i+1]}", "%b-%Y")
                comparison_start = comparison_date.strftime("%Y-%m-01")
                comparison_end = (comparison_date + relativedelta(months=1) - relativedelta(days=1)).strftime("%Y-%m-%d")
                break
            except (ValueError, IndexError):
                continue
    else:
        latest_rejection_month = monthly_rejection["Year-Month"].iloc[-1]
        latest_rejection_date = pd.to_datetime(latest_rejection_month, format="%b-%Y")
        comparison_start = latest_rejection_date.strftime("%Y-%m-01")
        comparison_end = (latest_rejection_date + pd.DateOffset(months=1) - pd.DateOffset(days=1)).strftime("%Y-%m-%d")

    config_data["data_selection"]["reference_period"] = [reference_start, reference_end]
    config_data["data_selection"]["comparison_period"] = [comparison_start, comparison_end]

    with open(config_path, "w") as f:
        json.dump(config_data, f, indent=4)

    if reference_start == comparison_start and reference_end == comparison_end:
        print("🎉 Achievement Unlocked: This month has the lowest rejection in recent times!")


# =================== DEFECT-WISE COLUMN MAPPINGS =================== #

defect_columns = {
    "Blow Hole": [
        'Date', 'Shift', 'Compactability (%)', 'Permeability (no)', 'Volatile Matter (%)',
        'Inert Fines (%)', 'Moisture (%)', 'Active Clay (%)', 'LOI (%)', 'Blow Hole %',
        'Permeability (no)_bins', 'Inert Fines (%)_bins', 'Compactability (%)_bins',
        'Moisture (%)_bins', 'Active Clay (%)_bins', 'LOI (%)_bins'
    ],
    "Total rejection": [
        'Date', 'Shift', 'LOI (%)', 'Permeability (no)', 'Moisture (%)', 'GCS (gm/cm2)',
        'Compactability (%)', 'Wet Tensile Strength (N/cm2)', 'GFN/AFS (no)', 'Inert Fines (%)',
        'Volatile Matter (%)', 'Active Clay (%)', 'Total rejection %', 'LOI (%)_bins',
        'Permeability (no)_bins', 'Moisture (%)_bins', 'GCS (gm/cm2)_bins', 'Compactability (%)_bins',
        'Wet Tensile Strength (N/cm2)_bins', 'GFN/AFS (no)_bins', 'Inert Fines (%)_bins',
        'Active Clay (%)_bins'
    ],
    "Broken Mould": [
        'Date', 'Shift', 'Compactability (%)', 'Moisture (%)', 'GCS (gm/cm2)',
        'Active Clay (%)', 'Broken Mould %', 'Moisture (%)_bins', 'Compactability (%)_bins',
        'GCS (gm/cm2)_bins', 'Active Clay (%)_bins'
    ],
    "Mould Swell": [
        'Date', 'Shift', 'Inert Fines (%)', 'GCS (gm/cm2)', 'Moisture (%)',
        'Compactability (%)', 'Active Clay (%)', 'Mould Swell %',
        'Inert Fines (%)_bins', 'GCS (gm/cm2)_bins', 'Moisture (%)_bins',
        'Compactability (%)_bins', 'Active Clay (%)_bins'
    ],
    "Sand Fusion": [
        'Date', 'Shift', 'GFN/AFS (no)', 'Inert Fines (%)', 'Permeability (no)',
        'Moisture (%)', 'LOI (%)', 'Sand Fusion %', 'GFN/AFS (no)_bins',
        'Inert Fines (%)_bins', 'Permeability (no)_bins', 'Moisture (%)_bins',
        'LOI (%)_bins'
    ],
    "Sand Inclusion defect": [
        'Date', 'Shift', 'Compactability (%)', 'Inert Fines (%)', 'GCS (gm/cm2)',
        'Moisture (%)', 'Active Clay (%)', 'Sand Inclusion defect %',
        'Compactability (%)_bins', 'Inert Fines (%)_bins', 'GCS (gm/cm2)_bins',
        'Moisture (%)_bins', 'Active Clay (%)_bins'
    ]
}


# =================== TABLE CREATION FUNCTION =================== #

def create_analysis_table(engine):
    """Creates the `analysis_data` table with all necessary columns."""
    create_table_sql = text("""
        CREATE TABLE IF NOT EXISTS analysis_data (
            id INT AUTO_INCREMENT PRIMARY KEY,
            foundry VARCHAR(50) NOT NULL,
            defect_type VARCHAR(50) NOT NULL,
            data_type VARCHAR(50) NOT NULL,
            Date DATE NULL,
            Shift VARCHAR(10) NULL,
            `LOI (%)` FLOAT NULL,
            `Permeability (no)` FLOAT NULL,
            `Moisture (%)` FLOAT NULL,
            `GCS (gm/cm2)` FLOAT NULL,
            `Compactability (%)` FLOAT NULL,
            `Wet Tensile Strength (N/cm2)` FLOAT NULL,
            `GFN/AFS (no)` FLOAT NULL,
            `Inert Fines (%)` FLOAT NULL,
            `Volatile Matter (%)` FLOAT NULL,
            `Active Clay (%)` FLOAT NULL,
            `Blow Hole %` FLOAT NULL,
            `Broken Mould %` FLOAT NULL,
            `Sand Fusion %` FLOAT NULL,
            `Mould Swell %` FLOAT NULL,
            `Sand Inclusion Defect %` FLOAT NULL,
            `Total rejection %` FLOAT NULL,
            `LOI (%)_bins` VARCHAR(20) NULL,
            `Permeability (no)_bins` VARCHAR(20) NULL,
            `Moisture (%)_bins` VARCHAR(20) NULL,
            `GCS (gm/cm2)_bins` VARCHAR(20) NULL,
            `Compactability (%)_bins` VARCHAR(20) NULL,
            `Wet Tensile Strength (N/cm2)_bins` VARCHAR(20) NULL,
            `GFN/AFS (no)_bins` VARCHAR(20) NULL,
            `Inert Fines (%)_bins` VARCHAR(20) NULL,
            `Active Clay (%)_bins` VARCHAR(20) NULL,
            UNIQUE KEY (`foundry`, `defect_type`, `data_type`, `Date`, `Shift`)
        )
    """)
    
    with engine.connect() as conn:
        conn.execute(create_table_sql)
        conn.commit()
        print(" Table `analysis_data` created successfully!")




# =================== DATA INSERTION FUNCTION =================== #
import pandas as pd
import numpy as np
from sqlalchemy import text

def save_analysis_data(foundry, defect_type, data_for_analysis, engine):
    """
    Insert multiple analysis types (reference, comparison) from `data_for_analysis` dictionary into `analysis_data`.
    """

    required_columns = [
        "foundry", "defect_type", "data_type", "Date", "Shift", "LOI (%)", "Permeability (no)", "Moisture (%)",
        "GCS (gm/cm2)", "Compactability (%)", "Wet Tensile Strength (N/cm2)", "GFN/AFS (no)", "Inert Fines (%)",
        "Volatile Matter (%)", "Active Clay (%)", "Blow Hole %", "Broken Mould %", "Sand Fusion %",
        "Mould Swell %", "Sand Inclusion Defect %", "Total rejection %", "LOI (%)_bins", "Permeability (no)_bins",
        "Moisture (%)_bins", "GCS (gm/cm2)_bins", "Compactability (%)_bins", "Wet Tensile Strength (N/cm2)_bins",
        "GFN/AFS (no)_bins", "Inert Fines (%)_bins", "Active Clay (%)_bins"
    ]
  
    for data_type, df in data_for_analysis.items():
        if df.empty:
            print(f" No data available for {data_type}. Skipping insert.")
            continue

        df["foundry"] = foundry
        df["defect_type"] = defect_type
        df["data_type"] = data_type

        for col in required_columns:
            if col not in df.columns:
                df[col] = None  

        df = df[required_columns]

        df.replace({np.nan: None}, inplace=True)
   
        columns = ", ".join(f"`{col}`" for col in required_columns)
        values = ", ".join(f":{col}" for col in required_columns)

        update_columns = [col for col in required_columns if col not in ["foundry", "defect_type", "data_type", "Date", "Shift"]]
        update_values = ", ".join(f"`{col}` = VALUES(`{col}`)" for col in update_columns)

        sql = text(f"""
            INSERT INTO analysis_data ({columns})
            VALUES ({values})
            ON DUPLICATE KEY UPDATE {update_values}
        """)

        with engine.connect() as conn:
            try:
                data_dicts = df.to_dict(orient="records")
                conn.execute(sql, data_dicts)
                conn.commit()
                print(f" Successfully inserted {len(df)} rows for `{defect_type}` [{data_type}].")
            except Exception as e:
                print(f" Error inserting into `analysis_data`: {e}")


def insert_summary_to_db(foundry_name, defect_type, summary_dict, engine):
    """
    Inserts or updates the summary table data into MySQL.
    """

    if not summary_dict:
        print(f" No data to insert for {defect_type} in {foundry_name}. Skipping...")
        return None
    

    summary_table = pd.DataFrame(columns=["Parameters", "Absolute Change (%)"])
    summary_table["Parameters"] = list(summary_dict.keys())
    summary_table["Absolute Change (%)"] = list(summary_dict.values())

    summary_table.sort_values(by="Absolute Change (%)", ascending=False, inplace=True)

    summary_table.replace({np.nan: 0}, inplace=True)

    with engine.connect() as conn:
        insert_query = text("""
            INSERT INTO summary_table (foundry_name, defect_type, parameter, absolute_change)
            VALUES (:foundry_name, :defect_type, :parameter, :absolute_change)
            ON DUPLICATE KEY UPDATE 
                absolute_change = VALUES(absolute_change),
                created_at = CURRENT_TIMESTAMP
        """)

        for _, row in summary_table.iterrows():
            conn.execute(insert_query, {
                "foundry_name": foundry_name,
                "defect_type": defect_type,
                "parameter": row["Parameters"],
                "absolute_change": row["Absolute Change (%)"]
            })

        conn.commit()
        print(f" Summary data for `{defect_type}` in `{foundry_name}` inserted/updated successfully.")







