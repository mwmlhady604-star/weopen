import os
import json
import asyncio
import threading
import requests
import websockets
from flask import Flask, request, Response
from openai import OpenAI, InvalidWebhookSignatureError

# ====================================
# إعداد Flask Webhook
# ====================================
app = Flask(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_WEBHOOK_SECRET = os.getenv("OPENAI_WEBHOOK_SECRET")

# التحقق من المفاتيح
if not OPENAI_API_KEY or not OPENAI_WEBHOOK_SECRET:
    raise ValueError("❌ يرجى ضبط OPENAI_API_KEY و OPENAI_WEBHOOK_SECRET في البيئة")

client = OpenAI(webhook_secret=OPENAI_WEBHOOK_SECRET)

AUTH_HEADER = {
    "Authorization": f"Bearer {OPENAI_API_KEY}"
}

# إعدادات القبول
CALL_ACCEPT_CONFIG = {
    "type": "realtime",
    "model": "gpt-4o-realtime-preview-2024-12-17",
    "voice": "verse",  # alloy / verse / coral
    "instructions": (
        "أنت وكيل صوتي عراقي ودود. ابدأ المكالمة بعبارة 'هلا بيك، شلونك؟ شنو تحتاج اليوم؟' "
        "تحدث باللهجة العراقية بأسلوب طبيعي وسريع الرد."
    ),
}

# أول رد بعد قبول المكالمة
INITIAL_RESPONSE = {
    "type": "response.create",
    "response": {
        "instructions": (
            "هلا بيك! شلونك؟ شنو تحتاج اليوم؟ أنا هنا أساعدك بكل شي تريده."
        )
    },
}

# ====================================
# التعامل مع WebSocket بعد قبول المكالمة
# ====================================
async def handle_realtime_session(call_id: str):
    try:
        async with websockets.connect(
            f"wss://api.openai.com/v1/realtime?call_id={call_id}",
            additional_headers=AUTH_HEADER,
        ) as ws:
            await ws.send(json.dumps(INITIAL_RESPONSE))
            print(f"✅ بدأ الرد الصوتي على المكالمة {call_id}")

            while True:
                msg = await ws.recv()
                print(f"🎧 WebSocket: {msg}")

    except Exception as e:
        print(f"⚠️ خطأ في WebSocket: {e}")


# ====================================
# استقبال Webhook من OpenAI
# ====================================
@app.route("/", methods=["POST"])
def webhook_handler():
    try:
        event = client.webhooks.unwrap(request.data, request.headers)

        if event.type == "realtime.call.incoming":
            call_id = event.data.call_id
            print(f"📞 مكالمة جديدة واردة: {call_id}")

            # قبول المكالمة
            resp = requests.post(
                f"https://api.openai.com/v1/realtime/calls/{call_id}/accept",
                headers={**AUTH_HEADER, "Content-Type": "application/json"},
                json=CALL_ACCEPT_CONFIG,
            )
            print(f"☎️ تم قبول المكالمة: {resp.status_code} - {resp.text}")

            # التحقق من نجاح القبول
            if resp.status_code == 200:
                print("✅ OpenAI accepted the call.")
                # تشغيل WebSocket في thread منفصل
                threading.Thread(
                    target=lambda: asyncio.run(handle_realtime_session(call_id)),
                    daemon=True,
                ).start()
            else:
                print(f"❌ OpenAI rejected the call: {resp.text}")

            return Response(status=200)

        else:
            print(f"⚙️ حدث آخر تم تجاهله: {event.type}")
            return Response(status=200)

    except InvalidWebhookSignatureError:
        print("❌ توقيع Webhook غير صالح")
        return Response("Invalid signature", status=400)
    except Exception as e:
        print(f"⚠️ خطأ أثناء معالجة Webhook: {e}")
        return Response(status=500)


# ====================================
# نقطة البداية
# ====================================
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"🚀 Running on port {port}")
    app.run(host="0.0.0.0", port=port)
