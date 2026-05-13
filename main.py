from fastapi import FastAPI
import requests
import os
import asyncio

app = FastAPI()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
WHATSAPP_CHANNEL_JID = os.getenv("WHATSAPP_CHANNEL_JID")
EVO_API_URL = os.getenv("EVO_API_URL")
EVO_API_KEY = os.getenv("EVO_API_KEY")
INSTANCE_NAME = os.getenv("INSTANCE_NAME", "Wapp")

# We will store the ID of the last message we forwarded so we don't spam Telegram
last_processed_message_id = None

@app.get("/")
def read_root():
    return {"status": "Polling script is running in the background!"}

async def poll_whatsapp_channel():
    global last_processed_message_id
    await asyncio.sleep(5)
    print(f"Polling started for JID: {WHATSAPP_CHANNEL_JID}")

    while True:
        try:
            url = f"{EVO_API_URL}/chat/findMessages/{INSTANCE_NAME}"
            headers = {"apikey": EVO_API_KEY, "Content-Type": "application/json"}
            # We add a 'count' to ensure we get the latest 5 messages
            payload = {
                "where": {"remoteJid": WHATSAPP_CHANNEL_JID},
                "count": 5
            }
            
            response = requests.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                # DEBUG: This will show us exactly what the API is seeing
                # print(f"Raw API Data: {data}") 

                messages = data.get("messages", [])
                if messages:
                    latest_message = messages[-1]
                    message_id = latest_message.get("key", {}).get("id")
                    
                    if message_id != last_processed_message_id:
                        msg_content = latest_message.get("message", {})
                        text = msg_content.get("conversation") or \
                               msg_content.get("extendedTextMessage", {}).get("text") or \
                               msg_content.get("newsletterText") # Some versions use this for channels
                        
                        if text:
                            print(f"Match Found! Sending to Telegram: {text[:20]}...")
                            send_to_telegram(text)
                            last_processed_message_id = message_id
                else:
                    # If you see this in logs, it means the JID is wrong or the DB is empty
                    print(f"No messages found in Evolution DB for JID: {WHATSAPP_CHANNEL_JID}")
            else:
                print(f"API Error {response.status_code}: {response.text}")

        except Exception as e:
            print(f"Polling error: {str(e)}")
            
        await asyncio.sleep(10)

def send_to_telegram(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    response = requests.post(url, json={"chat_id": TELEGRAM_CHANNEL_ID, "text": text})
    if response.status_code == 200:
        print("Successfully forwarded to Telegram!")

# Start the background loop when the FastAPI server starts
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(poll_whatsapp_channel())