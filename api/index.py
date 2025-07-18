import os
import nacl.signing
import nacl.exceptions
from flask import Flask, request, jsonify, abort

app = Flask(__name__)

DISCORD_PUBLIC_KEY = os.getenv("2991a488b2c82ec2e0f47de5dbc1e6298514c4e8427fa58ea50b37ac8c7aa59c")

def verify_signature(request):
    signature = request.headers.get("X-Signature-Ed25519")
    timestamp = request.headers.get("X-Signature-Timestamp")
    body = request.data.decode("utf-8")

    try:
        verify_key = nacl.signing.VerifyKey(bytes.fromhex(DISCORD_PUBLIC_KEY))
        verify_key.verify(f"{timestamp}{body}".encode(), bytes.fromhex(signature))
        return True
    except nacl.exceptions.BadSignatureError:
        return False

@app.route("/", methods=["POST"])
def interactions():
    if not verify_signature(request):
        abort(401)

    payload = request.json

    # Respond to Discord PING request
    if payload["type"] == 1:
        return jsonify({"type": 1})

    # Otherwise reply with dummy message
    return jsonify({
        "type": 4,
        "data": {
            "content": f"Command received: {payload['data']['name']}"
        }
    })
