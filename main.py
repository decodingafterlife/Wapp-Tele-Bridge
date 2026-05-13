from fastapi import FastAPI
import requests
import os
import asyncio
import traceback
from contextlib import asynccontextmanager

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip('"').strip("'").strip()
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "").strip('"').strip("'").strip()
WHATSAPP_CHANNEL_JID = os.getenv("WHATSAPP_CHANNEL_JID", "").strip('"').strip("'").strip()
EVO_API_URL = os.getenv("EVO_API_URL", "").strip('"').strip("'").strip()
EVO_API_KEY = os.getenv("EVO_API_KEY", "").strip('"').strip("'").strip()
INSTANCE_NAME = os.getenv("INSTANCE_NAME", "Wapp").strip('"').strip("'").strip()

last_processed_message_id = None

async def poll_whatsapp_channel():
    global last_processed_message_id
    print("\n--- POLLING ENGINE STARTING ---")
    print(f"Target JID: {WHATSAPP_CHANNEL_JID}")
    print("-------------------------------\n")
    
    await asyncio.sleep(2)

    while True:
        try:
            url = f"{EVO_API_URL}/chat/findMessages/{INSTANCE_NAME}"
            headers = {
                "apikey": EVO_API_KEY, 
                "Authorization": f"Bearer {EVO_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "where": {"remoteJid": WHATSAPP_CHANNEL_JID},
                "count": 5
            }
            
            response = requests.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                # --- NEW SAFEPARSE LOGIC ---
                messages = []
                
                # 1. If Evolution returned a direct list
                if isinstance(data, list):
                    messages = data
                # 2. If Evolution returned a dictionary
                elif isinstance(data, dict):
                    messages = data.get("messages") or data.get("data") or data.get("records") or []
                    # If the messages themselves are inside a dict instead of a list
                    if isinstance(messages, dict):
                        messages = list(messages.values())

                if not messages:
                    # Print the first 300 characters of the raw response so we can see it
                    print(f"No messages parsed. RAW DB Response: {str(data)[:300]}")
                else:
                    # Safely grab the most recent message
                    latest_message = messages[-1]
                    message_id = latest_message.get("key", {}).get("id")
                    
                    if message_id and message_id != last_processed_message_id:
                        print(f"New Message ID detected: {message_id}")
                        
                        msg_content = latest_message.get("message", {})
                        
                        text = msg_content.get("conversation") or \
                               msg_content.get("extendedTextMessage", {}).get("text") or \
                               msg_content.get("newsletterText") or \
                               msg_content.get("imageMessage", {}).get("caption") or \
                               msg_content.get("videoMessage", {}).get("caption")
                        
                        if text:
                            print(f"Extracted Text: {text[:30]}...")
                            send_to_telegram(text)
                            last_processed_message_id = message_id
                        else:
                            print(f"Received message, but no text found. RAW: {str(latest_message)[:200]}")
            else:
                print(f"API Request Failed ({response.status_code}): {response.text}")

        except Exception as e:
            print(f"CRITICAL ERROR in loop: {str(e)}")
            print(traceback.format_exc()) # This prints the exact line of the error!
            
        await asyncio.sleep(10)

def send_to_telegram(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID:
        print("Error: Missing Telegram credentials!")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    response = requests.post(url, json={"chat_id": TELEGRAM_CHANNEL_ID, "text": text})
    if response.status_code == 200:
        print("SUCCESS -> Sent to Telegram")
    else:
        print(f"TELEGRAM ERROR: {response.text}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(poll_whatsapp_channel())
    yield
    task.cancel()

app = FastAPI(lifespan=lifespan)

@app.get("/")
def read_root():
    return {"status": "Polling script is active!"}