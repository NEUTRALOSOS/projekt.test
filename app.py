from flask import Flask, request, jsonify, render_template
import requests
import datetime
import socket
import os
import urllib3
import time
from sqlalchemy import create_engine, text

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# --- DATABÁZE ---
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///local.db")
engine = create_engine(DATABASE_URL)

# Retry loop: Pockej, az se DB nastartuje (podle zadání v tipech)
for i in range(10):
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        break
    except Exception:
        print(f"Cekam na DB... pokus {i+1}")
        time.sleep(2)

# Vytvoreni tabulky pro zpravy/nicknamy
with engine.connect() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100),
            message_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    conn.commit()

# --- ZBYTEK LOGIKY ---
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://kurim.ithope.eu/v1")

def get_server_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except: return "127.0.0.1"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_messages', methods=['GET'])
def get_messages():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT username, message_text, created_at FROM chat_messages ORDER BY created_at ASC"))
        output = []
        for row in result:
            output.append({
                "user": row[0],
                "text": row[1],
                "time": row[2].strftime("%H:%M:%S")
            })
    return jsonify(output)

@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.get_json()
    user = data.get("user", "Anonym")
    text_val = data.get("text", "")

    if not text_val:
        return jsonify({"error": "Empty text"}), 400

    # Ulozeni do DB
    with engine.connect() as conn:
        conn.execute(
            text("INSERT INTO chat_messages (username, message_text) VALUES (:u, :t)"),
            {"u": user, "t": text_val}
        )
        conn.commit()

    # AI logika zůstává stejná, jen výsledek taky uložíme do DB
    if "!ai" in text_val.lower():
        claim = text_val.lower().replace("!ai", "").strip()
        ai_reply = verify_fact(claim if claim else "Ahoj!")
        with engine.connect() as conn:
            conn.execute(
                text("INSERT INTO chat_messages (username, message_text) VALUES (:u, :t)"),
                {"u": "🛡️ AI FAKT-CHECKER", "t": ai_reply}
            )
            conn.commit()

    return jsonify({"status": "ok"})

def verify_fact(text_input):
    clean_url = OPENAI_BASE_URL.rstrip('/')
    target_url = f"{clean_url}/chat/completions"
    prompt = f"Zkontroluj pravdivost: {text_input}"
    
    payload = {
        "model": "gemma3:27b",
        "messages": [{"role": "user", "content": prompt}],
        "stream": False
    }
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}

    try:
        r = requests.post(target_url, json=payload, headers=headers, timeout=20, verify=False)
        return r.json()['choices'][0]['message']['content'] if r.status_code == 200 else "Chyba AI"
    except:
        return "⚠️ AI chyba spojení"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
