# from flask import Blueprint, request, jsonify
# from flask_cors import cross_origin
# import os
# import json
# import time
# import requests
# import calendar
# import pandas as  pd
# import re
# from sqlalchemy import text
# from database import connect_db
# from models.groq_llm import GroqLLM
# from utils.plot_generator import generate_rejection_trend_chart,generate_summary_chart
# from langchain_community.chat_message_histories import ChatMessageHistory
# from langchain.memory import ConversationBufferMemory
# from langchain_core.messages import HumanMessage, AIMessage
# import difflib


# chatbot_bp = Blueprint("chatbot", __name__)


# engine = connect_db()
# llm = GroqLLM()
# CONFIG_DIR = "Configfile"

# multi_turn_memory = {}

# def get_memory(session_id):
#     if session_id not in multi_turn_memory:
#         multi_turn_memory[session_id] = ConversationBufferMemory(
#             memory_key="chat_history",
#             return_messages=True
#         )
#     return multi_turn_memory[session_id]

# memory_store = {}


# FOUNDRIES = ["Munjal"]#"MCIE", "Munjal Line 1", "MMK", "AIW",
# DEFECT_TYPES = ["Blow Hole", "Sand Inclusion defect", "Erosion Scab", "Broken Mould", "Mould Swell", "Sand Fusion", "Total Rejection"]

# def get_foundry_memory(foundry_name: str) -> ChatMessageHistory:
#     """Retrieves or initializes memory for a specific foundry."""
#     if foundry_name not in memory_store:
#         memory_store[foundry_name] = ChatMessageHistory()
#     return memory_store[foundry_name]

# def expand_month_range_across_years(start_month, start_year, end_month, end_year):
#     """Expands range across months and possibly years (e.g., March 2022 to May 2023)."""
#     start_year = int(start_year)
#     end_year = int(end_year)
#     start_index = list(calendar.month_abbr).index(start_month[:3])
#     end_index = list(calendar.month_abbr).index(end_month[:3])

#     result = []
#     for year in range(start_year, end_year + 1):
#         month_start = start_index if year == start_year else 1
#         month_end = end_index if year == end_year else 12
#         for i in range(month_start, month_end + 1):
#             result.append((calendar.month_abbr[i], str(year)))
#     return result

# def extract_query_params(user_query, prev_foundry=None, prev_defect_type=None):
#     foundries = [ "Munjal"]#"MCIE", "Munjal Line 1", "MMK", "AIW",
#     defect_types = ["Blow Hole", "Sand Inclusion defect", "Erosion Scab", "Broken Mould", "Sand Fusion", "Mould Swell", "Total Rejection"]

#     sorted_foundries = sorted(foundries, key=lambda x: -len(x))
#     foundry = next((f for f in sorted_foundries if f.lower() in user_query.lower()), None)
#     defect_type = next((d for d in defect_types if d.lower() in user_query.lower()), None)

    

#     foundry = foundry or prev_foundry or "Munjal"
#     defect_type = defect_type or prev_defect_type

#     month_map = {m.lower(): calendar.month_abbr[i] for i, m in enumerate(calendar.month_name) if m}
#     month_map.update({calendar.month_abbr[i].lower(): calendar.month_abbr[i] for i in range(1, 13)})
#     month_map.update({str(i): calendar.month_abbr[i] for i in range(1, 13)})
#     month_map.update({f"{i:02}": calendar.month_abbr[i] for i in range(1, 13)})

#     months, year = [], None

#     user_query = re.sub(r"(\b\d{4})[\s\-]*(\b[a-z]{3,9}\b)", r"\2 \1", user_query, flags=re.IGNORECASE)

    
#     range_with_year = re.search(r"(\b[a-z]{3,9})\s*(?:to|and|-)\s*(\b[a-z]{3,9})\s+(\d{2,4})", user_query, re.IGNORECASE)
#     if range_with_year:
#         m1, m2, y = range_with_year.groups()
#         year = f"20{y}" if len(y) == 2 else y
#         months = expand_month_range_across_years(month_map[m1.lower()], year, month_map[m2.lower()], year)
#         return foundry, defect_type, [m for m, y in months], year

#     range_across_years = re.search(r"(\b[a-z]{3,9})\s+(\d{2,4})\s*(?:to|-)\s*(\b[a-z]{3,9})\s+(\d{2,4})", user_query, re.IGNORECASE)
#     if range_across_years:
#         m1, y1, m2, y2 = range_across_years.groups()
#         y1 = f"20{y1}" if len(y1) == 2 else y1
#         y2 = f"20{y2}" if len(y2) == 2 else y2
#         months = expand_month_range_across_years(month_map[m1.lower()], y1, month_map[m2.lower()], y2)
#         return foundry, defect_type, [m for m, y in months], None

#     all_year = re.search(r"all\s+periods\s+in\s+(\d{4})", user_query, re.IGNORECASE)
#     if all_year:
#         year = all_year.group(1)
#         return foundry, defect_type, list(calendar.month_abbr[1:]), year

#     matches = re.findall(r"\b([a-zA-Z]{3,9})\b(?:\s*['\-]?\s*(\d{2,4}))?", user_query, re.IGNORECASE)
#     for m, y in matches:
#         if m.lower() in month_map:
#             months.append(month_map[m.lower()])
#         elif difflib.get_close_matches(m.lower(), month_map.keys(), n=1, cutoff=0.75):
#             match = difflib.get_close_matches(m.lower(), month_map.keys(), n=1)[0]
#             months.append(month_map[match])
#         if y:
#             year = f"20{y}" if len(y) == 2 else y

#     if months:
#         return foundry, defect_type, list(set(months)), year

#     if not months and not year:
#         words = re.findall(r'\b[a-z]{3,9}\b', user_query.lower())
#         for word in words:
#             if word in month_map:
#                 return foundry, defect_type, [month_map[word]], None
#             close_match = difflib.get_close_matches(word, month_map.keys(), n=1, cutoff=0.75)
#             if close_match:
#                 return foundry, defect_type, [month_map[close_match[0]]], None

#     if not months:
#         year_only = re.search(r"\b(?:in\s+)?(\d{2,4})\b", user_query)
#         if year_only:
#             y = year_only.group(1)
#             year = f"20{y}" if len(y) == 2 else y
#             return foundry, defect_type, list(calendar.month_abbr[1:]), year

#     foundry = foundry or prev_foundry or "Munjal"
#     defect_type = defect_type or prev_defect_type
#     return foundry, defect_type, None, None


