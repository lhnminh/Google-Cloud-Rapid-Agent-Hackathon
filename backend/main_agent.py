import json
import time
from datetime import datetime
from text_function import extract_schedule_details
from browser_agent import run_browser_agent
from playwright.sync_api import sync_playwright
from apscheduler.schedulers.blocking import BlockingScheduler

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

def deploy_agent():
    print("=================================================")
    print("        WELCOME TO THE AI MESSAGE AGENT        ")
    print("=================================================")
    
    user_command = input("\nWhat would you like the agent to do? \n")
    
    print("\nAI Brain analyzing your command...")
    json_raw = extract_schedule_details(user_command)
    
    try:
        data = json.loads(json_raw)
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
        
        print(f"\nWill deploy browser to message {friend} at exactly {target_time}...")
        scheduler.start()
        
    except Exception as e:
        print(f"\nFailed. Raw AI response was:\n{json_raw}\nError: {e}")

if __name__ == "__main__":
    deploy_agent()