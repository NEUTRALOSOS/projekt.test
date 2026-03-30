from flask import Flask, request, jsonify, render_template
import requests
import datetime
import socket

app = Flask(__name__)

# List pro ukládání zpráv v paměti
messages = []

def get_ip():
    """Pomocná funkce pro zjištění aktuální IP serveru"""
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
        "server_ip": get_ip(),
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

    # Uložíme zprávu od člověka
    new_msg = {"user": user, "text": text, "time": datetime.datetime.now().strftime("%H:%M:%S")}
    messages.append(new_msg)

    # Reakce na příkaz !ai
    if text.strip().startswith("!ai"):
        prompt = text.replace("!ai", "").strip()
        ai_response = call_ollama(prompt if prompt else "Ahoj, jsem tvůj AI asistent.")
        messages.append({
            "user": "🤖 AI MODERÁTOR",
            "text": ai_response,
            "time": datetime.datetime.now().strftime("%H:%M:%S")
        })

    return jsonify({"status": "ok"})

def call_gemma(prompt):
    # host.docker.internal zajistí komunikaci ven z kontejneru na tvou Ollamu
    url = "http://host.docker.internal:11434/api/generate"
    payload = {
        "model": "gemma3:27b",
        "prompt": f"Jsi stručný asistent v chatu. Odpověz jednou větou na: {prompt}",
        "stream": False
    }
    try:
        r = requests.post(url, json=payload, timeout=15)
        return r.json().get("response", "AI neodpovídá správně.")
    except:
        return "⚠️ AI je momentálně nedostupná (zkontroluj GEMMA_HOST=0.0.0.0)."

if __name__ == '__main__':
    # host='0.0.0.0' zajistí, že appka je PUBLIC v celé tvé síti
    app.run(host='0.0.0.0', port=8081, debug=False)