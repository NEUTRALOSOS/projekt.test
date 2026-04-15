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

# --- DATABÁZE (SQLite v perzistentním adresáři /data) ---
# Používáme 4 lomítka pro absolutní cestu v SQLite
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:////data/database.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Inicializace tabulky při startu
def init_db():
    try:
        with engine.begin() as conn:  # begin() automaticky dělá commit
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username VARCHAR(100),
                    message_text TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
        print("Databáze inicializována v /data/database.db")
    except Exception as e:
        print(f"Chyba pri inicializaci DB: {e}")

init_db()

# --- ZBYTEK LOGIKY ---
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://kurim.ithope.eu/v1")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_messages', methods=['GET'])
def get_messages():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT username, message_text, created_at FROM chat_messages ORDER BY created_at ASC"))
            output = []
            for row in result:
                # Ošetření None hodnot u času
                time_str = row[2].strftime("%H:%M:%S") if row[2] else datetime.datetime.now().strftime("%H:%M:%S")
                output.append({
                    "user": row[0],
                    "text": row[1],
                    "time": time_str
                })
        return jsonify(output)
    except Exception as e:
        print(f"Chyba při načítání: {e}")
        return jsonify([]), 200

@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.get_json()
    user = data.get("user", "Anonym")
    text_val = data.get("text", "")

    if not text_val:
        return jsonify({"error": "Empty text"}), 400

    try:
        # Ulozeni uzivatelske zpravy
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO chat_messages (username, message_text) VALUES (:u, :t)"),
                {"u": user, "t": text_val}
            )

        # AI logika
        if "!ai" in text_val.lower():
            claim = text_val.lower().replace("!ai", "").strip()
            ai_reply = verify_fact(claim if claim else "Ahoj!")
            with engine.begin() as conn:
                conn.execute(
                    text("INSERT INTO chat_messages (username, message_text) VALUES (:u, :t)"),
                    {"u": "🛡️ AI FAKT-CHECKER", "t": ai_reply}
                )
        
        return jsonify({"status": "ok"})
    except Exception as e:
        print(f"Chyba při odesílání: {e}")
        return jsonify({"error": str(e)}), 500

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
        if r.status_code == 200:
            return r.json()['choices'][0]['message']['content']
        return f"Chyba AI (Status: {r.status_code})"
    except Exception as e:
        return f"⚠️ AI chyba spojení: {str(e)}"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
