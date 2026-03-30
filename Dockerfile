# Použijeme lehký Python obraz
FROM python:3.9-slim

# Nastavení pracovního adresáře
WORKDIR /app

# Kopírování souborů
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Expozice portu
EXPOSE 8081

# Spuštění aplikace
CMD ["python", "app.py"]