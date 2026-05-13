from fastapi import FastAPI
import requests
import os
import asyncio
from contextlib import asynccontextmanager

# .strip('"').strip("'").strip() automatically removes any accidental quotes or spaces!
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
    print(f"Evolution URL: {EVO_API_URL}")
    # Print the first 4 characters of the key to verify it loaded without quotes
    print(f"API Key Starts With: {EVO_API_KEY[:4]}...") 
    print("-------------------------------\n")
    
    await asyncio.sleep(2)

    while True:
        try:
            url = f"{EVO_API_URL}/chat/findMessages/{INSTANCE_NAME}"
            
            # Sending the key in BOTH formats to guarantee V2 compatibility
            headers = {
                "apikey": EVO_API_KEY, 
                "Authorization": f"Bearer {EVO_API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "where": {"remoteJid": WHATSAPP_CHANNEL_JID},
                "count": 5
            }
            
            print("Fetching messages from database...")
            response = requests.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                messages = data.get("messages", [])
                
                if not messages:
                    print(f"Result: SUCCESS, but Database returned 0 messages for {WHATSAPP_CHANNEL_JID}.")
                else:
                    latest_message = messages[-1]
                    message_id = latest_message.get("key", {}).get("id")
                    
                    if message_id != last_processed_message_id:
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
    task = asyncio.create_task(poll_whatsapp_channel())
    yield
    task.cancel()

app = FastAPI(lifespan=lifespan)

@app.get("/")
def read_root():
    return {"status": "Polling script is active!"}