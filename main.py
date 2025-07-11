import os
import time
import requests
from bs4 import BeautifulSoup

def get_env_var(key, default=None):
    value = os.environ.get(key)
    if not value and default is None:
        print(f"❌ Variabile d'ambiente mancante: {key}")
        exit(1)
    return value or default

# Variabili d’ambiente
TOKEN = get_env_var("BOT_TOKEN")
CHAT_ID = get_env_var("CHAT_ID")
LOGIN_USERNAME = get_env_var("USERNAME")
LOGIN_PASSWORD = get_env_var("PASSWORD")
LOGIN_URL = get_env_var("LOGIN_URL")
DETAIL_URL_TEMPLATE = get_env_var("DETAIL_URL_TEMPLATE", "https://ynap.kappa3.app/home/ticketing/ticket/detail?id={id}")
START_ID = int(get_env_var("START_ID", "21950"))

sent_tickets = set()
current_id = START_ID

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": text})
    except Exception as e:
        print(f"Errore invio messaggio Telegram: {e}")

def get_logged_session():
    session = requests.Session()
    session.post(LOGIN_URL, data={
        "username": LOGIN_USERNAME,
        "password": LOGIN_PASSWORD
    })
    return session

def process_ticket(session, ticket_id):
    url = DETAIL_URL_TEMPLATE.format(id=ticket_id)
    response = session.get(url)

    if response.status_code != 200 or "Ticket non trovato" in response.text or "404" in response.text:
        print(f"[{ticket_id}] ❌ Ticket inesistente o pagina vuota")
        return

    soup = BeautifulSoup(response.text, "html.parser")

    subject_tag = soup.select_one("h5 strong")
    status_tag = soup.select_one(".status-text")

    if not subject_tag or not status_tag:
        print(f"[{ticket_id}] ⚠️ Ticket senza oggetto o stato — ignorato")
        return

    subject = subject_tag.text.strip()
    status = status_tag.text.strip().lower()

    print(f"[{ticket_id}] Stato: {status} | Oggetto: {subject}")

    if "risolto" not in status and ticket_id not in sent_tickets:
        sent_tickets.add(ticket_id)
        send_message(f"🆕 Nuovo ticket #{ticket_id}\n{subject}\n{url}")

def main():
    global current_id
    send_message("✅ Bot avviato. In ascolto per nuovi ticket.")
    session = get_logged_session()

    while True:
        try:
            process_ticket(session, current_id)
        except Exception as e:
            print(f"[{current_id}] ⚠️ Errore: {e}")
        current_id += 1
        time.sleep(5)

if __name__ == "__main__":
    main()
