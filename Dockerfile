FROM python:3.12-slim

WORKDIR /app

# Instalace závislostí
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopírování zbytku aplikace
COPY . .

# Exponujeme port 5000 (standard pro Flask v Dockeru)
EXPOSE 5000

# Spuštění aplikace
CMD ["python", "app.py"]
