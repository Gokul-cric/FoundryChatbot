from flask import Flask, request, jsonify
import os, re, logging
from dotenv import load_dotenv
from datetime import datetime
from sqlalchemy import create_engine

from groq import Groq
from langchain_groq import ChatGroq
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.agent_toolkits import create_sql_agent
from langgraph.prebuilt import create_react_agent

load_dotenv()
app = Flask(__name__)
logging.basicConfig(filename="sql_agent.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def normalize_query(query):
    patterns = [
        r"([A-Za-z]+)[\s'/\-]+(\d{2,4})",
        r"(\d{1,2})[\s/\-]+(\d{2,4})",
        r"(\d{4})[\s/\-]+([A-Za-z]+)"
    ]
    for pattern in patterns:
        matches = re.findall(pattern, query)
        for match in matches:
            try:
                if pattern == patterns[0]:
                    month, year = match
                elif pattern == patterns[1]:
                    month, year = match
                elif pattern == patterns[2]:
                    year, month = match
                if len(year) == 2:
                    year = "20" + year if int(year) < 50 else "19" + year
                dt = datetime.strptime(f"{month} {year}", "%B %Y")
                formatted = dt.strftime("%b-%Y")
            except:
                try:
                    dt = datetime.strptime(f"{month} {year}", "%b %Y")
                    formatted = dt.strftime("%b-%Y")
                except:
                    try:
                        dt = datetime.strptime(f"{int(month)} {year}", "%m %Y")
                        formatted = dt.strftime("%b-%Y")
                    except:
                        continue
            full_match = " ".join(match)
            query = query.replace(full_match, formatted)
    return query

class SQLAgentWrapper:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is missing")
        self.client = Groq(api_key=self.api_key)
        self.agent_executor = None
        self.init_sql_agent()

    def init_sql_agent(self):
        try:
            db_user = os.getenv("DB_USER")
            db_pass = os.getenv("DB_PASS")
            db_host = os.getenv("DB_HOST")
            db_port = os.getenv("DB_PORT")
            db_name = os.getenv("DB_NAME")

            if not all([db_user, db_pass, db_name, db_host, db_port]):
                raise ValueError("Missing DB credentials in .env file")

            mysql_url = f"mysql+mysqlconnector://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}?auth_plugin=mysql_native_password"
            print(f"[SQL Agent] Connecting to DB: {mysql_url}")
            engine = create_engine(mysql_url, connect_args={"connect_timeout": 5})
            db = SQLDatabase(engine)

            llm = ChatGroq(model="llama-3.2-90b-vision-preview", temperature=0.2, max_tokens=300, timeout=10)

            schema_description = """
You are an intelligent assistant for a Foundry Analytics chatbot. Your job is to answer analytical queries using the following MySQL database tables from the `foundry_db`:

---

🧾 **Available Tables & Their Purposes**

1. `rejection_analysis`
   - Stores **monthly rejection statistics** by defect and foundry.
   - Columns:
     - `foundry_name`: Munjal
     - `defect_type`: Type of defect (e.g., 'Blow Hole')
     - `month_year`: Month-Year in string format (e.g., 'Jan-2025')
     - `rejection_percentage`: Rejection percentage for that month (FLOAT)
     - Additional: `total_production`, `total_rejection`, `group_name`, `component_id`

2. `daily_rejection_analysis`
   - Stores **daily rejection breakdown** by date, shift, group, or component.
   - Columns:
     - `foundry_name`, `defect_type`, `date` (DATE), `shift`, `group_name`, `component_id`, `total_production`, `total_rejection`, `rejection_percentage`

3. `summary_table`
   - Stores absolute parameter changes between comparison periods.
   - Columns:
     - `foundry_name`, `defect_type`, `parameter`, `absolute_change` (FLOAT)

4. `comp_data_analysis_data` and `ref_data_analysis_data`
   - Detailed analysis data for **comparison** and **reference** periods.
   - Columns:
     - `Foundry`, `DefectType`, various sand properties (e.g., `moisture`, `permeability`), and defect-wise rejection percentages (e.g., `Blow Hole %`)

5. `prepared_sand_data` and `rejection_data`
   - Raw sand property and defect data (used to calculate aligned analytics).

---

⚠️ **Query Handling Rules**

- ✅ Use **exact values** as in the database:
  - `foundry_name` must match exactly (e.g., `'Munjal'`)
  - `month_year` must match format like `'Jan-2025'` (it's a `VARCHAR`)
  - `defect_type` must be exact (e.g., `'Broken Mould'`)

- 🔄 **Defaults:**
  - If no `foundry_name` is given, use `'Munjal'`
  - If no `defect_type` is provided, request it from the user
  - If no `month_year` is given, return **all available** records

- 🧠 **Special Case:**
  - For daily trend queries or queries involving `shift`, `date`, or `group_name`, use `daily_rejection_analysis` instead of `rejection_analysis`.

  - Do not Convert the rejection percentage to percentage by multiplying with 100 beacuse it is alreadyin that format.

  - If Daily keyword is present the search the thing in daily_rejection_analysis table.
  - If Monthly keyword is present the search the thing in rejection_analysis table.
 
---

📤 **Response Format Instructions**

Always format the output in a **clean table structure** like this:


#             schema_description = """

#             - Do NOT expand abbreviations like 'Munjal'. Query it exactly as 'Munjal'.
#                     - Foundry names include: 'Munjal'

#             Tables and their descriptions:

#             1. rejection_analysis:
#             - Stores monthly rejection stats.
#             - Columns: foundry_name, defect_type, month_year, rejection_percentage
#             - Sample foundry_name values:  'Munjal'

#             2. summary_table:
#             - Summary of parameter deviations.
#             - Columns: foundry_name, defect_type, parameter, absolute_change

#             3. comp_data_analysis_data and ref_data_analysis_data:
#             - Detailed comparison period data.
#             - Columns include: Foundry, DefectType, and various parameter columns like 'Blow Hole %', 'Sand Inclusion defect %', etc., .

#             4. Daily Rejction Data analysis:
#             - Stores daily rejection data.
#             - Columns: foundry_name, defect_type, date, rejection_percentage , shift, and other parameters.
#             - Table name: daily_rejection_analysis
#             - Sample foundry_name values:  'Munjal'
#             - Sample defect_type values: 'Blow Hole', 'Sand Inclusion defect', 'Erosion Scab', 'Sand Fusion', 'Mould Swell', 'Broken Mould'
#             - Date format: 'YYYY-MM-DD' (e.g., '2023-01-01'). 


#             ⚠️ Important:
#             - Do **not** expand abbreviations like 'MCIE' — it stands for 'Mahindra CIE' but should always be queried as `'MCIE'` in SQL.
#             - Use exact strings from the `foundry_name` field.

#             - Querying:
#             - if not specified foundry, assume 'Munjal' as the default foundry.
#             - if not specified defect_type, Ask what defect to analyze and use the defect_type from the user query.
#             - if not specified month_year, ignore month_year and answer all the month_year data in the table in a table format
#             - return the  result in a table format with the following columns:
#                 - foundry_name
#                 - defect_type
#                 - month_year
#                 - rejection_percentage

#             - If user asks querys related to Daily rejection data use the table daily_rejection_analysis
        
#             -Response 
#             - Answer in table  format with the following columns:
#                 - foundry_name
#                 - defect_type
#                 - month_year
#                 - rejection_percentage
#             - Use exact strings from the `foundry_name` field.
#             - Use exact strings from the `defect_type` field.
#             - Use exact strings from the `month_year` field.
#             - Use exact strings from the `rejection_percentage` field.
#             - use upto three decimal places
    
#             Important Notes:
#             - `month_year` is VARCHAR like 'Jan-2023', NOT a date.
#             - Always use exact format: WHERE month_year = 'Jan-2023'
#             - Foundry names: 'Munjal'
#             - use Defacult foundry as Munjal
# """

            self.agent_executor = create_react_agent(
                llm,
                SQLDatabaseToolkit(db=db, llm=llm).get_tools(),
                prompt="You are a SQL expert. Only return final answers in a friendly sentence. and do not repeat the words" + schema_description
            )
            print("[SQL Agent] Initialized successfully.")
        except Exception as e:
            logging.error(f"SQL Agent Init Error: {str(e)}")
            raise

    def ask_sql(self, user_query):
        try:
            if not self.agent_executor:
                return "SQL Agent is not initialized."
            cleaned_query = normalize_query(user_query)
            print(f"[SQL Agent] User Query: {cleaned_query}")
            result = self.agent_executor.invoke({"messages": [("user", cleaned_query)]})
            final_message = result["messages"][-1].content.strip()
            return final_message
        except Exception as e:
            logging.error(f"SQL Query Execution Error: {str(e)}")
            return "Failed to process SQL query."

sql_agent = SQLAgentWrapper()

@app.route("/ask_sql", methods=["POST"])
def ask_sql():
    try:
        data = request.get_json()
        query = data.get("query", "")
        result = sql_agent.ask_sql(query)
        return jsonify({"response": result})
    except Exception as e:
        return jsonify({"response": f"Internal error: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(port=8002, debug=True)
