import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

def generate_ai_text(user_prompt: str) -> str:
    try:
        client = genai.Client()
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_prompt,
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