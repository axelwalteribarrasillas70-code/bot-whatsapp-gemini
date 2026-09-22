import os

import requests
from fastapi import FastAPI, Request, Response
from google import genai

app = FastAPI()
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")


@app.get("/webhook")
async def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return Response(content=challenge or "", media_type="text/plain")

    return Response(status_code=403)


@app.post("/webhook")
async def receive_message(request: Request):
    body = await request.json()

    try:
        entry = body.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])

        if messages:
            message = messages[0]
            from_number = message.get("from")
            message_body = message.get("text", {}).get("body")

            if from_number and message_body:
                ai_response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=message_body,
                )
                response_text = ai_response.text or "No pude generar una respuesta."
                send_whatsapp_message(from_number, response_text)
    except Exception as error:
        print(f"Error procesando el webhook: {error}")

    return {"status": "ok"}


def send_whatsapp_message(to: str, message: str):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message},
    }
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }

    response = requests.post(url, json=payload, headers=headers, timeout=30)
    response.raise_for_status()
