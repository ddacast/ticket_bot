import time
import requests
import os
from bs4 import BeautifulSoup

# Configurazioni
DELAY = 60
DETAIL_URL_BASE = "https://ynap.kappa3.app/home/ticketing/ticket/detail?id="

# Recupera e verifica le variabili d'ambiente
def get_env_var(key):
    value = os.environ.get(key)
    if not value:
        print(f"❌ Variabile d'ambiente mancante: {key}")
        exit(1)
    return value

# Variabili
BOT_TOKEN = get_env_var("BOT_TOKEN")
CHAT_ID = get_env_var("CHAT_ID")
LOGIN_URL = get_env_var("LOGIN_URL")
TICKET_USERNAME = get_env_var("USERNAME")
TICKET_PASSWORD = get_env_var("PASSWORD")

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        response = requests.post(url, data={"chat_id": CHAT_ID, "text": text})
        print(f"📤 Messaggio inviato: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Errore invio messaggio Telegram: {e}")

def login():
    print("🔐 Effettuo login...")
    session = requests.Session()
    try:
        response = session.post(LOGIN_URL, data={
            "username": TICKET_USERNAME,
            "password": TICKET_PASSWORD
        })
        print(f"🔐 Login status: {response.status_code}")
        return session
    except Exception as e:
        print(f"❌ Errore durante il login: {e}")
        return None

def ticket_exists(session, ticket_id):
    url = f"{DETAIL_URL_BASE}{ticket_id}"
    print(f"🔎 Controllo ticket {ticket_id}: {url}")

    try:
        r = session.get(url)
        print(f"📥 GET {r.status_code}")
        if "Ticket non trovato" in r.text or r.status_code != 200:
            print(f"[{ticket_id}] ❌ Ticket non trovato")
            return None

        soup = BeautifulSoup(r.text, "html.parser")
        subject_tag = soup.select_one("div.ticket-data h4")
        status_tag = soup.select_one("span.tkt-status")

        subject = subject_tag.text.strip() if subject_tag else None
        status = status_tag.text.strip() if status_tag else None

        if not subject or not status:
            print(f"[{ticket_id}] ⚠️ Ticket senza oggetto o stato — ignorato")
            return None

        print(f"[{ticket_id}] ✅ Ticket trovato — Oggetto: {subject}, Stato: {status}")
        return {
            "id": ticket_id,
            "subject": subject,
            "status": status,
            "link": url
        }

    except Exception as e:
        print(f"[{ticket_id}] ❌ Errore nel parsing: {e}")
        return None

def main():
    print("✅ Bot avviato. Controllo ticket per ID incrementale...")
    send_message("🚀 Bot avviato ed in ascolto.")
    
    session = login()
    if not session:
        return

    current_id = 21954  # metti qui l’ultimo ID valido

    while True:
        ticket = ticket_exists(session, current_id)
        if ticket and ticket["status"].lower() != "risolto":
            send_message(f"🆕 Ticket #{ticket['id']}\n{ticket['subject']}\n{ticket['link']}")
        else:
            print(f"[{current_id}] Nessun nuovo ticket o già risolto.")
        current_id += 1
        time.sleep(DELAY)

if __name__ == "__main__":
    main()
