import json
import time
import os
import sys
from datetime import datetime
from tzlocal import get_localzone

# Add the backend directory to sys.path to allow execution from anywhere
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from text_function import extract_schedule_details
from browser_agent import run_browser_agent
# pyrefly: ignore [missing-import]
from playwright.sync_api import sync_playwright
# pyrefly: ignore [missing-import]
from apscheduler.schedulers.blocking import BlockingScheduler
# pyrefly: ignore [missing-import]
from apscheduler.schedulers.background import BackgroundScheduler
# pyrefly: ignore [missing-import]
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

import requests

def get_automated_timezone():
    """Dynamically detects the exact timezone automatically in any environment globally."""
    # 1. Local Check: If running in Docker with mounted volumes, trust the host system
    try:
        from tzlocal import get_localzone
        local_tz = str(get_localzone())
        if local_tz and local_tz != "UTC":
            return local_tz
    except Exception:
        pass

    # 2. Global Cloud Check: Query a live IP API to find out exactly where this container is running
    try:
        # ipapi.co is free, requires no API keys, and returns a clean text timezone string
        response = requests.get("https://ipapi.co/timezone/", timeout=3)
        if response.status_code == 200:
            detected_tz = response.text.strip()
            if detected_tz:
                return detected_tz
    except Exception as e:
        print(f"Warning: Global IP timezone lookup skipped: {e}")

    # 3. Cloud Provider Metadata Backup
    try:
        headers = {"Metadata-Flavor": "Google"}
        zone_url = "http://metadata.google.internal/computeMetadata/v1/instance/zone"
        zone_response = requests.get(zone_url, headers=headers, timeout=2)
        if zone_response.status_code == 200:
            full_zone = zone_response.text
            region = full_zone.split('/')[-1].rsplit('-', 1)[0]
            
            # Expanded baseline mappings
            region_tz_mapping = {
                "us-central1": "America/Chicago",
                "us-east1": "America/New_York",
                "us-west1": "America/Los_Angeles",
                "asia-east1": "Asia/Taipei",
                "asia-southeast1": "Asia/Singapore",
                "asia-southeast2": "Asia/Jakarta",
                "europe-west1": "Europe/Brussels",
                "europe-west2": "Europe/London"
            }
            return region_tz_mapping.get(region, "UTC")
    except Exception:
        pass

    return "UTC"  # Absolute fallback if the container is completely offline on startup

# Initialize background scheduler with true automated timezone discovery
detected_timezone = get_automated_timezone()
print(f"🌍 [Timezone Engine]: Automatically initialized using zone: {detected_timezone}")

bg_scheduler = BackgroundScheduler(timezone=detected_timezone)
bg_scheduler.start()

