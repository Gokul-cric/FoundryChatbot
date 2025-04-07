# services/memory_service.py
import os 
import json
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain.memory import ConversationBufferMemory
from langchain_core.messages import HumanMessage, AIMessage

multi_turn_memory = {}
memory_store = {}

FOUNDRIES = ["Munjal"]  # Extendable
DEFECT_TYPES = [
    "Blow Hole", "Sand Inclusion defect", "Erosion Scab", "Broken Mould",
    "Mould Swell", "Sand Fusion", "Total Rejection"
]

def get_memory(session_id):
    if session_id not in multi_turn_memory:
        multi_turn_memory[session_id] = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
    return multi_turn_memory[session_id]

def get_foundry_memory(foundry_name: str) -> ChatMessageHistory:
    if foundry_name not in memory_store:
        memory_store[foundry_name] = ChatMessageHistory()
    return memory_store[foundry_name]

def update_memory_context(memory, user_query, foundry, defect_type):
    memory.chat_memory.add_message(HumanMessage(content=user_query))
    if foundry and defect_type:
        memory.chat_memory.add_message(AIMessage(content=json.dumps({
            "foundry": foundry,
            "defect_type": defect_type
        })))

def get_last_used_foundry_and_defect(memory):
    for msg in reversed(memory.chat_memory.messages):
        if isinstance(msg, AIMessage):
            try:
                content = json.loads(msg.content)
                return content.get("foundry"), content.get("defect_type")
            except:
                continue
    return None, None

def save_user_context(memory, user_query, response):
    memory.save_context({"input": user_query}, {"output": response})

def format_previous_conversation(memory, limit=20):
    past_messages = memory.buffer[-limit:] if memory else []
    if past_messages:
        return "\n".join(msg.content for msg in past_messages if hasattr(msg, "content"))
    return "No past messages found."

def find_last_chart(memory):
    for msg in reversed(memory.buffer):
        if "Chart" in msg:
            return msg
    return None