from fastapi import FastAPI, Request, Response, BackgroundTasks, HTTPException
from openai import OpenAI, InvalidWebhookSignatureError
import asyncio
import json
import os
import requests
import time
import websockets

app = FastAPI()
client = OpenAI(
    webhook_secret=os.environ["OPENAI_WEBHOOK_SECRET"]
)

AUTH_HEADER = {
    "Authorization": "Bearer " + os.getenv("OPENAI_API_KEY")
}

call_accept = {
    "type": "realtime",
    "instructions": "انت موظف خدمة عملاء في منصة ادم للخدمات الكوول سنتر المدعوم بالذكاء الصناعي.",
    "model": "gpt-realtime",
}

response_create = {
    "type": "response.create",
    "response": {
        "instructions": (
             "أنت وكيل صوتي عراقي تمثّل منصة آدم للاتصالات الذكية (Adam Smart Communications). "
        "شخصيتك ودودة، احترافية، ومساعدة. "
        "تتحدث باللهجة العراقية القريبة من الناس، لكن تحافظ على أسلوب مهذب وواضح. "
        "ابدأ المكالمة بترحيب عراقي دافئ مثل: 'هلا بيك، نورت اتصالك بشركة آدم للاتصالات الذكية، شلونك اليوم؟' "
        "بعدها استمع للمتصل وساعده بأفضل شكل ممكن حسب سياق حديثه. "
        "إذا ما فهمت سؤاله، وضّح له بلطف واطلب منه يعيد بصيغة ثانية."
        )
    },
}


async def websocket_task(call_id):
    try:
        async with websockets.connect(
            "wss://api.openai.com/v1/realtime?call_id=" + call_id,
            additional_headers=AUTH_HEADER,
        ) as websocket:
            await websocket.send(json.dumps(response_create))

            while True:
                response = await websocket.recv()
                print(f"Received from WebSocket: {response}")
    except Exception as e:
        print(f"WebSocket error: {e}")


@app.post("/")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        body = await request.body()
        headers = dict(request.headers)
        
        event = client.webhooks.unwrap(body, headers)

        if event.type == "realtime.call.incoming":
            requests.post(
                "https://api.openai.com/v1/realtime/calls/"
                + event.data.call_id
                + "/accept",
                headers={**AUTH_HEADER, "Content-Type": "application/json"},
                json=call_accept,
            )
            background_tasks.add_task(
                lambda: asyncio.run(websocket_task(event.data.call_id))
            )
            return Response(content="", status_code=200)
    except InvalidWebhookSignatureError as e:
        print("Invalid signature", e)
        raise HTTPException(status_code=400, detail="Invalid signature")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
