from flask import Flask, request, jsonify, render_template
import requests
import os
import urllib3
import time
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(name)


DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://student:heslo123@db:5432/myapp")
engine = create_engine(DATABASE_URL)

def init_db():
    # Počkáme, až se Postgres nastartuje (max 10 pokusů)
    for i in range(10):
        try:
            with engine.begin() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS chat_messages (
                        id SERIAL PRIMARY KEY,
                        username VARCHAR(100),
                        message_text TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
            print("Databáze Postgres je připravena.")
            return
        except OperationalError:
            print(f"Čekám na databázi... (pokus {i+1}/10)")
            time.sleep(2)

init_db()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://kurim.ithope.eu/v1")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_messages', methods=['GET'])
def get_messages():
    try:
        with engine.connect() as conn:
            # Postgres používá TO_CHAR pro formátování času
            query = text("SELECT username, message_text, TO_CHAR(created_at, 'HH24:MI:SS') FROM chat_messages ORDER BY created_at ASC")
            result = conn.execute(query)
            output = [{"user": row[0], "text": row[1], "time": row[2]} for row in result]
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
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO chat_messages (username, message_text) VALUES (:u, :t)"),
                {"u": user, "t": text_val}
            )

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
    target_url = f"{OPENAI_BASE_URL.rstrip('/')}/chat/completions"
    payload = {
        "model": "gemma3:27b",
        "messages": [{"role": "user", "content": f"Zkontroluj pravdivost: {text_input}"}],
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

if name == 'main':
    app.run(host='0.0.0.0', port=5000)
