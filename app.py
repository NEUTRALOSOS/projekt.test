from flask import Flask, request, jsonify, render_template
import requests
import os
import urllib3
import time
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Důležité: __name__ musí mít dvě podtržítka na každé straně!
app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://student:heslo123@db:5432/myapp")
engine = create_engine(DATABASE_URL)

def init_db():
    print("Iniciuji připojení k databázi...")
    # Zvýšíme počet pokusů, Postgres může startovat déle
    for i in range(15):
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
            print("✅ Databáze Postgres je připravena.")
            return True
        except Exception as e:
            print(f"❌ Čekám na databázi... (pokus {i+1}/15), chyba: {e}")
            time.sleep(3)
    return False

# Spustíme inicializaci
db_ready = init_db()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://kurim.ithope.eu/v1")

@app.route('/')
def index():
    if not db_ready:
        return "Databáze není připravena, zkuste to za chvíli.", 503
    return render_template('index.html')

@app.route('/get_messages', methods=['GET'])
def get_messages():
    try:
        with engine.connect() as conn:
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

if __name__ == '__main__':
    # Načtení portu z proměnné prostředí (dle screenshotu č. 1)
    target_port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=target_port)
