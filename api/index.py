import os
from flask import Flask, request, jsonify, abort
import nacl.signing
import nacl.exceptions

app = Flask(__name__)
PUBLIC_KEY = os.getenv("2991a488b2c82ec2e0f47de5dbc1e6298514c4e8427fa58ea50b37ac8c7aa59c")

def verify_signature(req):
    signature = req.headers.get("X-Signature-Ed25519")
    timestamp = req.headers.get("X-Signature-Timestamp")
    body = req.data.decode("utf-8")

    try:
        verify_key = nacl.signing.VerifyKey(bytes.fromhex(PUBLIC_KEY))
        verify_key.verify(f"{timestamp}{body}".encode(), bytes.fromhex(signature))
        return True
    except nacl.exceptions.BadSignatureError:
        return False

@app.route("/", methods=["POST", "GET"])
def main():
    if request.method == "GET":
        return "Bot is running", 200

    if not verify_signature(request):
        abort(401)

    payload = request.json
    if payload["type"] == 1:  # PING from Discord
        return jsonify({"type": 1})

    # For now, just acknowledge other commands
    return jsonify({"type": 4, "data": {"content": "✅ Slash command received!"}})
