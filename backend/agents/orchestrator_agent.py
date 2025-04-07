# agents/orchestrator_agent.py (FINAL VERSION)

import os
import requests
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

from models.groq_llm import GroqLLM

load_dotenv()

llm = ChatGroq(model="llama3-8b-8192",temperature=0.2)

def classify_and_route(query: str, thread_id="default") -> dict:
    """
    Routes user query to the correct system:
    - Tool Agent (/ask_ai)
    - SQL Agent (/ask_sql)
    - GroqLLM fallback
    """
    classification_prompt = f"""
You are an AI classifier. For the given query, reply with only one of the following labels:
- "tool" → if it asks for distribution, box, correlation, fishbone generation
- "sql" → if it's about rejection trends, rates, months, data from DB
- "general" → for all other questions

Query: {query}

Label (tool / sql / general):
"""
    try:
        label = llm.invoke([HumanMessage(content=classification_prompt)]).content.strip().lower()
    except Exception as e:
        return {"messages": [f"LLM classification failed: {str(e)}"]}

    if label == "tool":
        try:
            response = requests.post("http://localhost:8001/ask_ai", json={
                "query": query,
                "thread_id": thread_id or "default-user"
            })

            return {"messages": [response.json().get("response", "Tool agent gave no response.")]}
        except Exception as e:
            return {"messages": [f"Tool Agent Error: {str(e)}"]}

    elif label == "sql":
        try:
            response = requests.post(
                "http://localhost:8002/ask_sql",
                json={"query": query}
            )
            return {"messages": [response.json().get("response", "SQL agent gave no response.")]}
        except Exception as e:
            return {"messages": [f"SQL Agent Error: {str(e)}"]}

    else:
        try:
            groq_llm = GroqLLM()
            return {"messages": [groq_llm.ask(query)]}
        except Exception as e:
            return {"messages": [f"GroqLLM fallback failed: {str(e)}"]}
