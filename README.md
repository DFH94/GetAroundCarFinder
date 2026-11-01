# 🚗 GetAround Car Finder

Busca coches seminuevos en **Wallapop, coches.net, AutoScout24 y Milanuncios**, detecta gangas y te avisa por **Telegram**.

## Instalación
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # y rellena el token de Telegram
uvicorn app.main:app --reload
```
Abre http://127.0.0.1:8000

## Telegram
1. Escribe a **@BotFather** → `/newbot` → copia el token en `TELEGRAM_BOT_TOKEN`.
2. Manda un mensaje a tu bot y abre `https://api.telegram.org/bot<TOKEN>/getUpdates` → copia `chat.id` en `TELEGRAM_CHAT_ID`.
3. Reinicia y pulsa *Ajustes → Enviar prueba*.

## ¿Qué es una ganga?
Un coche cuyo precio está un X % (por defecto 15 %) por debajo de la **mediana de coches iguales** (marca + modelo + año) encontrados en todos los portales.

## Aviso
El scraping puede ir contra los términos de uso de los portales. Úsalo de forma personal y con poca frecuencia. Si un portal cambia su web, su scraper puede dejar de funcionar.
