from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
import logging
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from tools.fishbone_tool import run_fishbone_analysis
from tools.rejection_sql_tool import query_rejection_rate

load_dotenv()
app = Flask(__name__)

# Configure logging
logging.basicConfig(
    filename="ai_agent.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Init Groq model + memory
llm = init_chat_model("llama3-8b-8192", model_provider="groq")
memory = MemorySaver()

# Register tools
tools = [run_fishbone_analysis, query_rejection_rate]
agent_executor = create_react_agent(llm, tools, checkpointer=memory)

@app.route("/ask_ai", methods=["POST"])
def ask_ai():
    data = request.get_json()
    query = data.get("query", "")
    thread_id = data.get("thread_id", "default-user")
    config = {"configurable": {"thread_id": thread_id}}

    logging.info(f"Received query: {query} | Thread: {thread_id}")

    try:
        response = agent_executor.invoke({"messages": [HumanMessage(content=query)], **config})
        final_response = response["messages"][-1].content
        logging.info(f"Agent response: {final_response}")
        return jsonify({"response": final_response})
    except Exception as e:
        logging.error(f"Agent Execution Error: {str(e)}", exc_info=True)
        return jsonify({"response": f"Agent Error: {str(e)}"}), 500

if __name__ == "__main__":
    print("Running the AI Agent")
    app.run(port=8001, debug=True)
    
