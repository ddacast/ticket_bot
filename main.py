import time
import os
import requests
from bs4 import BeautifulSoup

# Config da variabili d'ambiente
TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
LOGIN_USERNAME = os.environ.get("USERNAME")
LOGIN_PASSWORD = os.environ.get("PASSWORD")
LOGIN_URL = os.environ.get("LOGIN_URL")
DETAIL_URL_BASE = os.environ.get("TICKET_DETAIL_URL_BASE")  # tipo: https://ynap.kappa3.app/home/ticketing/ticket/detail?id=

# Check variabili
for var in ["BOT_TOKEN", "CHAT_ID", "USERNAME", "PASSWORD", "LOGIN_URL", "TICKET_DETAIL_URL_BASE"]:
    if not os.environ.get(var):
        print(f"❌ Variabile mancante: {var}")
        exit(1)

# Inizializzazione
START_ID = int(os.environ.get("START_TICKET_ID", 21954))
DELAY = 5  # secondi tra controlli

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": text})
    except Exception as e:
        print(f"❌ Errore Telegram: {e}")

def ticket_exists(session, ticket_id):
    detail_url = f"{DETAIL_URL_BASE}{ticket_id}"
    r = session.get(detail_url)
    if "Ticket non trovato" in r.text or r.status_code != 200:
        return None  # non esiste

    soup = BeautifulSoup(r.text, "html.parser")
    
    subject_tag = soup.select_one(".tkt-subject")
    status_tag = soup.select_one(".tkt-status-label")

    subject = subject_tag.text.strip() if subject_tag else None
    status = status_tag.text.strip() if status_tag else None

    if not subject or not status:
        print(f"[{ticket_id}] ⚠️ Ticket senza oggetto o stato — ignorato")
        return None

    return {
        "id": ticket_id,
        "subject": subject,
        "status": status,
        "link": detail_url
    }

def main():
    session = requests.Session()

    # Login iniziale
    session.post(LOGIN_URL, data={
        "username": LOGIN_USERNAME,
        "password": LOGIN_PASSWORD
    })

    ticket_id = START_ID
    send_message(f"✅ Bot avviato. Inizio da ID {ticket_id}...")

    while True:
        ticket = ticket_exists(session, ticket_id)
        if ticket and ticket["status"].lower() != "risolto":
            message = (
                f"🆕 Nuovo ticket #{ticket['id']}\n"
                f"{ticket['subject']}\n"
                f"{ticket['link']}"
            )
            send_message(message)
        ticket_id += 1
        time.sleep(DELAY)

if __name__ == "__main__":
    main()
