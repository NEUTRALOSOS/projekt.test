# 🧠 AI NotePad (Modern Chat UI)

Jednoduchá webová chatovací aplikace vytvořená ve Flasku s moderním dark-mode rozhraním. Slouží jako sdílený poznámkový blok s možností komunikace s AI pomocí příkazu `!ai`.

---

## ✨ Funkce

- 💬 Chat pro více uživatelů v reálném čase (polling)
- 🤖 Integrace AI přes příkaz `!ai`
- 🕒 Časové razítko u každé zprávy
- 🌙 Moderní dark mode design
- 🎨 Stylizované chat bubliny (uživatel / AI)
- 📱 Responzivní layout (mobil i desktop)
- ⚡ Automatická aktualizace zpráv každé 2 sekundy

---

## 🖥️ UI Vlastnosti

- Dark background (`#0f172a`)
- Chat box ve stylu moderních aplikací (Discord-like)
- Oddělené zprávy:
  - 🔵 uživatel (vpravo)
  - ⚫ AI (vlevo, kurzíva)
- Sticky input panel dole
- Automatický scroll dolů
- Hover efekt na tlačítku

---

## 🛠️ Technologie

- **Backend:** Python + Flask  
- **Frontend:** HTML + CSS + JavaScript  
- **Komunikace:** Fetch API (REST)  

---

## 🚀 Spuštění

### 1. Instalace
```bash
pip install flask requests
