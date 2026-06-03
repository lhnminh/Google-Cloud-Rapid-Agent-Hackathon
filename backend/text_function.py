import os
from datetime import datetime
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
from dotenv import load_dotenv

# Load .env from current working directory or fall back to project root
load_dotenv()
root_env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(root_env):
    load_dotenv(root_env)

# ---------------------------------------------------------------------------
# TODO: Set your Google Cloud project ID and region below, or define
#       GCP_PROJECT_ID and GCP_LOCATION in your .env file.
#
#   GCP_PROJECT_ID — your GCP project ID (e.g. "my-project-123")
#   GCP_LOCATION   — Vertex AI region (e.g. "us-central1", "us-east1")
#
# Before running, authenticate once with:
#   gcloud auth application-default login
# ---------------------------------------------------------------------------
_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "YOUR_PROJECT_ID")
_LOCATION = os.getenv("GCP_LOCATION", "us-central1")

vertexai.init(project=_PROJECT_ID, location=_LOCATION)

def extract_schedule_details(user_prompt: str) -> str:
    try:
        now = datetime.now()
        current_context = (
            f"Current Timestamp: {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Current Day of Week: {now.strftime('%A')}"
        )

        system_instruction = f"""
        You are an advanced scheduling parser and message generator.
        Analyze the user prompt and extract or generate the following pieces:

        1. 'recipient': The name of the person receiving the message.
        2. 'message': The exact content to send.
           - If the user specifies exactly what to say (e.g., 'say hello' or 'tell them I am running late'), use that exact message.
           - If the user gives an intent (e.g., 'wish them a happy anniversary'), generate a highly appropriate, tailored, and creative message matching that intent.
        3. 'execution_time': The target date and time formatted strictly as 'YYYY-MM-DD HH:MM:SS'.

        CRITICAL TIME CONTEXT AND LOGIC RULES:
        Use the following current clock data as your absolute reference point to calculate relative values:
        {current_context}

        - REGIVE AMBIGUITY / CLOSEST FUTURE RULE: If a date format is ambiguous (e.g., '3.6' or '6.3' could mean March 6th or June 3rd), always resolve it to the closest valid date in the FUTURE relative to the current timestamp.
        - INTELLIGENT AM/PM WRAPPING: If the user provides a raw 12-hour timestamp without an explicit AM/PM marker (e.g., '1:00'), and that time has already passed for the current day, assume they intended the upcoming afternoon/evening slot (e.g., if it is currently 11:00 AM, '1:00' must be interpreted as 13:00:00).
        - Relative calculations like 'tomorrow', 'tonight', or 'next Tuesday' must be derived exactly from the current day of the week provided above.

        Return ONLY a raw JSON object matching this structure. Do not include markdown code blocks or any conversational text.
        """

        model = GenerativeModel(
            # TODO: Change model name if needed. Other options: "gemini-2.0-flash", "gemini-1.5-pro"
            "gemini-2.5-flash-preview-05-20",
            system_instruction=system_instruction,
        )

        response = model.generate_content(
            user_prompt,
            generation_config=GenerationConfig(temperature=0.2),
        )

        return response.text

    except Exception as e:
        return f"Error: {str(e)}"