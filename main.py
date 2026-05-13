from fastapi import FastAPI
import requests
import os
import asyncio
from contextlib import asynccontextmanager

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
WHATSAPP_CHANNEL_JID = os.getenv("WHATSAPP_CHANNEL_JID")
EVO_API_URL = os.getenv("EVO_API_URL")
EVO_API_KEY = os.getenv("EVO_API_KEY")
INSTANCE_NAME = os.getenv("INSTANCE_NAME", "Wapp")

last_processed_message_id = None

async def poll_whatsapp_channel():
    global last_processed_message_id
    print("\n--- POLLING ENGINE STARTING ---")
    print(f"Target JID: {WHATSAPP_CHANNEL_JID}")
    print(f"Evolution URL: {EVO_API_URL}")
    print("-------------------------------\n")
    
    await asyncio.sleep(2)

    while True:
        try:
            url = f"{EVO_API_URL}/chat/findMessages/{INSTANCE_NAME}"
            headers = {"apikey": EVO_API_KEY, "Content-Type": "application/json"}
            payload = {
                "where": {"remoteJid": WHATSAPP_CHANNEL_JID},
                "count": 5
            }
            
            # Print right before the API call to prove the loop is running
            print("Fetching messages from database...")
            response = requests.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                # UNCOMMENT THIS LINE if you want to see the massive raw JSON dump
                # print(f"Raw API Data: {data}")

                messages = data.get("messages", [])
                
                if not messages:
                    print(f"Result: SUCCESS, but Database returned 0 messages for {WHATSAPP_CHANNEL_JID}.")
                else:
                    latest_message = messages[-1]
                    message_id = latest_message.get("key", {}).get("id")
                    
                    if message_id != last_processed_message_id:
                        print(f"New Message ID detected: {message_id}")
                        
                        msg_content = latest_message.get("message", {})
                        
                        # Handle standard texts, captions, and explicit newsletter text
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
                            print("Message received, but no text could be extracted.")
                    else:
                        print("No new messages.")
            else:
                print(f"API Request Failed ({response.status_code}): {response.text}")

        except Exception as e:
            print(f"CRITICAL ERROR in loop: {str(e)}")
            
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
    # This ensures the polling loop starts the moment the server boots up
    task = asyncio.create_task(poll_whatsapp_channel())
    yield
    task.cancel()

app = FastAPI(lifespan=lifespan)

@app.get("/")
def read_root():
    return {"status": "Polling script is active!"}