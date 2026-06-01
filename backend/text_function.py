import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load .env from current working directory or fall back to project root
load_dotenv()
root_env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(root_env):
    load_dotenv(root_env)

def extract_schedule_details(user_prompt: str) -> str:
    try:
        client = genai.Client()
        
        system_instruction = """
        You are an advanced scheduling parser and message generator. 
        Analyze the user prompt and extract or generate the following pieces:
        
        1. 'recipient': The name of the person receiving the message.
        2. 'message': The exact content to send. 
           - If the user specifies exactly what to say (e.g., 'say hello' or 'tell them I am running late'), use that exact message.
           - If the user gives an intent (e.g., 'wish them a happy anniversary'), generate a highly appropriate, tailored, and creative message matching that intent.
        3. 'execution_time': The target date and time formatted strictly as 'YYYY-MM-DD HH:MM:SS'. 
           Assume the current year is 2026. If the user says 'at 14:30 tomorrow', compute the exact timestamp.
        
        Return ONLY a raw JSON object matching this structure. Do not include markdown code blocks or any conversational text.
        """
        
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.2, 
        )
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_prompt,
            config=config,
        )
        
        return response.text
        
    except Exception as e:
        return f"Error: {str(e)}"
    