# def fetch_sql_data(foundry, defect_type, months=None, year=None):
#     base_query = """
#         SELECT month_year, rejection_percentage 
#         FROM rejection_analysis
#         WHERE foundry_name = :foundry AND defect_type = :defect_type
#     """
#     query_params = {"foundry": foundry, "defect_type": defect_type}

#     if months and year:
#         month_years = [f"{m}-{year}" for m in months]
#         base_query += " AND month_year IN ({})".format(
#             ", ".join([f":month_{i}" for i in range(len(month_years))])
#         )
#         for i, my in enumerate(month_years):
#             query_params[f"month_{i}"] = my

#     elif months and not year:
#         base_query += " AND (" + " OR ".join(
#             [f"month_year LIKE :month_{i}" for i in range(len(months))]
#         ) + ")"
#         for i, m in enumerate(months):
#             query_params[f"month_{i}"] = f"{m}-%"

#     elif year and not months:
#         month_years = [f"{calendar.month_abbr[i]}-{year}" for i in range(1, 13)]
#         base_query += " AND month_year IN ({})".format(
#             ", ".join([f":month_{i}" for i in range(len(month_years))])
#         )
#         for i, my in enumerate(month_years):
#             query_params[f"month_{i}"] = my
#     else:
#         base_query=base_query

#     base_query += " ORDER BY month_year DESC"

#     with engine.connect() as conn:
#         result = conn.execute(text(base_query), query_params).fetchall()

#     return [{"month": row[0], "rejection_percentage": row[1]} for row in result] if result else None



# def extract_chart_intent(user_query):
#     chart_types = ["distribution", "box", "correlation"]
#     known_parameters = {
#         "moisture": "moisture",
#         "moisture content": "moisture",
#         "active clay": "active_clay",
#         "compactability": "compactibility",
#         "shatter index": "shatter_index",
#         "gcs": "gcs",
#         "gfn afs": "gfn_afs",
#         "permeability": "permeability",
#         "loi": "loi",
#         "volatile matter": "volatile_matter",
#         "split strength": "split_strength",
#         "p h value": "pH_value",
#         "ph": "pH_value",
#     }

#     query = user_query.lower()
#     results = []

#     for chart_type in chart_types:
#         if chart_type in query:
#             for key in known_parameters:
#                 if key in query:
#                     if chart_type in query.split(key)[0]:  # Loose but useful logic
#                         results.append((chart_type.capitalize(), known_parameters[key]))

#     return results  




# def fetch_summary_data(foundry, defect_type):
#     """Fetches summary data (absolute change) from the database for a given foundry & defect type."""
#     response_messages = []

#     with engine.connect() as conn:
#         result = conn.execute(text("""
#             SELECT parameter, absolute_change 
#             FROM summary_table
#             WHERE foundry_name = :foundry_name AND defect_type = :defect_type
#             ORDER BY absolute_change DESC;
#         """), {"foundry_name": foundry, "defect_type": defect_type}).fetchall()

#     if result:
#         summary_data = [{"parameter": row[0], "absolute_change": row[1]} for row in result]
        
#         summary_chart_path = generate_summary_chart(foundry, defect_type, summary_data)
#         summary_chart_url = f"http://127.0.0.1:5000/{summary_chart_path}" if summary_chart_path else None

  
#         response_messages.append(f"Summary data for `{defect_type}` in `{foundry}`:")
#         table_data = {
#             "columns": ["Parameter", "Absolute Change (%)"],
#             "data": summary_data
#         }
#     else:
#         response_messages.append(f"No summary data available for `{defect_type}` in `{foundry}`.")
#         table_data = None
#         summary_chart_url = None

#     return {
#         "messages": response_messages,
#         "summary_table": table_data,
#         "summary_chart": summary_chart_url if summary_chart_url else "No Summary Chart Available"
#     }


    

# def get_last_used_foundry_and_defect(memory):
#     for msg in reversed(memory.chat_memory.messages):
#         if isinstance(msg, AIMessage):
#             try:
#                 content = json.loads(msg.content)
#                 return content.get("foundry"), content.get("defect_type")
#             except:
#                 continue
#     return None, None



# @chatbot_bp.route("/ask", methods=["POST"])
# @cross_origin(origin="http://localhost:3000")
# def ask_bot():
#     data = request.get_json()

#     if not data or "query" not in data:
#         return jsonify({"response": {"message": "No query provided. Please ask a valid question."}}), 400

#     user_query = data.get("query", "").strip()
#     session_id = request.remote_addr
#     memory = get_memory(session_id)
#     memory_vars = memory.load_memory_variables({})
#     # chat_history = memory.chat_memory

#     is_technical = any(word in user_query.lower() for word in [
#         "rejection", "chart", "fishbone", "defect", "summary", "blow hole",
#         "inclusion", "mould", "trend", "data", "compare","table","diagram","analyze","analytics","analysis","comparison","comparing","plot","plots","charts","all charts","rejection_analysis"
#     ])

#     if is_technical:
#         user_query = llm.clarify_user_query(user_query)
#     else:
#         response = llm.ask(user_query)
#         memory.save_context({"input": user_query}, {"output": response})
#         return jsonify({"response": {"messages": [response]}})
    
#     print(user_query)

#     prev_foundry = memory_vars.get("foundry")
#     prev_defect = memory_vars.get("defect_type")

#     foundry, defect_type, months, year = extract_query_params(user_query, prev_foundry, prev_defect)

#     if foundry:
#         memory_vars["foundry"] = foundry
#     if defect_type:
#         memory_vars["defect_type"] = defect_type

#     memory.chat_memory.add_message(HumanMessage(content=user_query))
#     if foundry and defect_type:
#         memory.chat_memory.add_message(AIMessage(content=json.dumps({
#             "foundry": foundry,
#             "defect_type": defect_type
#         })))

#     response_payload={}
#     if "messages" not in response_payload:
#         response_payload["messages"] = []

#     if not foundry:
#         foundry = prev_foundry or get_last_used_foundry_and_defect(memory)[0]
#     if not defect_type:
#         defect_type = prev_defect or get_last_used_foundry_and_defect(memory)[1]

#     if not foundry and defect_type:
#         kc=llm.ask(user_query)
#         response_payload["messages"].append(llm.ask(user_query))

#         return jsonify({"response":response_payload})
    
#     if foundry and defect_type:
#         config_path = os.path.join("Configfile", foundry, "config.json")

