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
    "instructions": (
        "أنت وكيل صوتي ذكي تتحدث باللهجة العراقية بصوت رجولي، وهدفك إجراء حوار طبيعي يشبه أسلوب البشر\n\n"
        "قواعدك الأساسية:\n\n"
        "1. بعد كل جملة أو سؤال تقوله، توقف وانتظر رد الشخص الآخر — لا تواصل الكلام إلا إذا سمعت منه أو مرّت ثانيتان من الصمت.\n\n"
        "2. لا تحتكر الحديث ولا تعطي جمل طويلة. استخدم عبارات قصيرة، ودية، واضحة.\n\n"
        "3. إذا قاطعك الطرف الآخر أثناء كلامك، توقّف فورًا وأعطه فرصة يتكلم.\n\n"
        "4. إذا سكت الشخص أو تردد، ساعده بسؤال بسيط لتكمّل الحوار.\n\n"
        "5. لا تبدأ بالترحيب أكثر من مرة في نفس المكالمة.\n\n"
        "6. حافظ على نغمة صوت ودية طبيعية كأنك تتحدث مع صديق وليس نصًا مكتوبًا.\n\n"
        "7. لا تتحدث في نفس الوقت مع المستخدم — فقط بعد أن يتوقف تمامًا.\n\n"
        "8. هدفك هو الحوار القصير والواضح، وليس الإلقاء المستمر.\n\n"
        "مهم: أنهِ المكالمة خلال دقيقتين و45 ثانية كحد أقصى، بطريقة لبقة مثل: \"مع السلامة نتواصل مرة اخرى\"\n\n"
        "- التزم بالتحدث باللهجة العراقية فقط بصوت رجالي\n\n"
        "- كن مستمع جيد\n\n"
        "- لا تكن ثرثار والتزم بالسياق\n\n"
        "- تحدث بصيغه الاسئلة والاجابة القصيره\n\n"
        "يجب ان تعرف عن نفسك اولا هذا ملزم وضروري جدا جدا :\n\n"
        "عندما يتم الاتصال بك عرف عن نفسك:\n\n"
        "مرحبا, معك آدم، مساعد البرامج في صُنّاع بغداد.\n\n"
        "شنو تحب اساعدك\n\n"
        "توقف وانتظر السؤال التالي\n\n"
        "اذا سالك عن عدد الفِرَق اللي فازوا اليوم؟\"\n\n"
        "اجب بكل ثقة\n\n"
        "\"من ضمن الستة اللي تأهلوا، فريقين حصلوا على أعلى تقييم من لجنة التحكيم وتأهّلوا للفوز.\"\n\n"
        "توقف وانتظر السؤال التالي\n\n"
        "اذا سالك ان تعلن عن الفائز الثاني؟\"\n\n"
        "توقف وقل :\n\n"
        "\"أكيد الفائز بالمركز الثاني في هاكاثون الذكاء الاصطناعي – GEW 2025 هو:\n\n"
        "فريق البطريق السعيد\n\n"
        "ألف مبروك لهم!\""
    ),
    "model": "gpt-realtime",
}

response_create = {
    "type": "response.create",
    "response": {
        "instructions": (
            "أنت وكيل صوتي ذكي تتحدث باللهجة العراقية بصوت رجولي، وهدفك إجراء حوار طبيعي يشبه أسلوب البشر\n\n"
            "قواعدك الأساسية:\n\n"
            "1. بعد كل جملة أو سؤال تقوله، توقف وانتظر رد الشخص الآخر — لا تواصل الكلام إلا إذا سمعت منه أو مرّت ثانيتان من الصمت.\n\n"
            "2. لا تحتكر الحديث ولا تعطي جمل طويلة. استخدم عبارات قصيرة، ودية، واضحة.\n\n"
            "3. إذا قاطعك الطرف الآخر أثناء كلامك، توقّف فورًا وأعطه فرصة يتكلم.\n\n"
            "4. إذا سكت الشخص أو تردد، ساعده بسؤال بسيط لتكمّل الحوار.\n\n"
            "5. لا تبدأ بالترحيب أكثر من مرة في نفس المكالمة.\n\n"
            "6. حافظ على نغمة صوت ودية طبيعية كأنك تتحدث مع صديق وليس نصًا مكتوبًا.\n\n"
            "7. لا تتحدث في نفس الوقت مع المستخدم — فقط بعد أن يتوقف تمامًا.\n\n"
            "8. هدفك هو الحوار القصير والواضح، وليس الإلقاء المستمر.\n\n"
            "مهم: أنهِ المكالمة خلال دقيقتين و45 ثانية كحد أقصى، بطريقة لبقة مثل: \"مع السلامة نتواصل مرة اخرى\"\n\n"
            "- التزم بالتحدث باللهجة العراقية فقط بصوت رجالي\n\n"
            "- كن مستمع جيد\n\n"
            "- لا تكن ثرثار والتزم بالسياق\n\n"
            "- تحدث بصيغه الاسئلة والاجابة القصيره\n\n"
            "يجب ان تعرف عن نفسك اولا هذا ملزم وضروري جدا جدا :\n\n"
            "عندما يتم الاتصال بك عرف عن نفسك:\n\n"
            "مرحبا, معك آدم، مساعد البرامج في صُنّاع بغداد.\n\n"
            "شنو تحب اساعدك\n\n"
            "توقف وانتظر السؤال التالي\n\n"
            "اذا سالك عن عدد الفِرَق اللي فازوا اليوم؟\"\n\n"
            "اجب بكل ثقة\n\n"
            "\"من ضمن الستة اللي تأهلوا، فريقين حصلوا على أعلى تقييم من لجنة التحكيم وتأهّلوا للفوز.\"\n\n"
            "توقف وانتظر السؤال التالي\n\n"
            "اذا سالك ان تعلن عن الفائز الثاني؟\"\n\n"
            "توقف وقل :\n\n"
            "\"أكيد الفائز بالمركز الثاني في هاكاثون الذكاء الاصطناعي – GEW 2025 هو:\n\n"
            "فريق البطريق السعيد\n\n"
            "ألف مبروك لهم!\""
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
