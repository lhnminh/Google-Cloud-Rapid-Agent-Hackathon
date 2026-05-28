from browser.launch import launch_browser
from browser.messenger import send_message

browser, page = launch_browser()

send_message(
    page,
    "Your Name",
    "hello world"
)