#         if os.path.exists(config_path):
#             with open(config_path, "r") as f:
#                 config = json.load(f)

#             config["defect_for_analysis"] = defect_type

#             date_keywords = ["compare", "reference", "period", "from", "between", "until", "vs", "versus","comparing","Comparison"]
#             if any(kw in user_query.lower() for kw in date_keywords):
#                 extracted = llm.extract_periods_from_query(user_query)
#                 if extracted:
                    
#                     if "reference_period" in extracted:
#                         config["data_selection"]["reference_period"] = extracted["reference_period"]
#                     if "comparison_period" in extracted:
#                         config["data_selection"]["comparison_period"] = extracted["comparison_period"]

#                     print("Updated periods from query:", extracted)

        
#             with open(config_path, "w") as f:
#                 json.dump(config, f, indent=4)

  
    
#     query_lower = user_query.lower().strip()

#     # Common synonyms and variations
#     def match_any(keywords):
#         return any(kw in query_lower for kw in keywords)

#     # Rejection-related intents
#     wants_rejection_data = match_any([
#         "rejection data", "rejection table", "show rejection table", "show rejection data"
#     ])
#     wants_rejection_chart = match_any([
#         "rejection chart", "rejection trend", "trend", "bar graph", 
#         "rejection bar chart", "trend chart", "rejection rate chart", "rejection data and chart"
#     ])

#     # Fishbone / Cause-effect
#     wants_fishbone = match_any([
#         "fishbone diagram", "fishbone", "cause and effect", "cause-effect", 
#         "fba", "diagram", "root cause", "defect analysis diagram"
#     ])

#     # Summary and insights
#     wants_summary = match_any([
#         "summary", "summarize", "summary data", "summary table", "top parameters", "top parameter", 
#         "change summary", "absolute change"
#     ])

#     wants_distribution = "distribution" in query_lower
#     wants_box = "box" in query_lower
#     wants_correlation = "correlation" in query_lower

#     # All charts or analysis plots
#     wants_all_charts = match_any([
#         "all charts", "three charts", "show all charts", 
#         "analysis plots", "all plots", "3 plots", "all comparison charts"
#     ])

#     # Analysis-related intents
#     wants_analysis = match_any([
#         "fishbone analysis", "rejection rate analysis", 
#         "compare on", "comparison on", "rejection on the months",
#         "compare with", "do analysis", "compare analyze","compare data"
#     ])

#     wants_companalysis = match_any([
#         "fishbone comparison", "comparison and analysis between",
#         "compare on the periods", "rejection rate analysis on the months",
#         "compare and analyze between", "compare between", "comparison between",
#         "compare and analyse", "comparing", "comparison", "relative difference","compare and analyze"
#     ])

#     # Group all high-level detection
#     any_intent = any([
#         wants_rejection_data,
#         wants_rejection_chart,
#         wants_fishbone,
#         wants_summary,
#         wants_all_charts,
#         wants_analysis,
#         wants_companalysis
#     ])

#     sql_data, chart_url, fba_chart_url, summary_response = None, None, None, None
#     data_found = False

#     if wants_fishbone and defect_type and not foundry:
#         fba_chart_path = f"results/FBADiagrams/{defect_type}.jpg"
#         if os.path.exists(fba_chart_path):
#             fba_chart_url = f"http://127.0.0.1:5000/{fba_chart_path}"
#             return jsonify({"response": {"FBA Chart": fba_chart_url}})
#         else:
#             return jsonify({"response": {"message": f"No Fishbone chart available for '{defect_type}'."}})

#     if foundry and defect_type:

#         if wants_rejection_data:
#             sql_data = fetch_sql_data(foundry, defect_type, months, year)
#             if sql_data:
#                 response_payload["data"] = sql_data
#                 response_payload["rejection_data"] = sql_data
#                 data_found = True

#         if wants_rejection_chart:
#             sql_data_chart = fetch_sql_data(foundry, defect_type, months, year)
#             if sql_data_chart:
#                 chart_path = generate_rejection_trend_chart(foundry, defect_type, sql_data_chart)
#                 if os.path.exists(chart_path):
#                     chart_url = f"http://127.0.0.1:5000/{chart_path}?timestamp={int(time.time())}"
#                     response_payload["Chart"] = chart_url
#                     data_found = True

#         elif wants_all_charts or wants_distribution or wants_box or wants_correlation:
#             chart_request = extract_chart_intent(user_query)
#             print(chart_request)

#             if not chart_request:
#                 try:
#                     query = text("""
#                         SELECT parameter
#                         FROM summary_table
#                         WHERE foundry_name = :foundry_name AND defect_type = :defect_type
#                         ORDER BY absolute_change DESC
#                         LIMIT 1
#                     """)
#                     with engine.connect() as conn:
#                         result = conn.execute(query, {
#                             "foundry_name": foundry,
#                             "defect_type": defect_type
#                         })
#                         row = result.fetchone()
#                         if row:
#                             fallback_param = row[0]
#                             fallback_charts = []
#                             fallback_messages = []

#                             for chart_type in ["Distribution", "Box", "Correlation"]:
#                                 chart_response = requests.post("http://127.0.0.1:5000/chart", json={
#                                     "foundry": foundry,
#                                     "chart_type": chart_type,
#                                     "parameter": fallback_param
#                                 })

#                                 if chart_response.ok:
#                                     chart_json = chart_response.json()
#                                     chart_list = chart_json.get("charts", [])
#                                     if chart_list:
#                                         fallback_charts.extend(chart_list)
                                        
#                                     else:
#                                         fallback_messages.append(f"Sorry, no {chart_type} chart found for {fallback_param}.")
#                                 else:
#                                     fallback_messages.append(f"Failed to generate {chart_type} chart for {fallback_param}.")

#                             return jsonify({
#                                 "response": {
#                                     "messages": fallback_messages,
#                                     "charts": fallback_charts
#                                 }
#                             })

#                 except Exception as e:
#                     print("Failed to fetch fallback parameter from summary table:", e)

#                 return jsonify({
#                     "response": {
#                         "messages": ["Unable to generate charts for the given defect."],
#                         "charts": []
#                     }
#                 })

#             elif chart_request:
#                 chart_blocks = []

#                 for chart_type, param in chart_request:
#                     chart_response = requests.post("http://127.0.0.1:5000/chart", json={
#                         "foundry": foundry,
#                         "chart_type": chart_type,
#                         "parameter": param
#                     })

