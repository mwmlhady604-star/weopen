from fastapi import FastAPI, Request, Response, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI, InvalidWebhookSignatureError
import asyncio
import json
import os
import requests
import time
import websockets

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define a model for the instructions
class Instructions(BaseModel):
    instructions: str

# Global variable to store dynamic instructions (initially empty)
DYNAMIC_INSTRUCTIONS = ""

client = OpenAI(
    webhook_secret=os.environ["OPENAI_WEBHOOK_SECRET"]
)

AUTH_HEADER = {
    "Authorization": "Bearer " + os.getenv("OPENAI_API_KEY")
}

call_accept = {
    "type": "realtime",
    "instructions": DYNAMIC_INSTRUCTIONS,
    "model": "gpt-realtime",
}

response_create = {
    "type": "response.create",
    "response": {
        "instructions": DYNAMIC_INSTRUCTIONS
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


@app.post("/set_instructions")
async def set_instructions(instructions: Instructions):
    global DYNAMIC_INSTRUCTIONS, call_accept, response_create
    
    # Update the global instructions variable
    DYNAMIC_INSTRUCTIONS = instructions.instructions
    
    # Update the instructions in both dictionaries
    call_accept["instructions"] = DYNAMIC_INSTRUCTIONS
    response_create["response"]["instructions"] = DYNAMIC_INSTRUCTIONS
    
    return {"message": "Instructions updated successfully"}

@app.get("/instructions")
async def get_instructions():
    return {"instructions": DYNAMIC_INSTRUCTIONS}

# Serve the HTML file
@app.get("/")
async def serve_frontend():
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    html_file = os.path.join(current_dir, "index.html")
    
    if os.path.exists(html_file):
        with open(html_file, "r", encoding="utf-8") as file:
            content = file.read()
        return Response(content=content, media_type="text/html")
    else:
        return Response(content="Frontend file not found", status_code=404)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
