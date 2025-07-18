from fastapi import FastAPI, Request, HTTPException
from discord_interactions import verify_key_decorator, InteractionType, InteractionResponseType
import random

app = FastAPI()
DISCORD_PUBLIC_KEY = "2991a488b2c82ec2e0f47de5dbc1e6298514c4e8427fa58ea50b37ac8c7aa59c"

@app.post("/api")
@verify_key_decorator(DISCORD_PUBLIC_KEY)
async def interactions(request: Request):
    body = await request.json()

    if body["type"] == InteractionType.PING:
        return {"type": InteractionResponseType.PONG}

    if body["type"] == InteractionType.APPLICATION_COMMAND:
        command_name = body["data"]["name"]

        if command_name == "coinflip":
            result = random.choice(["Heads", "Tails"])
            return {
                "type": InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE,
                "data": {"content": f"🪙 You flipped: **{result}**!"}
            }

        return {
            "type": InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE,
            "data": {"content": "Command not implemented."}
        }

    raise HTTPException(status_code=400, detail="Unknown interaction type")
