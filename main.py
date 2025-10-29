from flask import Flask, request, Response
from openai import OpenAI, InvalidWebhookSignatureError
import asyncio, json, os, requests, threading, websockets

app = Flask(__name__)
client = OpenAI(webhook_secret=os.environ["OPENAI_WEBHOOK_SECRET"])

AUTH_HEADER = {"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"}

call_accept = {
    "type": "realtime",
    "model": "gpt-4o-realtime-preview-2024-12-17",
    "voice": "verse",
    "instructions": (
        "أنت وكيل صوتي عراقي ودود. "
        "ابدأ المكالمة بعبارة: 'هلا بيك، شلونك؟ شنو تحتاج اليوم؟'"
    ),
}

response_create = {
    "type": "response.create",
    "response": {
        "instructions": "هلا بيك! شلونك؟ شنو تحتاج اليوم؟"
    },
}

async def websocket_task(call_id):
    try:
        async with websockets.connect(
            f"wss://api.openai.com/v1/realtime?call_id={call_id}",
            additional_headers=AUTH_HEADER,
        ) as ws:
            print(f"✅ WebSocket opened for {call_id}")
            await ws.send(json.dumps(response_create))
            while True:
                msg = await ws.recv()
                print(f"🎧 {msg}")
    except Exception as e:
        print(f"⚠️ WebSocket error: {e}")

@app.route("/", methods=["POST"])
def webhook():
    try:
        event = client.webhooks.unwrap(request.data, request.headers)
        if event.type == "realtime.call.incoming":
            call_id = event.data.call_id
            print(f"📞 Incoming call: {call_id}")

            resp = requests.post(
                f"https://api.openai.com/v1/realtime/calls/{call_id}/accept",
                headers={**AUTH_HEADER, "Content-Type": "application/json"},
                json=call_accept,
            )
            print(f"☎️ Accept response: {resp.status_code} - {resp.text}")

            if resp.status_code == 200:
                threading.Thread(
                    target=lambda: asyncio.run(websocket_task(call_id)),
                    daemon=True,
                ).start()
            else:
                print("❌ Failed to accept call.")

            return Response(status=200)
        return Response(status=200)

    except InvalidWebhookSignatureError:
        print("❌ Invalid signature")
        return Response("Invalid signature", status=400)
    except Exception as e:
        print(f"⚠️ Error: {e}")
        return Response(status=500)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    print(f"🚀 Running on port {port}")
    app.run(host="0.0.0.0", port=port)
