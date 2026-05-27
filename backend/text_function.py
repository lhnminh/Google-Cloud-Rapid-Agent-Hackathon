import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

def generate_ai_text(user_prompt: str) -> str:
    try:
        client = genai.Client()

        # Define a configuration to control the model behavior
        config = types.GenerateContentConfig(
            # Tell the AI how to behave before it reads the prompt
            system_instruction="You are a precise backend assistant. Do not provide a list of options. Do not provide multiple choices. Provide exactly ONE final response or message directly based on the user's request. No commentary, no intro, no outro.",
            
            # Tell the API to only generate 1 candidate response
            candidate_count=1, 
            
            # Low temperature makes the AI more focused and less likely to wander into multiple ideas
            temperature=0.3, 
        )
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_prompt,
            config=config,
        )
        
        return response.text
        
    except Exception as e:
        return f"An error occurred: {str(e)}"

# Simple Local Test
if __name__ == "__main__":
    test_prompt = "Write a short, cool birthday message for Minh."
    print(f"Prompt: {test_prompt}\n")
    
    ai_response = generate_ai_text(test_prompt)
    print(f"AI Response:\n{ai_response}")