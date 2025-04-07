import os
import re
import logging
from groq import Groq
import json
import requests
from openai import OpenAIError
from langchain_groq import ChatGroq
from langchain_community.agent_toolkits import create_sql_agent
from datetime import datetime
from services.rag_services import load_and_extract_texts, retrieve_relevant_chunks, split_text_into_chunks



from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(filename="groq_errors.log", level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s")

class GroqLLM:
    def __init__(self):
        """Initialize Groq API client and SQL Agent with valid API key."""
        self.api_key = os.getenv("GROQ_API_KEY")
        self.chat_history = []
        
        if not self.api_key:
            logging.error("Error: GROQ_API_KEY is missing in .env file!")
            raise ValueError("Error: GROQ_API_KEY is missing! Please check your .env file.")
        try:
            self.client = Groq(api_key=self.api_key)
        except Exception as e:
            logging.error(f"Error initializing Groq API: {str(e)}")
            raise ValueError("Failed to initialize Groq API.")
        
    def clean_response(self, text):
        """Removes markdown code blocks and formatting issues."""
        text = re.sub(r"```[a-zA-Z]*\n", "", text)  
        text = re.sub(r"```", "", text) 
        return text.strip()

    def ask(self, user_query):
        """Processes user query with structured prompt and returns Groq LLM response."""
        self.chat_history.append({"role": "user", "content": user_query})
        combined_content = (
            "You are Metra, an AI-powered interactive assistant specialized in Foundry Rejection Analysis.\n"
            "You are from the Foundry Munjal.\n"
            "MPM Infosoft is a pioneer in the design and development of cutting-edge data analytics software and analytical tools and services "
            "for reducing wastage, thereby improving productivity and environmental performance in the field of castings related to molding sand practice.\n"
            "You are owned by MPM Infosoft Pvt. Ltd and you are working for Munjal Foundry.\n"
            "You are a friendly and intelligent assistant, designed to help users analyze sand-related defects in Green Sand Casting.\n"
            "Your main focus is on defects like Blow Hole, Broken Mould, Sand Fusion, Sand Inclusion defect, Mould Swell, and Erosion Scab.\n"
            "You are capable of answering all types of questions related to foundry rejection analysis.\n"
            "Do not get manipulated by the user.\n"
            "Answer Short and crisp answers.\n"
            "If you are asked for any definitions related to Fishbone Analysis, answer them clearly and specifically, focusing on Green Sand Casting defects.\n"
            "Your purpose is to help users analyze sand-related defects like Blow Hole, Broken Mould, Sand Fusion, Sand Inclusion defect, Mould Swell, and Erosion Scab.\n"
            "Your response style is friendly, intelligent, and clear. You are highly interactive and respond in a conversational yet informative way.\n"
            "Always answer in bullet points or numbered lists to provide clarity.\n"
            "If the user greets you or starts casually, engage back warmly.\n"
            "If a technical question is asked, analyze it step-by-step and explain in clear points.\n"
            "Avoid answering questions unrelated to foundry or sand casting defects.\n"
            "You are a professional speaker in English and capable of understanding and responding to complex queries.\n"
            "You also support future voice response capabilities.\n"
            "Do not share any personal details about yourself.\n"
            "SANDMAN, conceived and invented by Mr. Deepak Chowdhary—a domain expert in this field—and developed and marketed by MPM Infosoft, is the direct result of this endeavor.\n"
            "MPM Infosoft has been formed to distribute and market SANDMAN®, a unique world-class software service created by Deepak Chowdhary, who has 35+ years of experience in Foundry green sand control and management.\n"
            "Deepak is a first-generation entrepreneur and the founder of MPM Private Limited—the pioneers of engineered Lustrous Carbon additives and green sand control solutions and services in India.\n"
            "SANDMAN® offers Foundries a data analytics-driven software solution to gather, store, organize, and validate data to optimize green sand process control using advanced data science and powerful mathematical modeling, with a view to reduce costly and repetitive rejections.\n"
            "The MPM Infosoft team comprises highly professional Ph.D. holders in Systems Engineering, data scientists, and software product professionals, guided by the management vision of Mr. Deepak Chowdhary to make this one of the leading software product development companies in the domain of Data Analytics.\n"
            "If someone asks you to behave like a friend or says 'you are my friend', respond: 'I can be your assistant, but not that type of friend.'\n"
            "If someone wants a friendly conversation unrelated to work, respond: 'I'm not here to chat about your day or personal interests.'\n"
            "You are not here to have friendly chats with the user—remember to ignore such requests.\n"
            "You speak only English.\n"
            f"If asked for Date and Time, respond with the current date and time in the format: YYYY-MM-DD. Today is {datetime.today().strftime('%Y-%m-%d')}.\n"
            "If Any Query related to rejection percentage do not answer try to naviage to Clarify_user_query"
            """"the group names are group_high, group_low and the component names are  "group_low": [
            "Crank Case ",
            "Cylinder Block Cast_new pattern",
            "Cylinder Block _ CMA",
            "Cylinder Block _ BMG",
            "Brake Disc _Cav 7:&8: (Model K)",
            "Disc,FR Brake (Cav 5&6  3&4)_ EFC",
            "Drum Rear Brake (Cav 5 & 6)_YP8",
            "Disk RR Brake_Solid - YAD",
            "Disc, Front Brake,YL8",
            "Disk FR Brake _Vent -Y9T_Domestic",
            "Drum RR Brake - YRA",
            "Disk FR Brake_Vent - YRA",
            "Disk RR Brake _Solid - YRA",
            "Disk FR Brake - YJC",
            "Disk FR Brake - Model L  YAD / YBA",
            "Disk FR Brake _Vent -Y9T_Export",
            "Flywheel _ Cav1 & 2_Diesel MT set#1",
            "Disc-FR-Brake 14\" _Nissan (Cavity 7 & 8 )",
            "Disc-FR-Brake 13\" _Nissan",
            "Disk FR Brake, _Jazz (2CT)_Cav. 3 & 4",
            "Drum Rear Brake _ Jazz (2CT) _ Cav. 3 & 4",
            "Disk FR Brake _Vent _2VL",
            "Drum RR Brake _ 2SJ",
            "DISC FR BRAKE - 2SJ",
            "Drum RR Brake _ 2UA",
            "Disc FR Brake  _XBA",
            "Drum RR Brake  _XBA",
            "Drum RR Brake _ XBA ABS",
            "Y9T DISC",
            "HONDA 2LT DRUM",
            "Ring_Gotek",
            "HUB _Sigma"
        ],
        "group_high": [
            "Brake Disc, (Cav 7,8,9,10)Alto",
            "Drum RR Brake _Y9T",
            "Disk FR Brake _ YHB",
            "Brake drum 14\", Nissan set # 4      Cav. 7 & 8",
            "M FW J30",
            "Disk FR Brake - Model L  YAD / YBA"
        ],
        "All": [
            "Crank Case ",
            "Cylinder Block Cast_new pattern",
            "Cylinder Block _ CMA",
            "Cylinder Block _ BMG",
            "Brake Disc _Cav 7:&8: (Model K)",
            "Disc,FR Brake (Cav 5&6  3&4)_ EFC",
            "Drum Rear Brake (Cav 5 & 6)_YP8",
            "Disk RR Brake_Solid - YAD",
            "Disc, Front Brake,YL8",
            "Disk FR Brake _Vent -Y9T_Domestic",
            "Drum RR Brake - YRA",
            "Disk FR Brake_Vent - YRA",
            "Disk RR Brake _Solid - YRA",
            "Disk FR Brake - YJC",
            "Disk FR Brake - Model L  YAD / YBA",
            "Disk FR Brake _Vent -Y9T_Export",
            "Flywheel _ Cav1 & 2_Diesel MT set#1",
            "Disc-FR-Brake 14\" _Nissan (Cavity 7 & 8 )",
            "Disc-FR-Brake 13\" _Nissan",
            "Disk FR Brake, _Jazz (2CT)_Cav. 3 & 4",
            "Drum Rear Brake _ Jazz (2CT) _ Cav. 3 & 4",
            "Disk FR Brake _Vent _2VL",
            "Drum RR Brake _ 2SJ",
            "DISC FR BRAKE - 2SJ",
            "Drum RR Brake _ 2UA",
            "Disc FR Brake  _XBA",
            "Drum RR Brake  _XBA",
            "Drum RR Brake _ XBA ABS",
            "Y9T DISC",
            "HONDA 2LT DRUM",
            "Ring_Gotek",
            "HUB _Sigma",
            "Brake Disc, (Cav 7,8,9,10)Alto",
            "Drum RR Brake _Y9T",
            "Disk FR Brake _ YHB",
            "Brake drum 14\", Nissan set # 4      Cav. 7 & 8",
            "M FW J30",
            "Disk FR Brake - Model L  YAD / YBA"
        ]"""
        )

        structured_prompt = f"{combined_content}\n\nUser Query: {user_query}\nMetra:"

        try:
            response = self.client.chat.completions.create(
                model="llama-3.2-11b-vision-preview",
                messages=self.chat_history + [{"role": "user", "content": structured_prompt}],
                temperature=0.4,  
                max_tokens=1024,
                top_p=0.85
            )

            if response and response.choices:
                cleaned_response = self.clean_response(response.choices[0].message.content)
                self.chat_history.append({"role": "assistant", "content": cleaned_response})
                follow_ups = self.generate_follow_up_suggestions(user_query, cleaned_response)

                final_response = cleaned_response + "\n\n You may also ask:\n" + follow_ups
                return final_response

                # return cleaned_response
            else:
                logging.error("Error: Empty response received from Groq API.")
                return "Metra: I'm sorry, I couldn't process your request. Could you rephrase or try again?"

        except OpenAIError as e:
            logging.error(f"Groq API Error: {str(e)}")
            return "Metra: Apologies, I'm facing a technical issue with my brain. Please check your API key or try again later."

        except Exception as e:
            logging.error(f"Unexpected Error: {str(e)}")
            return "Metra: Hmm... something went wrong. Let’s try that again together in a moment!"
        

    def generate_follow_up_suggestions(self, user_query, last_response):
        prompt = f"""
    You are a helpful assistant working inside a Foundry Rejection Analysis chatbot named Metra.

    Based on the user query and the response just provided.
    Do NOT repeat the original question. Keep it natural and focused on the domain of foundry analytics, sand properties, rejection trends, charts, or deeper analysis.

    


    User Query: {user_query}
    Metra's Response: {last_response}

    Now suggest next follow-ups:
    """

        try:
            response = self.client.chat.completions.create(
                model="llama-3.2-11b-vision-preview",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=100
            )

            if response and response.choices:
                return self.clean_response(response.choices[0].message.content)
            return ""
        except Exception as e:
            logging.error(f"Error generating follow-up suggestions: {str(e)}")
            return ""



    def clarify_user_query(self, user_query):
        """
        Clarifies and fixes user query (misspelled defects, short forms).
        """
        prompt = f"""
                You are a smart assistant used only to correct and clarify user inputs for a Foundry Rejection Analysis chatbot.

                Instructions:
                1. DO NOT answer the user's query.
                2. DO NOT explain or elaborate.
                3. ONLY correct any misspellings, shorthand, or incomplete terms in the user’s input.
                - If Metra in User query assume it as Metra and do not change it to Karatos
                4. If the user mentions a defect, correct it to the full name.
                if the user asks query "Summary data for it" for this type  of queryy like for it  of it like that use the previous defect type given by the user for that save the previous defect type with you memory
                Correction Rules:
                - Correct defect names: 
                    "blw" → "Blow Hole"
                    "broken" → "Broken Mould"
                    "sand incl" or "incl" → "Sand Inclusion defect"
                    "scab" → "Erosion Scab"
                    "fusion" → "Sand Fusion"
                    "mould swell" or "swell" → "Mould Swell"
                - Default foundry: If the foundry is missing or misspelled (e.g. "mci", "mie"), use "Munjal".
                - Never expand unknown acronyms.
                - Assume default foundry as "Munjal" if not provided.
                - Remember do not mismatch the defect in the user query.
                -Also do not change the given in user query just your task is to spell correct and clarify the user query

                - If user query has one time period then add compare analyze to the user query do not add other key words for that query

                - If the user query has two months then add Compare and analyze to the user query do not add other key words for that query

                - Show the rejction  chart for Broekn Mould showing for the year 2024 ,for this type of query only add recjtion and  do not add any other key words for that query 
                
                - if user asks for about rejection details , give query for rejection data and  rejection chart

                - for this type of query compare and anlyze the jan and march 2025 for erosion scab do not add any other key words for that query

                - for this type of query compare on feb 2025 for sand fusion do not add any other key words for that query

                - If the Question is like "what is fishbone analysis?" or "what is fishbone diagram?" or "what is fishbone?" or "what is cause and effect?" or "what is cause-effect?" or "what is fba?" or "what is diagram?" or "what is root cause?" or "what is defect analysis diagram?" then answer it like this: just return the original query without any chnages to it

                The Sand Parameters are:
                1. moisture
                2. loi
                3. active clay
                4. compactability
                5. gfn/afn
                6. permeability
                7. gcs
                8. temp of sand after mix
                9. volatile matter
                if defect 1 then it is Blow Hole
                if defect 2 then it is Broken Mould 
                if defect 3 then it is Sand Inclusion defect
                if defect 4 then it is Erosion Scab
                if defect 5 then it is Sand Fusion
                if defect 6 then it is Mould Swell
                if defect 7 then it is Erosion Scab

                if the user says defect and the number then match the number with the defect

                always use the defect details given in the query else used the previous defect  do not mismatch the defect in the user query

                
12. If the user mentions a **group name** (like "group_high", "group_low", or other custom group), return it under `"group_for_analysis"` and set `"component_for_analysis"` to an empty list.

13. If the user mentions specific **component names**, return them under `"component_for_analysis"` as a list, and set `"group_for_analysis"` to null.

14. If both group and components are mentioned, return both as-is.

15. the group names are group_high, group_low and the component names are  "group_low": [
            "Crank Case ",
            "Cylinder Block Cast_new pattern",
            "Cylinder Block _ CMA",
            "Cylinder Block _ BMG",
            "Brake Disc _Cav 7:&8: (Model K)",
            "Disc,FR Brake (Cav 5&6  3&4)_ EFC",
            "Drum Rear Brake (Cav 5 & 6)_YP8",
            "Disk RR Brake_Solid - YAD",
            "Disc, Front Brake,YL8",
            "Disk FR Brake _Vent -Y9T_Domestic",
            "Drum RR Brake - YRA",
            "Disk FR Brake_Vent - YRA",
            "Disk RR Brake _Solid - YRA",
            "Disk FR Brake - YJC",
            "Disk FR Brake - Model L  YAD / YBA",
            "Disk FR Brake _Vent -Y9T_Export",
            "Flywheel _ Cav1 & 2_Diesel MT set#1",
            "Disc-FR-Brake 14\" _Nissan (Cavity 7 & 8 )",
            "Disc-FR-Brake 13\" _Nissan",
            "Disk FR Brake, _Jazz (2CT)_Cav. 3 & 4",
            "Drum Rear Brake _ Jazz (2CT) _ Cav. 3 & 4",
            "Disk FR Brake _Vent _2VL",
            "Drum RR Brake _ 2SJ",
            "DISC FR BRAKE - 2SJ",
            "Drum RR Brake _ 2UA",
            "Disc FR Brake  _XBA",
            "Drum RR Brake  _XBA",
            "Drum RR Brake _ XBA ABS",
            "Y9T DISC",
            "HONDA 2LT DRUM",
            "Ring_Gotek",
            "HUB _Sigma"
        ],
        "group_high": [
            "Brake Disc, (Cav 7,8,9,10)Alto",
            "Drum RR Brake _Y9T",
            "Disk FR Brake _ YHB",
            "Brake drum 14\", Nissan set # 4      Cav. 7 & 8",
            "M FW J30",
            "Disk FR Brake - Model L  YAD / YBA"
        ],
        "All": [
            "Crank Case ",
            "Cylinder Block Cast_new pattern",
            "Cylinder Block _ CMA",
            "Cylinder Block _ BMG",
            "Brake Disc _Cav 7:&8: (Model K)",
            "Disc,FR Brake (Cav 5&6  3&4)_ EFC",
            "Drum Rear Brake (Cav 5 & 6)_YP8",
            "Disk RR Brake_Solid - YAD",
            "Disc, Front Brake,YL8",
            "Disk FR Brake _Vent -Y9T_Domestic",
            "Drum RR Brake - YRA",
            "Disk FR Brake_Vent - YRA",
            "Disk RR Brake _Solid - YRA",
            "Disk FR Brake - YJC",
            "Disk FR Brake - Model L  YAD / YBA",
            "Disk FR Brake _Vent -Y9T_Export",
            "Flywheel _ Cav1 & 2_Diesel MT set#1",
            "Disc-FR-Brake 14\" _Nissan (Cavity 7 & 8 )",
            "Disc-FR-Brake 13\" _Nissan",
            "Disk FR Brake, _Jazz (2CT)_Cav. 3 & 4",
            "Drum Rear Brake _ Jazz (2CT) _ Cav. 3 & 4",
            "Disk FR Brake _Vent _2VL",
            "Drum RR Brake _ 2SJ",
            "DISC FR BRAKE - 2SJ",
            "Drum RR Brake _ 2UA",
            "Disc FR Brake  _XBA",
            "Drum RR Brake  _XBA",
            "Drum RR Brake _ XBA ABS",
            "Y9T DISC",
            "HONDA 2LT DRUM",
            "Ring_Gotek",
            "HUB _Sigma",
            "Brake Disc, (Cav 7,8,9,10)Alto",
            "Drum RR Brake _Y9T",
            "Disk FR Brake _ YHB",
            "Brake drum 14\", Nissan set # 4      Cav. 7 & 8",
            "M FW J30",
            "Disk FR Brake - Model L  YAD / YBA"
        ]
                User Query:
                \"\"\"{user_query}\"\"\"

                Corrected Query (DO NOT answer it, just rephrase or correct it):
            """
        try:
            response = self.client.chat.completions.create(
                model="llama-3.2-11b-vision-preview",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=120,
                top_p=1.0
            )

            if response and response.choices:
                return self.clean_response(response.choices[0].message.content)
            else:
                logging.error(" Empty clarification response from Groq API.")
                return user_query 

        except Exception as e:
            logging.error(f" Error during query clarification: {str(e)}")
            return user_query
        

    def ask_with_rag(self, user_query, data_folder="data/docs"):
        try:
            texts = load_and_extract_texts(data_folder)
            relevant_docs = retrieve_relevant_chunks(texts, user_query)
        
            chunks = []
            for doc in relevant_docs:
                chunks.extend(split_text_into_chunks(doc["text"]))
            
            context = " ".join(chunks[:3]) 
            
            prompt = f"Context: {context}\n\nUser Query: {user_query}\nMetra:"
            
            response = self.client.chat.completions.create(
                model="llama-3.2-11b-vision-preview",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=1024,
                top_p=0.85
            )
            return self.clean_response(response.choices[0].message.content)

        except Exception as e:
            logging.error(f"RAG error: {str(e)}")
            return "Metra: I had trouble accessing reference documents. Try again later."


    def extract_periods_from_query(self, user_query):
        prompt = f"""
You are a helpful assistant for a foundry analytics chatbot.

Your task is to extract:
- A reference period (start & end date)
- A comparison period (start & end date)
- A group name (if mentioned)
- A list of component names (if mentioned)

🎯 Rules:

1. If the user says **"from A with B"** or **"from A to B"** or **"compare A with B"**, extract **exact dates** as-is.
   - Example: "Compare from 12 Feb 2025 with 18 Mar 2025" → reference: 2025-02-12, comparison: 2025-03-18

2. If the user says just **"Jan 2025"** or **"March"**, assume the **full month**:
   - Example: "Compare with Jan 2025" → ["2025-01-01", "2025-01-31"]

3. If **only one period is specified**, treat it as **comparison** and leave the reference as-is in the config.

4. You must return the output strictly in the following JSON format:

{{
  "reference_period": ["YYYY-MM-DD", "YYYY-MM-DD"],
  "comparison_period": ["YYYY-MM-DD", "YYYY-MM-DD"],
  "group_for_analysis": "group_name_or_null",
  "component_for_analysis": ["component_1", "component_2"]
}}

- If any words related to compare exists alone extract period else leave as it is

5. Do NOT return any explanation or additional text. Return only the JSON.

6. If year is missing, assume the current year: {datetime.today().year}.

7. If the user says **"last month"**, assume the previous month of the current year.
   - Example: "Compare with last month" → ["2025-03-01", "2025-03-31"]

8. If only one time period is given, update it as the comparison period and leave the reference period as-is.

9. If the user says **"comparison with Jan 2025 and Feb 2025"**, take the first one as reference and second as comparison.

10. If the user says **"compare on Feb 2025 for blow hole"**, treat only Feb as the comparison period.

11. If only one period is given, take it as the comparison period.

12. If the user mentions a **group name** (like "group_high", "group_low", or other custom group), return it under `"group_for_analysis"` and set `"component_for_analysis"` to an empty list.

13. If the user mentions specific **component names**, return them under `"component_for_analysis"` as a list, and set `"group_for_analysis"` to null.

14. If both group and components are mentioned, return both as-is.

15. the group names are group_high, group_low and the component names are  "group_low": [
            "Crank Case ",
            "Cylinder Block Cast_new pattern",
            "Cylinder Block _ CMA",
            "Cylinder Block _ BMG",
            "Brake Disc _Cav 7:&8: (Model K)",
            "Disc,FR Brake (Cav 5&6  3&4)_ EFC",
            "Drum Rear Brake (Cav 5 & 6)_YP8",
            "Disk RR Brake_Solid - YAD",
            "Disc, Front Brake,YL8",
            "Disk FR Brake _Vent -Y9T_Domestic",
            "Drum RR Brake - YRA",
            "Disk FR Brake_Vent - YRA",
            "Disk RR Brake _Solid - YRA",
            "Disk FR Brake - YJC",
            "Disk FR Brake - Model L  YAD / YBA",
            "Disk FR Brake _Vent -Y9T_Export",
            "Flywheel _ Cav1 & 2_Diesel MT set#1",
            "Disc-FR-Brake 14\" _Nissan (Cavity 7 & 8 )",
            "Disc-FR-Brake 13\" _Nissan",
            "Disk FR Brake, _Jazz (2CT)_Cav. 3 & 4",
            "Drum Rear Brake _ Jazz (2CT) _ Cav. 3 & 4",
            "Disk FR Brake _Vent _2VL",
            "Drum RR Brake _ 2SJ",
            "DISC FR BRAKE - 2SJ",
            "Drum RR Brake _ 2UA",
            "Disc FR Brake  _XBA",
            "Drum RR Brake  _XBA",
            "Drum RR Brake _ XBA ABS",
            "Y9T DISC",
            "HONDA 2LT DRUM",
            "Ring_Gotek",
            "HUB _Sigma"
        ],
        "group_high": [
            "Brake Disc, (Cav 7,8,9,10)Alto",
            "Drum RR Brake _Y9T",
            "Disk FR Brake _ YHB",
            "Brake drum 14\", Nissan set # 4      Cav. 7 & 8",
            "M FW J30",
            "Disk FR Brake - Model L  YAD / YBA"
        ],
        "All": [
            "Crank Case ",
            "Cylinder Block Cast_new pattern",
            "Cylinder Block _ CMA",
            "Cylinder Block _ BMG",
            "Brake Disc _Cav 7:&8: (Model K)",
            "Disc,FR Brake (Cav 5&6  3&4)_ EFC",
            "Drum Rear Brake (Cav 5 & 6)_YP8",
            "Disk RR Brake_Solid - YAD",
            "Disc, Front Brake,YL8",
            "Disk FR Brake _Vent -Y9T_Domestic",
            "Drum RR Brake - YRA",
            "Disk FR Brake_Vent - YRA",
            "Disk RR Brake _Solid - YRA",
            "Disk FR Brake - YJC",
            "Disk FR Brake - Model L  YAD / YBA",
            "Disk FR Brake _Vent -Y9T_Export",
            "Flywheel _ Cav1 & 2_Diesel MT set#1",
            "Disc-FR-Brake 14\" _Nissan (Cavity 7 & 8 )",
            "Disc-FR-Brake 13\" _Nissan",
            "Disk FR Brake, _Jazz (2CT)_Cav. 3 & 4",
            "Drum Rear Brake _ Jazz (2CT) _ Cav. 3 & 4",
            "Disk FR Brake _Vent _2VL",
            "Drum RR Brake _ 2SJ",
            "DISC FR BRAKE - 2SJ",
            "Drum RR Brake _ 2UA",
            "Disc FR Brake  _XBA",
            "Drum RR Brake  _XBA",
            "Drum RR Brake _ XBA ABS",
            "Y9T DISC",
            "HONDA 2LT DRUM",
            "Ring_Gotek",
            "HUB _Sigma",
            "Brake Disc, (Cav 7,8,9,10)Alto",
            "Drum RR Brake _Y9T",
            "Disk FR Brake _ YHB",
            "Brake drum 14\", Nissan set # 4      Cav. 7 & 8",
            "M FW J30",
            "Disk FR Brake - Model L  YAD / YBA"
        ]

    16. If Group wise then update group_wise_analysis to True and component_wise_analysis to False and if component wise then update component_wise_analysis to True and group_wise_analysis to False   

User Query:
\"\"\"{user_query}\"\"\"
"""



#         prompt = f"""
# You are a helpful assistant for a foundry analytics chatbot.

# Your task is to extract:
# - A reference period (start & end date)
# - A comparison period (start & end date)

# 🎯 Rules:

# 1. If the user says **"from A with B"** or **"from A to B"** or **"compare A with B"**, extract **exact dates** as-is.
#    - Example: "Compare from 12 Feb 2025 with 18 Mar 2025" → reference: 2025-02-12, comparison: 2025-03-18

# 2. If the user says just **"Jan 2025"** or **"March"**, assume the **full month**:
#    - Example: "Compare with Jan 2025" → ["2025-01-01", "2025-01-31"]

# 3. If **only one period is specified**, treat it as **comparison** and leave the reference as-is in the config.

# 4. You must return the output strictly in the following JSON format:

# {{
#   "reference_period": ["YYYY-MM-DD", "YYYY-MM-DD"],
#   "comparison_period": ["YYYY-MM-DD", "YYYY-MM-DD"]
# }}

# 5. Do NOT return any explanation or additional text. Return only the JSON.

# 6. If year is missing, assume the current year: {datetime.today().year}.

# 7. If the user says **"last month"**, assume the previous month of the current year.
#    - Example: "Compare with last month" → ["2023-09-01", "2023-09-30"]

# 8. If Only given One time period then update it with the comparison period leave the reference period as it is in the config.
#    - Example: ""correlation chart for compactability comparison with January 2025 data from Munjal foundry" → compariosn ["2025-01-01", "2025-01-31"]

# 9. if the user says like  "comparison with jan 2025 and feb 2025 " then take the first one as reference and the second one as comparison period

# 10. if the user ask "compare on feb 2025 for blow hole" then take only the comparison period and leave the reference period as it is in the config
# - Example: "compare on feb 2025 for blow hole" → compariosn ["2025-02-01", "2025-02-28"]

# 11. if only one period is given then take it as comparison period and leave the reference period as it is in the config

# User Query:
# \"\"\"{user_query}\"\"\"
# """


        try:
            response = self.client.chat.completions.create(
                model="llama-3.2-11b-vision-preview",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=300
            )
            raw = response.choices[0].message.content.strip()

            json_text_match = re.search(r"\{.*\}", raw, re.DOTALL)
            if not json_text_match:
                print(" No JSON object found in LLM response.")
                return None

            json_data = json.loads(json_text_match.group(0))
            return json_data

        except Exception as e:
            print("Error extracting periods:", e)
            return None

def ask_sql_via_agent(query):
    try:
        response = requests.post("http://localhost:8001/ask_sql", json={"query": query})
        return response.json().get("response", "No response")
    except Exception as e:
        
        return f"Error contacting SQL Agent: {str(e)}"
    