#                     if chart_response.ok:
#                         chart_json = chart_response.json()
#                         chart_list = chart_json.get("charts", [])
#                         if chart_list:
#                             for chart_url in chart_list:
#                                 chart_blocks.append({
#                                     "message": f"Here is the **{chart_type}** chart for **{param}**.",
#                                     "image": chart_url
#                                 })
#                         else:
#                             chart_blocks.append({
#                                 "message": f"Sorry, no {chart_type} chart found for {param}.",
#                                 "image": None
#                             })
#                     else:
#                         chart_blocks.append({
#                             "message": f"Failed to generate {chart_type} chart for {param}.",
#                             "image": None
#                         })

#                 return jsonify({
#                     "response": {
#                         "chart_blocks": chart_blocks
#                     }
#                 })



#             else:
#                 return jsonify({
#                     "response": {
#                         "messages": ["Failed to generate the requested chart. As Less data points for statisitcal analysis."],
#                         "charts": []
#                     }
#                 })


#         if wants_summary:
#             summary_response = fetch_summary_data(foundry, defect_type)
#             if summary_response:
#                 response_payload["summary"] = summary_response
#                 data_found = True

#         if wants_fishbone:
#             fba_chart_path = f"results/FBADiagrams/{defect_type}.jpg"
#             if os.path.exists(fba_chart_path):
#                 fba_chart_url = f"http://127.0.0.1:5000/{fba_chart_path}"
#                 response_payload["FBA Chart"] = fba_chart_url
#                 data_found = True

#         if wants_analysis:
#             try:
#                 analyze_url = "http://127.0.0.1:5000/running"
#                 response = requests.post(
#                                 analyze_url,
#                                 json={"foundry": foundry},
#                                 headers={"Content-Type": "application/json"}
#                             )

#                 if response.status_code == 200:
#                     base_url = "http://127.0.0.1:5000"
#                     results_dir = os.path.join("results", foundry)
#                     temp_dir = os.path.join(results_dir, "temp")
#                     fba_dir=os.path.join("results","FBADiagrams")

#                     config_path = os.path.join("Configfile", foundry, "config.json")
#                     with open(config_path, "r") as f:
#                         config_data = json.load(f)

#                     reference_period = config_data["data_selection"]["reference_period"]
#                     comparison_period = config_data["data_selection"]["comparison_period"]

#                     query = text("""
#                         SELECT parameter AS `Parameters`, absolute_change AS `Absolute Change (%)`
#                         FROM summary_table
#                         WHERE foundry_name = :foundry_name AND defect_type = :defect_type
#                         ORDER BY `Absolute Change (%)` DESC
#                     """)
#                     with engine.connect() as conn:
#                         result = conn.execute(query, {"foundry_name": foundry, "defect_type": config_data["defect_for_analysis"]})
#                         summary_table = pd.DataFrame(result.fetchall(), columns=result.keys())

#                     if summary_table.empty:
#                         return jsonify({"error": "Summary table is empty"}), 400
#                     top_parameter = summary_table.iloc[0]["Parameters"]

#                     chart_list = []
                    
                    
#                     # 1. Monthly Rejection
#                     defect = config_data["defect_for_analysis"]
#                     fba_diagram=f"{defect}.jpg"
#                     fishbone_chart=os.path.join(fba_dir,fba_diagram)
#                     monthly_chart = f"monthly_rejection_rate_{defect}.jpeg"
#                     monthly_chart_path = os.path.join(results_dir, monthly_chart)
#                     if os.path.exists(monthly_chart_path):
#                         chart_list.append(f"{base_url}/results/{foundry}/{monthly_chart}")

#                     if os.path.exists(fishbone_chart):
#                         chart_list.append(f"{base_url}/results/FBADiagrams/{fba_diagram}")

#                     # 2. Distribution, Box, Correlation plots of top varied parameter
#                     for plot_type in ["Distribution", "Box", "Correlation"]:
#                         filename = f"{plot_type} plot of {top_parameter}.jpeg"
#                         file_path = os.path.join(temp_dir, filename)
#                         if os.path.exists(file_path):
#                             chart_list.append(f"{base_url}/results/{foundry}/temp/{filename}")

#                     # 3. Summary Chart
#                     summary_chart_path = os.path.join(results_dir, f"summary_table_plot_{defect_type}.jpeg")
#                     if os.path.exists(summary_chart_path):
#                         chart_list.append(f"{base_url}/results/{foundry}/summary_table_plot_{defect_type}.jpeg")

#                     summary_data={"summary": {
#                                 "reference_period": reference_period,
#                                 "comparison_period": comparison_period,
#                                 "top_parameter": top_parameter
#                             }}

#                     response_payload["Chart"]=chart_list
#                     response_payload["summary"]=summary_data
#                     response_payload["messages"].append(
#                         f" Fishbone Analytics executed successfully for **{foundry}**.\n"
#                         f" Reference Period: **{reference_period[0]}** to **{reference_period[1]}**\n"
#                         f" Comparison Period: **{comparison_period[0]}** to **{comparison_period[1]}**\n"
#                         f" Top varied parameter: **{top_parameter}**"
#                     )
#                     # print(response_payload)
#                     return jsonify({"response": {
#                         "messages": [
#                             f" Fishbone Analytics executed successfully for **{foundry}**.",
#                             f" Reference Period: **{reference_period[0]}** to **{reference_period[1]}**",
#                             f" Comparison Period: **{comparison_period[0]}** to **{comparison_period[1]}**",
#                             f" Top varied parameter: **{top_parameter}**"
#                         ],
#                         "charts": chart_list,
#                         "summary": {
#                             "reference_period": reference_period,
#                             "comparison_period": comparison_period,
#                             "top_parameter": top_parameter
#                         }
#                     }})

#                 else:
#                     return jsonify({"response": {
#                         "message": f"Failed to run analysis: {response.json().get('error', '')}",
#                         "status": "failed"
#                     }})
#             except Exception as e:
#                 return jsonify({"response": {"message": f"Error executing analysis: {str(e)}"}})
    
    
#     if wants_companalysis:
#         try:
#             analyze_url = "http://127.0.0.1:5000/refcomp"
#             response = requests.post(
#                 analyze_url,
#                 json={"foundry": foundry},
#                 headers={"Content-Type": "application/json"}
#             )

