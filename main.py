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
    
    # Give the server a few seconds to boot up before starting the loop
    await asyncio.sleep(5)
    print("Started polling WhatsApp Channel...")

    while True:
        try:
            # Ask Evolution API for the messages from this specific JID
            url = f"{EVO_API_URL}/chat/findMessages/{INSTANCE_NAME}"
            headers = {"apikey": EVO_API_KEY, "Content-Type": "application/json"}
            payload = {"where": {"remoteJid": WHATSAPP_CHANNEL_JID}}
            
            response = requests.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if we got messages back (Evolution returns a list of message objects)
                if data and "messages" in data and len(data["messages"]) > 0:
                    
                    # Sort or get the most recent message (Evolution usually returns latest last)
                    messages = data["messages"]
                    latest_message = messages[-1] # Grabbing the last one in the array
                    
                    message_id = latest_message.get("key", {}).get("id")
                    
                    # If this is a brand new message we haven't seen yet
                    if message_id and message_id != last_processed_message_id:
                        
                        # Extract the text
                        msg_content = latest_message.get("message", {})
                        text = msg_content.get("conversation") or msg_content.get("extendedTextMessage", {}).get("text")
                        
                        if text:
                            print(f"New Channel Message Found: {text}")
                            send_to_telegram(text)
                        
                        # Update our tracker so we don't send it again
                        last_processed_message_id = message_id

        except Exception as e:
            print(f"Polling error: {str(e)}")
            
        # Wait 10 seconds before checking again (adjust this depending on how fast you want it)
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