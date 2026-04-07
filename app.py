from flask import Flask, request, jsonify, render_template
import requests
import datetime
import socket
import os

app = Flask(__name__)

# ✅ načtení z ENV (server si to nastaví sám)
api_key = os.environ.get("OPENAI_API_KEY",)
base_url = os.environ.get("OPENAI_BASE_URL", "https://kurim.ithope.eu/v1")

# List pro ukládání historie zpráv
messages = []

def get_server_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ping', methods=['GET'])
def ping():
    return "pong"

@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        "status": "online",
        "author": "Martin Havlicek",
        "ip": get_server_ip(),
        "time": datetime.datetime.now().isoformat()
    })

@app.route('/get_messages', methods=['GET'])
def get_messages():
    return jsonify(messages)

@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.get_json()
    user = data.get("user", "Anonym")
    text = data.get("text", "")

    if not text:
        return jsonify({"error": "Empty text"}), 400

    messages.append({
        "user": user,
        "text": text,
        "time": datetime.datetime.now().strftime("%H:%M:%S")
    })

    if "!ai" in text.lower():
        claim = text.lower().replace("!ai", "").strip()
        ai_reply = verify_fact(claim if claim else "Ahoj, jsem připraven kontrolovat fakta.")
        messages.append({
            "user": "🛡️ AI FAKT-CHECKER",
            "text": ai_reply,
            "time": datetime.datetime.now().strftime("%H:%M:%S")
        })

    return jsonify({"status": "ok"})

def verify_fact(text):
    # ✅ použije BASE_URL z ENV
    url = f"{OPENAI_BASE_URL}/chat/completions"

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "Jsi přísný kontrolor faktů. Odpověz jednou větou."},
            {"role": "user", "content": text}
        ]
    }

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=15)
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"⚠️ AI chyba: {str(e)}"

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get("PORT", 8081))
    )
