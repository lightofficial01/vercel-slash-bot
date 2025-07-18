import os
import random
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import nacl.signing
import nacl.encoding
import nacl.exceptions
from supabase import create_client

app = FastAPI()

# Env vars
DISCORD_PUBLIC_KEY = os.getenv("DISCORD_PUBLIC_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
ADMIN_USER_ID = os.getenv("ADMIN_USER_ID")  # Put your Discord ID here

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def verify_signature(request: Request, body: bytes) -> bool:
    signature = request.headers.get("X-Signature-Ed25519")
    timestamp = request.headers.get("X-Signature-Timestamp")
    if not signature or not timestamp:
        return False
    try:
        verify_key = nacl.signing.VerifyKey(DISCORD_PUBLIC_KEY, encoder=nacl.encoding.HexEncoder)
        message = timestamp.encode() + body
        verify_key.verify(message, bytes.fromhex(signature))
        return True
    except nacl.exceptions.BadSignatureError:
        return False

async def get_user_balance(user_id: str) -> int:
    res = supabase.table("users").select("balance").eq("id", user_id).execute()
    data = res.data
    if not data:
        # New user starts with 1,000 coins by default
        supabase.table("users").insert({"id": user_id, "balance": 1000}).execute()
        return 1000
    return data[0]["balance"]

async def update_user_balance(user_id: str, new_balance: int):
    supabase.table("users").upsert({"id": user_id, "balance": new_balance}).execute()

def get_leaderboard():
    res = supabase.table("users").select("id,balance").order("balance", desc=True).limit(10).execute()
    return res.data or []

@app.post("/")
async def interactions(request: Request):
    body = await request.body()

    # Verify Discord request signature for security
    if not verify_signature(request, body):
        return JSONResponse(status_code=401, content={"error": "invalid request signature"})

    payload = await request.json()

    # Respond to Discord PINGs immediately
    if payload["type"] == 1:
        return {"type": 1}

    # Respond to slash commands immediately to avoid timeout
    if payload["type"] == 2:
        data = payload.get("data", {})
        name = data.get("name")
        options = {opt["name"]: opt.get("value") for opt in data.get("options", [])}
        user_id = payload["member"]["user"]["id"]

        # Helper for responding easily
        async def respond(content: str):
            return {"type": 4, "data": {"content": content}}

        # Commands
        if name == "help":
            return await respond(
                "**Commands:**\n"
                "/coinflip <amount>\n"
                "/blackjack <amount>\n"
                "/chest <amount>\n"
                "/balance [user]\n"
                "/leaderboard\n"
                "/setbalance <user> <amount> (admin only)\n"
                "/pay <user> <amount>\n"
                "/deposit, /withdraw (tickets)\n"
                "/winrate <game> <decimal> (admin only)"
            )

        elif name == "balance":
            target_id = options.get("user", user_id)
            bal = await get_user_balance(target_id)
            return await respond(f"<@{target_id}>'s balance is {bal} coins.")

        elif name == "coinflip":
            try:
                amount = int(options.get("amount", 0))
                if amount <= 0:
                    return await respond("Bet must be a positive number.")
            except Exception:
                return await respond("Invalid bet amount.")

            bal = await get_user_balance(user_id)
            if amount > bal:
                return await respond("You don't have enough coins to bet that amount.")

            win_chance = 0.4
            if random.random() < win_chance:
                new_bal = bal + amount
                result = f"You won! Your new balance is {new_bal} coins."
            else:
                new_bal = bal - amount
                result = f"You lost! Your new balance is {new_bal} coins."
            await update_user_balance(user_id, new_bal)
            return await respond(result)

        elif name == "blackjack":
            try:
                amount = int(options.get("amount", 0))
                if amount <= 0:
                    return await respond("Bet must be a positive number.")
            except Exception:
                return await respond("Invalid bet amount.")

            bal = await get_user_balance(user_id)
            if amount > bal:
                return await respond("You don't have enough coins to bet that amount.")

            # Rigged 40% chance to win
            win_chance = 0.4
            if random.random() < win_chance:
                new_bal = bal + amount
                result = f"You won blackjack! Your new balance is {new_bal} coins."
            else:
                new_bal = bal - amount
                result = f"You lost blackjack! Your new balance is {new_bal} coins."
            await update_user_balance(user_id, new_bal)
            return await respond(result)

        elif name == "chest":
            try:
                amount = int(options.get("amount", 0))
                if amount <= 0:
                    return await respond("Amount must be a positive number.")
            except Exception:
                return await respond("Invalid amount.")

            cost = amount * 10_000_000
            bal = await get_user_balance(user_id)
            if cost > bal:
                return await respond("You don't have enough coins to buy that many chests.")

            loot_table = [
                (0.5, 5_000_000),
                (0.35, 7_500_000),
                (0.13, 8_250_000),
                (0.015, 30_000_000),
                (0.0039, 50_000_000),
                (0.001, 100_000_000),
                (0.0001, 750_000_000),
            ]
            total_reward = 0
            for _ in range(amount):
                r = random.random()
                cumulative = 0
                for chance, reward in loot_table:
                    cumulative += chance
                    if r < cumulative:
                        total_reward += reward
                        break
            new_bal = bal - cost + total_reward
            await update_user_balance(user_id, new_bal)
            return await respond(
                f"You opened {amount} chest(s) for {cost} coins.\n"
                f"You got {total_reward} coins in rewards!\n"
                f"Your new balance is {new_bal} coins."
            )

        elif name == "leaderboard":
            leaderboard = get_leaderboard()
            if not leaderboard:
                return await respond("Leaderboard is empty.")
            text = "**Leaderboard - Top 10 users:**\n"
            for i, entry in enumerate(leaderboard, start=1):
                text += f"{i}. <@{entry['id']}> - {entry['balance']} coins\n"
            return await respond(text)

        elif name == "setbalance":
            if user_id != ADMIN_USER_ID:
                return await respond("You are not authorized to use this command.")

            target_id = options.get("user")
            amount = options.get("amount")

            if not target_id or amount is None:
                return await respond("Please specify both user and amount.")

            try:
                amount = int(amount)
                if amount < 0:
                    return await respond("Amount cannot be negative.")
            except Exception:
                return await respond("Invalid amount.")

            supabase.table("users").upsert({"id": target_id, "balance": amount}).execute()
            return await respond(f"Set <@{target_id}>'s balance to {amount} coins.")

        elif name == "pay":
            target_id = options.get("user")
            amount = options.get("amount")

            if not target_id or amount is None:
                return await respond("Please specify both user and amount.")

            try:
                amount = int(amount)
                if amount <= 0:
                    return await respond("Amount must be positive.")
            except Exception:
                return await respond("Invalid amount.")

            bal = await get_user_balance(user_id)
            if bal < amount:
                return await respond("You don't have enough coins to pay that amount.")

            target_bal = await get_user_balance(target_id)
            await update_user_balance(user_id, bal - amount)
            await update_user_balance(target_id, target_bal + amount)
            return await respond(f"You paid <@{target_id}> {amount} coins.")

        else:
            return await respond("Unknown command. Use /help to see available commands.")
    
    # If other types come in, just return empty
    return JSONResponse(status_code=404, content={"error": "Unsupported interaction type"})
