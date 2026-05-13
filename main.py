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
            # Increased count to 20 to ensure we don't miss channel messages in a busy global feed
            payload = {
                "remoteJid": WHATSAPP_CHANNEL_JID,
                "where": {"remoteJid": WHATSAPP_CHANNEL_JID},
                "count": 20 
            }
            
            response = requests.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                messages = []
                if isinstance(data, list):
                    messages = data
                elif isinstance(data, dict):
                    messages = data.get("messages") or data.get("data") or data.get("records") or []
                    if isinstance(messages, dict):
                        messages = list(messages.values())

                if not messages:
                    pass # Quietly wait
                else:
                    # --- STRICT PYTHON-SIDE FILTERING ---
                    channel_msgs = []
                    for m in messages:
                        # Unwrap lists if necessary
                        if isinstance(m, list) and len(m) > 0:
                            m = m[-1]
                        
                        if isinstance(m, dict):
                            # Check if this specific message is from our Channel
                            jid = m.get("key", {}).get("remoteJid", "")
                            if jid == WHATSAPP_CHANNEL_JID:
                                channel_msgs.append(m)
                    
                    if not channel_msgs:
                        # Feed had messages, but none were from our target channel
                        pass 
                    else:
                        # Grab the most recent message THAT BELONGS TO OUR CHANNEL
                        latest_message = channel_msgs[-1]
                        message_id = latest_message.get("key", {}).get("id")
                        
                        if message_id and message_id != last_processed_message_id:
                            print(f"New CHANNEL Message ID: {message_id}")
                            
                            # The 'or {}' fixes the NoneType error on system messages
                            msg_content = latest_message.get("message") or {}
                            
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
                                print(f"Message received, but no text found (System Message/Sticker).")
            else:
                print(f"API Request Failed ({response.status_code}): {response.text}")

        except Exception as e:
            print(f"CRITICAL ERROR in loop: {str(e)}")
            print(traceback.format_exc())
            
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