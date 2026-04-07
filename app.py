from flask import Flask, request, jsonify, render_template
import requests
import datetime
import socket

app = Flask(__name__)

# Tvůj OpenAI-compatible setup
OPENAI_API_KEY = ""
OPENAI_BASE_URL = "https://kurim.ithope.eu/v1"

# List pro ukládání historie zpráv v paměti
messages = []

def get_server_ip():
    """Zjistí IP adresu serveru pro zobrazení v záhlaví [cite: 8, 14]"""
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
    """Povinný endpoint dle zadání [cite: 15, 23]"""
    return "pong"

@app.route('/status', methods=['GET'])
def status():
    """Povinný endpoint s autorem a časem [cite: 15, 23]"""
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

    # Uložíme zprávu od uživatele
    messages.append({
        "user": user, 
        "text": text, 
        "time": datetime.datetime.now().strftime("%H:%M:%S")
    })

    # Pokud zpráva obsahuje !ai, spustíme kontrolu faktů [cite: 9, 30]
    if "!ai" in text.lower():
        claim = text.lower().replace("!ai", "").strip()
        ai_reply = verify_fact(claim if claim else "Ahoj, jsem připraven kontrolovat fakta.")
        messages.append({
            "user": "🛡️ AI FAKT-CHECKER", 
            "text": ai_reply, 
            "time": datetime.datetime.now().strftime("%H:%M:%S")
        })

    return jsonify({"status": "ok"})

@app.route('/ai', methods=['POST'])
def ai_endpoint():
    """Povinný endpoint POST /ai vyžadovaný zadáním [cite: 15, 23]"""
    data = request.get_json()
    prompt = data.get("prompt", "")
    return jsonify({"reply": verify_fact(prompt)})

def verify_fact(text):
    """Volání externího LLM pro kontrolu správnosti [cite: 17, 30]"""
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "gemma3:27b",
        "messages": [
            {
                "role": "system", 
                "content": "Jsi přísný kontrolor faktů. Posuď krátce (1 věta), zda je tvrzení pravdivé nebo lživé."
            },
            {"role": "user", "content": text}
        ],
        "temperature": 0.7,
        "max_tokens": 100 # Držíme odpověď krátkou dle zadání [cite: 30, 74]
    }

    try:
        r = requests.post(OPENAI_BASE_URL, json=payload, headers=headers, timeout=15)
        # Formát pro OpenAI-compatible API
        result = r.json()
        return result['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"⚠️ AI momentálně nedostupná. (Chyba: {str(e)})"

if __name__ == '__main__':
    # Běží na portu 8081 dle zadání [cite: 8, 16, 24]
    app.run(host='0.0.0.0', port=8081)