#             if response.status_code == 200:
#                 result = response.json()
#                 reference_period = result.get("reference_period", ["", ""])
#                 comparison_period = result.get("comparison_period", ["", ""])
#                 top_parameter = result.get("top_parameter", "")
#                 chart_list = result.get("charts", [])

#                 return jsonify({
#                     "response": {
#                         "messages": [
#                             f"Fishbone Analytics executed successfully for **{foundry}**.",
#                             f"Reference Period: **{reference_period[0]}** to **{reference_period[1]}**",
#                             f"Comparison Period: **{comparison_period[0]}** to **{comparison_period[1]}**",
#                             f"Top varied parameter: **{top_parameter}**"
#                         ],
#                         "charts": chart_list,
#                         "summary": {
#                             "reference_period": reference_period,
#                             "comparison_period": comparison_period,
#                             "top_parameter": top_parameter
#                         }
#                     }
#                 })
#             else:
#                 return jsonify({
#                     "response": {
#                         "messages": [f"Failed to run analysis: {response.json().get('error', '')}"],
#                         "status": "failed"
#                     }
#                 })
#         except Exception as e:
#             return jsonify({
#                 "response": {
#                     "messages": [f"Error executing analysis: {str(e)}"]
#                 }
#             })

#     if any([wants_rejection_data, wants_rejection_chart, wants_summary, wants_fishbone]):
#         if not data_found:
#             response_payload["messages"].append("No data available. Please try running the analysis.")
#         memory.save_context({"input": user_query}, {"output": str(response_payload)})
        

#         return jsonify({"response": response_payload})
    
#     analysis_keywords = ["run", "rejection analysis", "start analysis", "trigger", "perform analysis"]
#     if any(kw in user_query.lower() for kw in analysis_keywords) and foundry and defect_type:

#         try:
#             analyze_url = "http://127.0.0.1:5000/analyze"
#             response = requests.post(
#                             analyze_url,
#                             json={"foundry": foundry},
#                             headers={"Content-Type": "application/json"}
#                         )

#             if response.status_code == 200:
#                 base_url = "http://127.0.0.1:5000"
#                 results_dir = os.path.join("results", foundry)
#                 temp_dir = os.path.join(results_dir, "temp")
#                 fba_dir=os.path.join("results","FBADiagrams")

#                 config_path = os.path.join("Configfile", foundry, "config.json")
#                 with open(config_path, "r") as f:
#                     config_data = json.load(f)

#                 reference_period = config_data["data_selection"]["reference_period"]
#                 comparison_period = config_data["data_selection"]["comparison_period"]

#                 query = text("""
#                     SELECT parameter AS `Parameters`, absolute_change AS `Absolute Change (%)`
#                     FROM summary_table
#                     WHERE foundry_name = :foundry_name AND defect_type = :defect_type
#                     ORDER BY `Absolute Change (%)` DESC
#                 """)
#                 with engine.connect() as conn:
#                     result = conn.execute(query, {"foundry_name": foundry, "defect_type": config_data["defect_for_analysis"]})
#                     summary_table = pd.DataFrame(result.fetchall(), columns=result.keys())

#                 if summary_table.empty:
#                     return jsonify({"error": "Summary table is empty"}), 400

#                 top_parameter = summary_table.iloc[0]["Parameters"]

#                 chart_list = []
                
#                 # 1. Monthly Rejection
#                 defect = config_data["defect_for_analysis"]
#                 fba_diagram=f"{defect}.jpg"
#                 fishbone_chart=os.path.join(fba_dir,fba_diagram)
#                 monthly_chart = f"monthly_rejection_rate_{defect}.jpeg"
#                 monthly_chart_path = os.path.join(results_dir, monthly_chart)
#                 if os.path.exists(monthly_chart_path):
#                     chart_list.append(f"{base_url}/results/{foundry}/{monthly_chart}")

#                 if os.path.exists(fishbone_chart):
#                     chart_list.append(f"{base_url}/results/FBADiagrams/{fba_diagram}")

#                 # 2. Distribution, Box, Correlation plots of top varied parameter
#                 for plot_type in ["Distribution", "Box", "Correlation"]:
#                     filename = f"{plot_type} plot of {top_parameter}.jpeg"
#                     file_path = os.path.join(temp_dir, filename)
#                     if os.path.exists(file_path):
#                         chart_list.append(f"{base_url}/results/{foundry}/temp/{filename}")

#                 # 3. Summary Chart
#                 summary_chart_path = os.path.join(results_dir, f"summary_table_plot_{defect_type}.jpeg")
#                 if os.path.exists(summary_chart_path):
#                     chart_list.append(f"{base_url}/results/{foundry}/summary_table_plot_{defect_type}.jpeg")
#                 memory.save_context({"input": user_query}, {"output": str({
#                 "messages": [
#                     f" Fishbone Analytics executed successfully for **{foundry}**.",
#                     f" Reference Period: **{reference_period[0]}** to **{reference_period[1]}**",
#                     f" Comparison Period: **{comparison_period[0]}** to **{comparison_period[1]}**",
#                     f" Top varied parameter: **{top_parameter}**"
#                 ],
#                 "charts": chart_list,
#                 "summary": {
#                     "reference_period": reference_period,
#                     "comparison_period": comparison_period,
#                     "top_parameter": top_parameter
#                 }
#             })})
#                 return jsonify({
#                     "response": {
#                         "messages": [
#                             f" Fishbone Analytics executed successfully for **{foundry}**.",
#                             f" Reference Period: **{reference_period[0]}** to **{reference_period[1]}**",
#                             f" Comparison Period: **{comparison_period[0]}** to **{comparison_period[1]}**",
#                             f" Top varied parameter: **{top_parameter}**"
#                         ],
#                         "charts": chart_list,
#                         "summary": {
#                             "reference_period": reference_period,
#                             "comparison_period": comparison_period,
#                             "top_parameter": top_parameter
#                         }
#                     }
#                 })
#             else:
#                 return jsonify({"response": {
#                     "message": f"Failed to run analysis: {response.json().get('error', '')}",
#                     "status": "failed"
#                 }})
#         except Exception as e:
#             return jsonify({"response": {"message": f"Error executing analysis: {str(e)}"}})


#     sql_keywords = [
#         "rejection rate", "rejection percentage", "total rejection", "how many defects",
#         "average rejection", "show me", "fetch", "what is the rejection", "in the month",
#         "defect rate", "defect percentage", "monthly rejection", "production", "defect count","defect_type",
#     "date", "shift", "group name", "component id", "total production", "total rejection","rejction analysis","daily","defects"
#     ]

