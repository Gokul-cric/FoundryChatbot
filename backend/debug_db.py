# from pydantic_ai import Agent
# from pydantic_ai.models.groq import GroqModel
# from pydantic_ai.providers.groq import GroqProvider
# from httpx import AsyncClient
# import os
# from dotenv import load_dotenv

# # Load API key from .env (recommended)
# load_dotenv()
# api_key = os.getenv("GROQ_API_KEY")  # safer than hardcoding

# # Create custom HTTP client
# custom_http_client = AsyncClient(timeout=30)

# # Setup Groq Model with provider
# model = GroqModel(
#     'llama-3.3-70b-versatile',
#     provider=GroqProvider(api_key='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', http_client=custom_http_client),
# )

# # Instantiate the agent
# agent = Agent(model)

# # Async main
# async def main():
#     result = await agent.run("hello!")
#     while True:
#         print(f"\n{result.data}")
#         user_input = input("\n> ")
#         result = await agent.run(
#             user_input,
#             message_history=result.new_messages(),
#         )

# if __name__ == "__main__":
#     import asyncio
#     asyncio.run(main())



# from api.chatbot import extract_chart_intent_with_llm


# result=[]
# result=extract_chart_intent_with_llm("give the distribution plot of moisture on Broken Mould on compare march and jan 2025")

# print(result)
# chart_type, parameter = extract_chart_intent_with_llm("Show distribution plot of active clay content for Munjal")
# print(chart_type, parameter)


from database import generate_daily_rejection_summary,connect_db
import os
from sqlalchemy import create_engine, text
import json
import pandas as pd

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

generate_daily_rejection_summary(engine,foundry,config_file)