from fastapi import FastAPI, Request
import requests
import os

app = FastAPI()

# Fetching variables from Easypanel's Environment tab
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
WHATSAPP_CHANNEL_JID = os.getenv("WHATSAPP_CHANNEL_JID")

@app.post("/webhook")
async def receive_webhook(request: Request):
    payload = await request.json()
    
    # 1. Print the payload to your console first to see the exact structure
    # print(payload) 

    # 2. Filter for new messages only
    if payload.get("event") != "messages.upsert":
        return {"status": "ignored"}

    data = payload.get("data", {})
    key = data.get("key", {})
    message = data.get("message", {})
    
    remote_jid = key.get("remoteJid", "")

    # 3. Check if the message is from your target WhatsApp Channel
    if remote_jid == WHATSAPP_CHANNEL_JID:
        
        # Extract the text (the JSON path varies slightly between standard text and media captions)
        text = message.get("conversation") or message.get("extendedTextMessage", {}).get("text")
        
        if text:
            send_to_telegram(text)

    return {"status": "success"}

def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHANNEL_ID,
        "text": text
    }
    response = requests.post(url, json=payload)
    if response.status_code != 200:
        print(f"Failed to send to Telegram: {response.text}")