#     if not data_found and any(kw in user_query.lower() for kw in sql_keywords):
#         try:
#             sql_response = requests.post("http://127.0.0.1:8002/ask_sql", json={"query": user_query})
#             result = sql_response.json().get("response", "")
            
#             if "Final Answer:" in result:
#                 result = result.split("Final Answer:")[-1].strip()
#             memory.save_context({"input": user_query}, {"output": str({"messages": [f"{result}"]})})
#             return jsonify({"response": {"messages": [f"{result}"]}})
#         except Exception as e:
#             return jsonify({"response": {"messages": [f"SQL Agent error: {str(e)}"]}})


#     if "previous chart" in user_query.lower() and memory:
#         last_chart = None
#         for msg in reversed(memory.buffer):
#             if "Chart" in msg:
#                 last_chart = msg
#                 break
#         return jsonify({"response": {"message": f"Here is the last generated chart: {last_chart}"}}) if last_chart else \
#                jsonify({"response": {"message": "No previous chart found in chat history."}})

#     if "previous conversation" in user_query.lower():
#         past_messages = memory.buffer[-20:] if memory else []
#         if past_messages:
#             formatted = "\n".join(msg.content for msg in past_messages if hasattr(msg, "content"))
#             return jsonify({"response": {"message": f"Here are the last 20 messages:\n{formatted}"}})
#         else:
#             return jsonify({"response": {"message": "No past messages found."}})

#     response_messages = []

#     if not foundry and not defect_type and not months and not year:
#         recovered_foundry, recovered_defect = get_last_used_foundry_and_defect(memory)
#         foundry = foundry or recovered_foundry
#         defect_type = defect_type or recovered_defect

#         if foundry and defect_type:
#             response_messages.append(
#                 f"Based on previous chats: You were analyzing **{defect_type}** in **{foundry}**. "
#                 f"Please confirm what you’d like to do — summary table, rejection chart, or fishbone?"
#             )
#         else:
#             past_messages = memory.buffer[-10:] if memory else []
#             if past_messages:
#                 context = "\n".join(msg.content for msg in past_messages if hasattr(msg, "content"))
#                 response_messages.append(f"Based on previous chats:\n{context}")
#             else:
#                 response_messages.append(llm.ask(user_query))

#     memory.save_context({"input": user_query}, {"output": "\n".join(response_messages)})
#     print(memory)
#     if not any_intent and foundry and defect_type:
#         followup_prompt = (
#             f"I noticed you mentioned **{defect_type}** in the **{foundry}** foundry.\n"
#             "Could you clarify what information you'd like?\n\n"
#             "- 📊 Rejection Chart?\n"
#             "- 🧾 Rejection Table?\n"
#             "- 🎯 Summary of Parameter Changes?\n"
#             "- 🧠 Fishbone Diagram?\n"
#         )

#         llm_followup = llm.ask(followup_prompt)
        
#         return jsonify({
#             "response": {
#                 "messages": [
#                     "I need a bit more detail to proceed with your analysis.",
#                     llm_followup
#                 ],
#                 "status": "need_clarification"
#             }
#         })
    
#     return jsonify({
#         "response": {
#             "messages": response_messages
#         }
#     })



















#     # if wants_companalysis:
#     #         try:
#     #             analyze_url = "http://127.0.0.1:5000/refcomp"
#     #             response = requests.post(
#     #                             analyze_url,
#     #                             json={"foundry": foundry},
#     #                             headers={"Content-Type": "application/json"}
#     #                         )

#     #             if response.status_code == 200:
#     #                 base_url = "http://127.0.0.1:5000"
#     #                 results_dir = os.path.join("results", foundry)
#     #                 temp_dir = os.path.join(results_dir, "temp")
#     #                 fba_dir=os.path.join("results","FBADiagrams")

#     #                 config_path = os.path.join("Configfile", foundry, "config.json")
#     #                 with open(config_path, "r") as f:
#     #                     config_data = json.load(f)

#     #                 reference_period = config_data["data_selection"]["reference_period"]
#     #                 comparison_period = config_data["data_selection"]["comparison_period"]

#     #                 query = text("""
#     #                     SELECT parameter AS `Parameters`, absolute_change AS `Absolute Change (%)`
#     #                     FROM summary_table
#     #                     WHERE foundry_name = :foundry_name AND defect_type = :defect_type
#     #                     ORDER BY `Absolute Change (%)` DESC
#     #                 """)
#     #                 with engine.connect() as conn:
#     #                     result = conn.execute(query, {"foundry_name": foundry, "defect_type": config_data["defect_for_analysis"]})
#     #                     summary_table = pd.DataFrame(result.fetchall(), columns=result.keys())

#     #                 if summary_table.empty:
#     #                     return jsonify({"error": "Summary table is empty"}), 400
#     #                 top_parameter = summary_table.iloc[0]["Parameters"]

#     #                 chart_list = []
                    
                    
#     #                 # 1. Monthly Rejection
#     #                 defect = config_data["defect_for_analysis"]
#     #                 fba_diagram=f"{defect}.jpg"
#     #                 fishbone_chart=os.path.join(fba_dir,fba_diagram)
#     #                 monthly_chart = f"monthly_rejection_rate_{defect}.jpeg"
#     #                 monthly_chart_path = os.path.join(results_dir, monthly_chart)
#     #                 if os.path.exists(monthly_chart_path):
#     #                     chart_list.append(f"{base_url}/results/{foundry}/{monthly_chart}")

#     #                 if os.path.exists(fishbone_chart):
#     #                     chart_list.append(f"{base_url}/results/FBADiagrams/{fba_diagram}")

#     #                 # 2. Distribution, Box, Correlation plots of top varied parameter
#     #                 for plot_type in ["Distribution", "Box", "Correlation"]:
#     #                     filename = f"{plot_type} plot of {top_parameter}.jpeg"
#     #                     file_path = os.path.join(temp_dir, filename)
#     #                     if os.path.exists(file_path):
#     #                         chart_list.append(f"{base_url}/results/{foundry}/temp/{filename}")

#     #                 # 3. Summary Chart
#     #                 summary_chart_path = os.path.join(results_dir, f"summary_table_plot_{defect_type}.jpeg")
#     #                 if os.path.exists(summary_chart_path):
#     #                     chart_list.append(f"{base_url}/results/{foundry}/summary_table_plot_{defect_type}.jpeg")

