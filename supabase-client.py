import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()  # Load variables from .env

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_balance(user_id: str) -> int:
    response = supabase.table('users').select('balance').eq('id', user_id).single().execute()
    if response.data:
        return response.data['balance']
    else:
        supabase.table('users').insert({'id': user_id, 'balance': 0}).execute()
        return 0

def set_balance(user_id: str, amount: int) -> None:
    supabase.table('users').upsert({'id': user_id, 'balance': amount}).execute()

def get_winrate(game: str) -> float:
    response = supabase.table('winrates').select('rate').eq('game', game).single().execute()
    if response.data:
        return float(response.data['rate'])
    else:
        supabase.table('winrates').insert({'game': game, 'rate': 0.5}).execute()
        return 0.5

def set_winrate(game: str, rate: float) -> None:
    supabase.table('winrates').upsert({'game': game, 'rate': rate}).execute()
