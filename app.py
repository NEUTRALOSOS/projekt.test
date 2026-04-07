from flask import Flask, request, jsonify, render_template
import requests
import datetime
import socket
import os
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# ✅ načtení z ENV
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")  # nevyužitý, ale kvůli zadání
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "http://host.docker.internal:11434")

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
    # ✅ Ollama endpoint z ENV
    url = f"{OPENAI_BASE_URL}/api/generate"

    prompt = f"Jsi přísný kontrolor faktů. Posuď krátce (1 věta), zda je toto tvrzení pravdivé nebo lživé: {text}"

    payload = {
        "model": "gemma3:27b",
        "prompt": prompt,
        "stream": False
    }

    try:
        # Skládání URL pro endpoint kurim.ithope.eu/v1
        clean_url = base_url.rstrip('/')
        target_url = f"{clean_url}/chat/completions"
        
        # DEBUG výpis do konzole dockeru (uvidíš v logu, kam se to skutečně posílá)
        print(f"DEBUG: Volám URL: {target_url}")

        response = requests.post(
            target_url, 
            headers=headers, 
            json=payload, 
            timeout=20, 
            verify=False
        )
        
        if response.status_code == 200:
            ai_response = response.json()['choices'][0]['message']['content']
            return jsonify({"recommendation": ai_response})
        else:
            # Pokud server vrátí chybu, pošleme ji do frontendu pro diagnostiku
            return jsonify({
                "error": f"Server vrátil {response.status_code}.",
                "details": response.text
            }), response.status_code

    except Exception as e:
        return jsonify({"error": f"Spojení selhalo: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)  