#     #                 summary_data={"summary": {
#     #                             "reference_period": reference_period,
#     #                             "comparison_period": comparison_period,
#     #                             "top_parameter": top_parameter
#     #                         }}

#     #                 response_payload["Chart"]=chart_list
#     #                 response_payload["summary"]=summary_data
#     #                 response_payload["messages"].append(
#     #                     f" Fishbone Analytics executed successfully for **{foundry}**.\n"
#     #                     f" Reference Period: **{reference_period[0]}** to **{reference_period[1]}**\n"
#     #                     f" Comparison Period: **{comparison_period[0]}** to **{comparison_period[1]}**\n"
#     #                     f" Top varied parameter: **{top_parameter}**"
#     #                 )
#     #                 # print(response_payload)
#     #                 return jsonify({"response": {
#     #                     "messages": [
#     #                         f" Fishbone Analytics executed successfully for **{foundry}**.",
#     #                         f" Reference Period: **{reference_period[0]}** to **{reference_period[1]}**",
#     #                         f" Comparison Period: **{comparison_period[0]}** to **{comparison_period[1]}**",
#     #                         f" Top varied parameter: **{top_parameter}**"
#     #                     ],
#     #                     "charts": chart_list,
#     #                     "summary": {
#     #                         "reference_period": reference_period,
#     #                         "comparison_period": comparison_period,
#     #                         "top_parameter": top_parameter
#     #                     }
#     #                 }})

#     #             else:
#     #                 return jsonify({"response": {
#     #                     "message": f"Failed to run analysis: {response.json().get('error', '')}",
#     #                     "status": "failed"
#     #                 }})
#     #         except Exception as e:
#     #             return jsonify({"response": {"message": f"Error executing analysis: {str(e)}"}})


import json 
import requests
from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from langchain_core.messages import HumanMessage, AIMessage
from services.memory_service import get_memory, get_last_used_foundry_and_defect
from services.intent_services import detect_user_intents
from utils.query_utils import extract_query_params
from services.summary_service import handle_summary_intent
from services.chart_service import handle_chart_intent
from services.analyzer_service import handle_analysis_intent, handle_companalysis_intent, handle_trigger_analysis
from services.config_service import update_defect_in_config, update_periods_from_query
from utils.sql_utils import fetch_sql_data, fetch_summary_data, generate_rejection_trend_chart
from models.groq_llm import GroqLLM
from api.report_generation import generate_report
import os
import time

chatbot_bp = Blueprint("chatbot", __name__)
llm = GroqLLM()


