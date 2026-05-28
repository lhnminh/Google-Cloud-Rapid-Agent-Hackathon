def send_message(page, friend_name, message):

    page.goto("https://www.facebook.com/messages")

    page.wait_for_timeout(5000)

    search_box = page.locator(
        'input[placeholder="Search Messenger"]'
    )

    search_box.fill(friend_name)

    page.wait_for_timeout(2000)

    page.keyboard.press("Enter")

    page.wait_for_timeout(3000)

    message_box = page.locator(
        '[contenteditable="true"]'
    ).last

    message_box.fill(message)

    page.keyboard.press("Enter")