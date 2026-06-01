import json
import time
import os
import sys
from datetime import datetime

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

# Initialize background scheduler for web app requests
bg_scheduler = BackgroundScheduler()
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
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir="./sessions/facebook",
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
        browser.close()

def main_agent(user_command: str):
    print(f"\nWeb request received instruction: {user_command}")
    json_raw = extract_schedule_details(user_command)
    
    try:
        data = parse_json_response(json_raw)
        friend = data.get('recipient')
        ai_message = data.get('message')
        target_time = data.get('execution_time')
        
        if not friend or not ai_message or not target_time:
            return {
                "status": "clarification_needed",
                "message": "Missing information",
                "clarification": f"I couldn't extract all details. Raw response: {json_raw}"
            }
            
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
        
        return {
            "status": "sent",
            "message": f"Scheduled message for {friend} at {target_time}: '{ai_message}'",
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
        
        scheduler = BlockingScheduler()
        
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