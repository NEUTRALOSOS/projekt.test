from flask import Flask, request, jsonify, render_template_string
import requests
import os
import urllib3
import time
from sqlalchemy import create_engine, text

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://student:heslo123@db:5432/myapp")
engine = create_engine(DATABASE_URL)

# --- 1. ČEKÁNÍ NA DATABÁZI (Jako u kamaráda) ---
db_ready = False
print("Iniciuji připojení k databázi...")
for i in range(15):
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Databáze Postgres je připravena.")
        db_ready = True
        break
    except Exception as e:
        print(f"❌ Čekám na databázi... (pokus {i+1}/15)")
        time.sleep(3)

# Pokud se připojíme, rovnou vytvoříme tabulky
if db_ready:
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

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://kurim.ithope.eu/v1")

# --- 2. TVŮJ HTML KÓD VLOŽENÝ PŘÍMO SEM ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="cs">
<head>
<meta charset="UTF-8">
<title>AINotePad</title>
<style>
    * { box-sizing: border-box; }
    body { font-family: 'Segoe UI', sans-serif; background: #0f172a; margin: 0; display: flex; justify-content: center; align-items: center; height: 100vh; }
    .container { width: 100%; max-width: 600px; height: 90vh; background: #1e293b; display: flex; flex-direction: column; border-radius: 15px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
    .header { background: #020617; color: #38bdf8; padding: 15px; text-align: center; font-size: 1.1em; font-weight: bold; border-bottom: 1px solid #334155; }
    #chat { flex: 1; overflow-y: auto; padding: 15px; display: flex; flex-direction: column; gap: 10px; }
    .m { padding: 10px 12px; border-radius: 12px; max-width: 80%; word-wrap: break-word; font-size: 0.95em; }
    .u { align-self: flex-end; background: #0ea5e9; color: white; }
    .a { align-self: flex-start; background: #334155; color: #e2e8f0; font-style: italic; }
    .info { font-size: 0.7em; opacity: 0.7; display: block; margin-bottom: 4px; }
    .controls { padding: 10px; display: flex; gap: 8px; background: #020617; border-top: 1px solid #334155; }
    input { padding: 10px; border-radius: 8px; border: none; background: #1e293b; color: white; outline: none; }
    input::placeholder { color: #94a3b8; }
    button { padding: 10px 15px; background: #0ea5e9; color: white; border: none; border-radius: 8px; cursor: pointer; transition: 0.2s; }
    button:hover { background: #0284c7; }
    @media (max-width: 600px) {
        .container { height: 100vh; border-radius: 0; }
        .controls { flex-direction: column; }
        #nick { width: 100% !important; }
        button { width: 100%; }
    }
</style>
</head>
<body>
<div class="container">
    <div class="header">ENotePad: MartinHavlicek.skola.test</div>
    <div id="chat"></div>
    <div class="controls">
        <input type="text" id="nick" placeholder="Přezdívka" style="width: 100px;">
        <input type="text" id="msg" placeholder="Zpráva (použij !ai ...)" style="flex: 1;" onkeypress="if(event.key==='Enter') send()">
        <button onclick="send()">Odeslat</button>
    </div>
</div>
<script>
    let msgCount = 0;
    async function send() {
        const nick = document.getElementById('nick').value || "Host";
        const input = document.getElementById('msg');
        if (!input.value.trim()) return;
        await fetch('/send_message', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ user: nick, text: input.value })
        });
        input.value = '';
        update();
    }
    async function update() {
        const r = await fetch('/get_messages');
        const data = await r.json();
        const box = document.getElementById('chat');
        if (data.length !== msgCount) {
            box.innerHTML = '';
            data.forEach(m => {
                const cls = m.user.includes('AI') ? 'a' : 'u';
                box.innerHTML += `<div class="m ${cls}"><span class="info">${m.user} (${m.time})</span>${m.text}</div>`;
            });
            box.scrollTop = box.scrollHeight;
            msgCount = data.length;
        }
    }
    setInterval(update, 2000);
    update();
</script>
</body>
</html>
"""

# --- 3. ROUTY ---
@app.route('/')
def index():
    if not db_ready:
        return "Databáze není připravena, zkuste to za chvíli.", 503
    # Renderujeme přímo ten obrovský text výše, nepotřebujeme složku templates!
    return render_template_string(HTML_TEMPLATE)

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
    target_port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=target_port)