def parse_json_response(raw: str) -> dict:
    """Robustly parse a JSON string that may be wrapped in markdown triple backticks."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        # Remove markdown triple backtick lines
        lines = cleaned.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return json.loads(cleaned)

def verify_login_session():
    print("\nPerforming Immediate Pre-Flight Login Check...")
    session_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sessions", "facebook")
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=session_dir,
            headless=False
        )
        page = browser.new_page()
        page.goto("https://www.facebook.com/messages")
        
        page.wait_for_timeout(3000)
        
        print("\n-------------------------------------------------------------")
        print("LOGIN VERIFICATION:")
        print("1. Look at the automated browser window that just popped up.")
        print("2. If you are logged in and see your inbox, you are good to go!")
        print("3. If not, log in right now.")
        print("ONCE LOGGED IN, PRESS [ENTER] IN THIS TERMINAL TO LOCK IT IN.")
        print("-------------------------------------------------------------\n")
        
        input("Press Enter here once your Facebook Inbox is fully loaded...")
        print("Session saved successfully! Closing browser until scheduled time...")
        # Write the flag file to match the backend login status indicator
        flag_path = os.path.join(session_dir, "logged_in.flag")
        try:
            with open(flag_path, "w") as f:
                f.write("true")
        except Exception as e:
            print(f"Warning: Could not create flag file: {e}")
        browser.close()

def main_agent(user_command: str):
    print(f"\nWeb request received instruction: {user_command}")
    json_raw = extract_schedule_details(user_command)
    
    if json_raw.startswith("Error:"):
        print(f"Error in extract_schedule_details: {json_raw}")
        return {
            "status": "error",
            "message": json_raw,
            "clarification": ""
        }
    
    try:
        data = parse_json_response(json_raw)
        friend = data.get('recipient')
        ai_message = data.get('message')
        target_time = data.get('execution_time')
        fetch_gitlab_issues = data.get('fetch_gitlab_issues', False) # Track our new fetch flag
        
        if not friend or target_time is None:
            return {
                "status": "clarification_needed",
                "message": "Missing information",
                "clarification": f"I couldn't extract all details. Raw response: {json_raw}"
            }
            
        # THE DATA RETRIEVAL INTERCEPT
        if fetch_gitlab_issues:
            print(f"\n[GitLab Fetch Active]: Contacting remote API to collect project issues...")
            from text_function import fetch_raw_gitlab_issues, generate_ai_summary
            
            # 1. Fetch real, live items from your GitLab profile
            raw_issues = fetch_raw_gitlab_issues()
            
            # 2. Hand them to Gemini to write a perfect executive briefing message
            print("[Gemini Sync]: Synthesizing raw issues into a text update message...")
            ai_message = generate_ai_summary(raw_issues)
        
        print("\nExtraction Successful:")
        print(f"Target Friend : {friend}")
        print(f"AI Message    : {ai_message}")
        print(f"Execution Time: {target_time}")
        print("-------------------------------------------------")
        
        bg_scheduler.add_job(
            run_browser_agent, 
            'date', 
            run_date=target_time, 
            args=[friend, ai_message]
        )
        
        if fetch_gitlab_issues:
            ui_confirmation = f"Successfully pulled your GitLab status briefing and scheduled it for delivery to {friend}: '{ai_message}'"
        else:
            ui_confirmation = f"Scheduled message for {friend} at {target_time}: '{ai_message}'"
        
        return {
            "status": "sent",
            "message": ui_confirmation, 
            "clarification": ""
        }
        
    except Exception as e:
        print(f"Error in main_agent: {e}")
        return {
            "status": "error",
            "message": f"Error: {e}. Raw response: {json_raw}",
            "clarification": ""
        }

def deploy_agent():
    print("=================================================")
    print("        WELCOME TO THE AI MESSAGE AGENT        ")
    print("=================================================")
    
    user_command = input("\nWhat would you like the agent to do? \n")
    
    print("\nAI Brain analyzing your command...")
    json_raw = extract_schedule_details(user_command)
    
    if json_raw.startswith("Error:"):
        print(f"\nFailed. Gemini returned an error: {json_raw}")
        return
    
    try:
        data = parse_json_response(json_raw)
        friend = data['recipient']
        ai_message = data['message']
        target_time = data['execution_time']
        
        print("\nExtraction Successful:")
        print(f"Target Friend : {friend}")
        print(f"AI Message    : {ai_message}")
        print(f"Execution Time: {target_time}")
        print("-------------------------------------------------")
        
        # Run the login check RIGHT NOW before sleeping
        verify_login_session()
        
        scheduler = BlockingScheduler(timezone=str(get_localzone()))
        
        scheduler.add_job(
            run_browser_agent, 
            'date', 
            run_date=target_time, 
            args=[friend, ai_message]
        )
        
        # Add event listener to shut down the blocking scheduler upon job completion or error
        def shutdown_listener(event):
            print("\nScheduled job finished. Shutting down the agent...")
            scheduler.shutdown(wait=False)
            
        scheduler.add_listener(shutdown_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
        
        print(f"\nWill deploy browser to message {friend} at exactly {target_time}...")
        scheduler.start()
        
    except Exception as e:
        print(f"\nFailed. Raw AI response was:\n{json_raw}\nError: {e}")

if __name__ == "__main__":
    deploy_agent()