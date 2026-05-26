import httpx
import streamlit as st

BACKEND_URL = "http://localhost:8000"

st.title("Message Agent")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hi! Who should I message and what should I say?"}
    ]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

instruction = st.chat_input("Tell me who to message and what to say…")

if instruction:
    st.session_state.messages.append({"role": "user", "content": instruction})
    with st.chat_message("user"):
        st.write(instruction)

    with st.chat_message("assistant"):
        with st.spinner("Sending via Messenger…"):
            try:
                response = httpx.post(
                    f"{BACKEND_URL}/send-message",
                    json={"instruction": instruction},
                    timeout=120.0,
                )
                data = response.json()
            except Exception as e:
                data = {"status": "failed", "message": str(e), "clarification": ""}

        if data.get("status") == "sent":
            #Look into this whenever status is sent again. This is still a test
            reply = f"Done! {data['message']}"
        elif data.get("status") == "clarification_needed":
            reply = data["clarification"]
        else:
            reply = f"Something went wrong: {data.get('message', 'Unknown error')}"

        st.write(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})