@chatbot_bp.route("/ask", methods=["POST"])
@cross_origin(origin="http://localhost:3000")
def ask_bot():
    data = request.get_json()
    if not data or "query" not in data:
        return jsonify({"response": {"message": "No query provided. Please ask a valid question."}}), 400

    user_query = data.get("query", "").strip()
    session_id = request.remote_addr
    memory = get_memory(session_id)
    memory_vars = memory.load_memory_variables({})


    is_technical = any(word in user_query.lower() for word in [
        "rejection", "chart", "fishbone", "defect", "summary", "blow hole",
        "inclusion", "mould", "trend", "data", "compare", "table", "diagram",
        "analyze", "analytics", "analysis", "comparison", "comparing", "plot", "plots",
        "charts", "all charts", "rejection_analysis","run"])

    if not is_technical:
        response = llm.ask(user_query)
        memory.save_context({"input": user_query}, {"output": response})
        return jsonify({"response": {"messages": [response]}})

    user_query = llm.clarify_user_query(user_query)
    print("Clarified Query:", user_query)

    foundry="Munjal"

    prev_foundry = memory_vars.get("foundry")
    prev_defect = memory_vars.get("defect_type")
    foundry, defect_type, months, year = extract_query_params(user_query, prev_foundry, prev_defect)


    if foundry:
        memory_vars["foundry"] = foundry
    if defect_type:
        memory_vars["defect_type"] = defect_type

    if not foundry:
        foundry = prev_foundry or get_last_used_foundry_and_defect(memory)[0]
    if not defect_type:
        defect_type = prev_defect or get_last_used_foundry_and_defect(memory)[1]


    memory.chat_memory.add_message(HumanMessage(content=user_query))
    if foundry and defect_type:
        memory.chat_memory.add_message(AIMessage(content=jsonify({
            "foundry": foundry,
            "defect_type": defect_type
        }).data.decode()))

    if foundry and defect_type:
        update_defect_in_config(foundry, defect_type)
        update_periods_from_query(user_query, foundry)

    response_payload = {"messages": []}

    intents = detect_user_intents(user_query)
    print(intents)

    if intents.get("wants_rejection_data") and foundry and defect_type:
        sql_data = fetch_sql_data(foundry, defect_type, months, year)
        if sql_data:
            response_payload["data"] = sql_data
            response_payload["rejection_data"] = sql_data
            response_payload["messages"].append("Here is the rejection data.")
            memory.save_context({"input": user_query}, {"output": str(response_payload)})
            return jsonify({"response": response_payload})

    if intents.get("wants_rejection_chart") and foundry and defect_type:
        sql_data_chart = fetch_sql_data(foundry, defect_type, months, year)

        if sql_data_chart:
            chart_path = generate_rejection_trend_chart(foundry, defect_type, sql_data_chart)

            if os.path.exists(chart_path):
                chart_url = f"http://127.0.0.1:5000/{chart_path}?timestamp={int(time.time())}"
                response_payload["Chart"] = chart_url
                response_payload["messages"].append("Here is the rejection trend chart.")
            else:
                response_payload["messages"].append("Chart generation failed. Chart file not found.")
        else:
            response_payload["messages"].append("No rejection data available for the selected period.")

        memory.save_context({"input": user_query}, {"output": str(response_payload)})
        return jsonify({"response": response_payload})


    if intents.get("wants_summary") and foundry and defect_type:
        summary_response = handle_summary_intent(foundry, defect_type)
        memory.save_context({"input": user_query}, {"output": "\n".join(summary_response["messages"])})
        return jsonify({"response": summary_response})



    if any([intents.get("wants_all_charts"), intents.get("wants_distribution"), intents.get("wants_box"), intents.get("wants_correlation")]):
        return handle_chart_intent(user_query, foundry, defect_type, memory)

    if intents.get("wants_fishbone") and foundry and defect_type:
        fba_chart_path = f"results/FBADiagrams/{defect_type}.jpg"
        if os.path.exists(fba_chart_path):
            fba_chart_url = f"http://127.0.0.1:5000/{fba_chart_path}"
            return jsonify({"response": {"FBA Chart": fba_chart_url}})
        else:
            return jsonify({"response": {"message": f"No Fishbone chart available for '{defect_type}'."}})

    # if intents.get("wants_analysis") and foundry and defect_type:
    #     return handle_analysis_intent(foundry)
    if intents.get("wants_analysis") and foundry and defect_type:
        analysis_response = handle_analysis_intent(foundry)

        if not isinstance(analysis_response, dict):
            analysis_data = analysis_response.get_json().get("response", {})
        else:
            analysis_data = analysis_response.get("response", {})

        report_path = generate_report({
            "foundry": foundry,
            "defect_type": defect_type,
            "reference_period": analysis_data.get("summary", {}).get("reference_period", []),
            "comparison_period": analysis_data.get("summary", {}).get("comparison_period", []),
            "top_parameter": analysis_data.get("summary", {}).get("top_parameter", ""),
            "charts": analysis_data.get("charts", []),
            "query": user_query
        })

        report_url = f"http://127.0.0.1:5000/{report_path}"
        analysis_data["report"] = report_url

        return jsonify({
            "response": {
                "messages": analysis_data.get("messages", []),
                "charts": analysis_data.get("charts", []),
                "summary": analysis_data.get("summary", {}),
                "report": report_url
            }
        })




    # companalysis_keywords = [ "comparison analysis", "compare and analyze", "compare with", "refcomp","fishbone comparison", "comparison and analysis between","compare on the periods", "rejection rate analysis on the months","compare and analyze between", "compare between", "comparison between","compare and analyse", "comparing", "comparison", "relative difference","compare and analyze"]
    # if any(kw in user_query.lower() for kw in companalysis_keywords) and foundry and defect_type:
    #     analysis_data = handle_companalysis_intent(foundry, defect_type)
        
    #     # Wrap dict in Flask response if it's not already
    #     if isinstance(analysis_data, dict):
    #         analysis_response = jsonify({"response": analysis_data})
    #     else:
    #         analysis_response = analysis_data

    #     output_str = json.dumps(analysis_response.get_json())
    #     memory.save_context({"input": user_query}, {"output": output_str})
    #     return analysis_response
    companalysis_keywords = [
        "comparison analysis", "compare and analyze", "compare with", "refcomp", "fishbone comparison",
        "comparison and analysis between", "compare on the periods", "rejection rate analysis on the months",
        "compare and analyze between", "compare between", "comparison between", "compare and analyse",
        "comparing", "comparison", "relative difference", "compare and analyze"
    ]

    if any(kw in user_query.lower() for kw in companalysis_keywords) and foundry and defect_type:
        analysis_data = handle_companalysis_intent(foundry, defect_type)

      
        if not isinstance(analysis_data, dict):
            analysis_data = analysis_data.get_json()

        analysis_content = analysis_data.get("response", analysis_data)

        report_path = generate_report({
            "foundry": foundry,
            "defect_type": defect_type,
            "reference_period": analysis_content.get("reference_period", []),
            "comparison_period": analysis_content.get("comparison_period", []),
            "top_parameter": analysis_content.get("top_parameter", ""),
            "charts": analysis_content.get("charts", []),
            "query": user_query
        })

        report_url = f"http://127.0.0.1:5000/{report_path}"
        analysis_content["report"] = report_url

        memory.save_context({"input": user_query}, {"output": json.dumps(analysis_content)})

        return jsonify({"response": analysis_content})




    # analysis_keywords = ["run", "rejection analysis", "start analysis", "trigger", "perform analysis"]
    # if any(kw in user_query.lower() for kw in analysis_keywords) and foundry and defect_type:
    #     analysis_response = handle_trigger_analysis(foundry, defect_type, user_query)
    #     output_str = json.dumps(analysis_response.get_json()) 
    #     memory.save_context({"input": user_query}, {"output": output_str})

    #     return analysis_response

    analysis_keywords = ["run", "rejection analysis", "start analysis", "trigger", "perform analysis","run an analysis","show the analysis"]
    if any(kw in user_query.lower() for kw in analysis_keywords) and foundry and defect_type:
        analysis_response = handle_trigger_analysis(foundry, defect_type, user_query)

        if not isinstance(analysis_response, dict):
            analysis_data = analysis_response.get_json().get("response", {})
        else:
            analysis_data = analysis_response.get("response", {})

        report_path = generate_report({
            "foundry": foundry,
            "defect_type": defect_type,
            "reference_period": analysis_data.get("summary", {}).get("reference_period", []),
            "comparison_period": analysis_data.get("summary", {}).get("comparison_period", []),
            "top_parameter": analysis_data.get("summary", {}).get("top_parameter", ""),
            "charts": analysis_data.get("charts", []),
            "query": user_query
        })

        report_url = f"http://127.0.0.1:5000/{report_path}"
        analysis_data["report"] = report_url

        memory.save_context({"input": user_query}, {"output": json.dumps(analysis_data)})

        return jsonify({
            "response": {
                "messages": analysis_data.get("messages", []),
                "charts": analysis_data.get("charts", []),
                "summary": analysis_data.get("summary", {}),
                "report": report_url
            }
        })


    if intents.get("sql_query") and foundry and defect_type:
        try:
            sql_response = requests.post("http://127.0.0.1:8002/ask_sql", json={"query": user_query})
            result = sql_response.json().get("response", "")
            if "Final Answer:" in result:
                result = result.split("Final Answer:")[-1].strip()
            memory.save_context({"input": user_query}, {"output": result})
            return jsonify({"response": {"messages": [result]}})
        except Exception as e:
            return jsonify({"response": {"messages": [f"SQL Agent error: {str(e)}"]}})

    response_messages = []
    recovered_foundry, recovered_defect = get_last_used_foundry_and_defect(memory)
    if not foundry and not defect_type and recovered_foundry and recovered_defect:
        response_messages.append(
            f"Based on previous chats: You were analyzing **{recovered_defect}** in **{recovered_foundry}**.\n"
            f"Please confirm what you'd like to do — summary table, rejection chart, or fishbone?"
        )
    elif not response_messages:
        response_messages.append(llm.ask(user_query))

    memory.save_context({"input": user_query}, {"output": "\n".join(response_messages)})

    return jsonify({"response": {"messages": response_messages}})
