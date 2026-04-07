from flask import Flask, request, jsonify, render_template
import requests
import datetime
import socket
import os

app = Flask(__name__)

# Načtení klíče z environment variables
OPENAI_API_KEY = os.getenv("MY_API_KEY", "klic_nenalezen")
OPENAI_BASE_URL = "https://kurim.ithope.eu/v1/chat/completions"

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
        "time": datetime.datetime.now().isoformat(),
        "python_version": "3.12-slim"
    })

@app.route('/get_messages', methods=['GET'])
def get_messages():
    return jsonify(messages)

@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.get_json()
    user = data.get("user", "Anonym")
    text = data.get("text", "")
    if not text: return jsonify({"error": "Empty"}), 400

    messages.append({"user": user, "text": text, "time": datetime.datetime.now().strftime("%H:%M:%S")})

    if "!ai" in text.lower():
        claim = text.lower().replace("!ai", "").strip()
        ai_reply = verify_fact(claim if claim else "Ahoj!")
        messages.append({"user": "🛡️ AI FAKT-CHECKER", "text": ai_reply, "time": datetime.datetime.now().strftime("%H:%M:%S")})
    return jsonify({"status": "ok"})

def verify_fact(text):
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "gemma3:27b",
        "messages": [
            {"role": "system", "content": "Jsi přísný kontrolor faktů. Odpověz jednou krátkou větou, zda je to pravda nebo lež."},
            {"role": "user", "content": text}
        ],
        "temperature": 0.7
    }
    try:
        r = requests.post(OPENAI_BASE_URL, json=payload, headers=headers, timeout=15)
        return r.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"⚠️ AI neodpovídá. (Chyba: {str(e)})"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8081)
