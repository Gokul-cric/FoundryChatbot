# config_service.py

import os
import json
from models.groq_llm import GroqLLM

CONFIG_DIR = "Configfile"
llm = GroqLLM()

def load_config(foundry):
    config_path = os.path.join(CONFIG_DIR, foundry, "config.json")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"No config found for foundry '{foundry}'")

    with open(config_path, "r") as f:
        return json.load(f), config_path


def save_config(config, config_path):
    with open(config_path, "w") as f:
        json.dump(config, f, indent=4)


def update_defect_in_config(foundry, defect_type):
    try:
        config, config_path = load_config(foundry)
        config["defect_for_analysis"] = defect_type
        save_config(config, config_path)
        return True
    except Exception as e:
        print(f"Error updating defect in config: {e}")
        return False

def update_periods_from_query(user_query, foundry):
    try:
        config, config_path = load_config(foundry)

        # Check if the query has any date-related keyword
        date_keywords = [
            "compare", "reference", "period", "from", "between", "until",
            "vs", "versus", "comparing", "comparison", "on", "last month", "this month"
        ]
        if any(kw in user_query.lower() for kw in date_keywords):
            extracted = llm.extract_periods_from_query(user_query)

            if extracted:
                # Update reference and comparison periods
                if "reference_period" in extracted and extracted["reference_period"]:
                    config["data_selection"]["reference_period"] = extracted["reference_period"]
                if "comparison_period" in extracted and extracted["comparison_period"]:
                    config["data_selection"]["comparison_period"] = extracted["comparison_period"]

                # Validate and update group
                group = extracted.get("group_for_analysis")
                if group and group in config.get("group", {}):
                    config["group_for_analysis"] = group
                    config["group_wise_analysis"] = True
                    config["component_wise_analysis"] = False

                # Validate and update components
                valid_components = set(config.get("group", {}).get("All", []))
                extracted_components = extracted.get("component_for_analysis", [])

                if extracted_components and isinstance(extracted_components, list):
                    matched_components = [
                        comp for comp in extracted_components if comp in valid_components
                    ]
                    if matched_components:
                        config["component_for_analysis"] = matched_components
                        config["component_wise_analysis"] = True
                        config["group_wise_analysis"] = False

                save_config(config, config_path)
                print("Updated config from query:", extracted)
                return extracted

    except Exception as e:
        print(f" Error updating periods/group/components from query: {e}")

    return None


def update_group_for_analysis(foundry, group_name):
    try:
        config, config_path = load_config(foundry)
        config["group_for_analysis"] = group_name
        save_config(config, config_path)
        return True
    except Exception as e:
        print(f"Error updating group: {e}")
        return False


def update_component_filter(foundry, component_list):
    try:
        config, config_path = load_config(foundry)
        config["component_filter"] = component_list
        save_config(config, config_path)
        return True
    except Exception as e:
        print(f"Error updating component filter: {e}")
        return False


def update_top_n_components(foundry, n):
    try:
        config, config_path = load_config(foundry)
        config["top_n"] = int(n)
        save_config(config, config_path)
        return True
    except Exception as e:
        print(f"Error updating top_n: {e}")
        return False
