from flask import Flask, request, jsonify, render_template
import requests
import datetime
import socket
import os
import urllib3

# ✅ Vypnutí varování o SSL (stejně jako u tebe)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# ✅ Načtení konfigurace z ENV (s tvým funkčním base_url jako defaultem)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://kurim.ithope.eu/v1")

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

    # Přidání zprávy od uživatele
    messages.append({
        "user": user,
        "text": text,
        "time": datetime.datetime.now().strftime("%H:%M:%S")
    })

    # Logika pro AI fakt-checkera
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
    # ✅ Oprava URL na standardní OpenAI chat endpoint
    clean_url = OPENAI_BASE_URL.rstrip('/')
    target_url = f"{clean_url}/chat/completions"

    prompt = f"Zkontroluj pravdivost tvrzení, pokud je tvrzeni pravdive tak to potvrď, pokud ale není tak oprav a ve zkratce vysvětli, pokud se nekdo na neco bude ptát tak spravnost neověřuj a velmi krátce odpověz : {text}"

    # ✅ Oprava struktury payloadu (z prompt na messages)
    payload = {
        "model": "gemma3:27b",
        "messages": [{"role": "user", "content": prompt}],
        "stream": False
    }

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        # ✅ Přidáno verify=False kvůli certifikátům
        r = requests.post(
            target_url, 
            json=payload, 
            headers=headers, 
            timeout=20, 
            verify=False
        )
        
        if r.status_code == 200:
            # ✅ Oprava parsování odpovědi (choices[0]...)
            return r.json()['choices'][0]['message']['content']
        else:
            return f"Chyba AI (Status {r.status_code}): {r.text[:100]}"
            
    except Exception as e:
        return f"⚠️ AI chyba spojení: {str(e)}"

if __name__ == '__main__':
    # Spuštění na portu 8081 (podle jeho zadání)
    port = int(os.environ.get("PORT", 8081))
    app.run(host='0.0.0.0', port=port)
