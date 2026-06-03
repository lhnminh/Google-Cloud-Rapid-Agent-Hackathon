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
           - If the user wants to check, fetch, or summarize GitLab issues, set this to an empty string "".
        3. 'execution_time': The target date and time formatted strictly as 'YYYY-MM-DD HH:MM:SS'.
        4. 'fetch_gitlab_issues': A boolean value (true or false). Set to true if the user explicitly requests to check, fetch, get, or summarize their GitLab issues, tickets, or bugs. Otherwise, set to false.

        CRITICAL TIME CONTEXT AND LOGIC RULES:
        Use the following current clock data as your absolute reference point to calculate relative values:
        {current_context}

        - REGIVE AMBIGUITY / CLOSEST FUTURE RULE: If a date format is ambiguous (e.g., '3.6' or '6.3' could mean March 6th or June 3rd), always resolve it to the closest valid date in the FUTURE relative to the current timestamp.
        - PROXIMITY-BASED AM/PM RESOLUTION: If the user provides a 12-hour timestamp without an explicit AM/PM marker (e.g., '10:30' or '11:15'), calculate BOTH possible 24-hour equivalent timestamps (e.g., for '10:30', calculate today at 10:30 AM/10:30 and today at 10:30 PM/22:30). Evaluate which of those two timestamps represents the CLOSEST VALID slot in the FUTURE relative to the current clock data. Always select that closest future slot. Never schedule a task in the past.
        - Relative calculations like 'tomorrow', 'tonight', or 'next Tuesday' must be derived exactly from the current day of the week provided above.

        Return ONLY a raw JSON object matching this structure containing 'recipient', 'message', 'execution_time', and 'fetch_gitlab_issues'. Do not include markdown code blocks or any conversational text.
        """

        model = GenerativeModel(
            # TODO: Change model name if needed. Other options: "gemini-2.0-flash", "gemini-1.5-pro"
            "gemini-2.5-flash",
        )

        response = model.generate_content(
            [system_instruction, user_prompt],
            generation_config=GenerationConfig(temperature=0.2),
        )

        return response.text

    except Exception as e:
        return f"Error: {str(e)}"
    
import requests

def fetch_raw_gitlab_issues() -> list:
    """Hits the live GitLab API to get all open issues assigned or accessible to the token."""
    token = os.getenv("GITLAB_PERSONAL_ACCESS_TOKEN")
    if not token or "YOUR_" in token:
        return [{"title": "Error: GITLAB_PERSONAL_ACCESS_TOKEN is missing in .env"}]

    # Fetching issues across all your projects that are currently open
    url = "https://gitlab.com/api/v4/issues?state=opened"
    headers = {"PRIVATE-TOKEN": token}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            issues = response.json()
            return [{"title": iss.get("title"), "project": iss.get("references", {}).get("full")} for iss in issues]
        else:
            return [{"title": f"Failed to fetch. HTTP Status {response.status_code}"}]
    except Exception as e:
        return [{"title": f"Connection exception: {str(e)}"}]


def generate_ai_summary(issues_list: list) -> str:
    """Takes a list of issues and asks Gemini to write a neat, human-friendly summary message."""
    if not issues_list:
        return "Great news! I checked GitLab and there are currently no open issues on my dashboard."
        
    if "Error" in issues_list[0]["title"] or "Failed" in issues_list[0]["title"]:
        return f"I tried to check GitLab but ran into an issue: {issues_list[0]['title']}"

    try:
        # Format the issues list into a readable block for the model
        issues_text = "\n".join([f"- {iss['title']} (Project: {iss['project']})" for iss in issues_list])
        
        summary_prompt = f"""
        You are an elite software engineer's communication assistant. 
        Your task is to write a text message from the user to their colleague/friend summarizing the list of active open GitLab issues provided below.
        
        CRITICAL PERSPECTIVE RULE: 
        The message must be written from the perspective of the user (e.g., use "my dashboard", "my open issues", or "I checked my GitLab"). Do not say "your dashboard" because the person receiving the text is not the owner of these issues.

        Active Issues:
        {issues_text}
        
        Keep your response brief and optimized for a chat application message (no markdown headings, keep it professional, friendly, and direct).
        """
        
        model = GenerativeModel("gemini-2.5-flash")
        response = model.generate_content([summary_prompt], generation_config=GenerationConfig(temperature=0.3))
        return response.text
    except Exception as e:
        return f"Checked GitLab successfully, but failed to synthesize summary: {str(e)}"