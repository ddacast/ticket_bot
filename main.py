import os
import time
import requests
from bs4 import BeautifulSoup

# Funzione di utilità per caricare variabili d'ambiente
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
START_ID = int(get_env_var("START_ID", "21950"))  # fallback se non è presente

# Variabili interne
sent_tickets = set()
current_id = START_ID

# Invia messaggio Telegram
def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": text})
    except Exception as e:
        print(f"Errore invio messaggio Telegram: {e}")

# Login e sessione
def get_logged_session():
    session = requests.Session()
    session.post(LOGIN_URL, data={
        "username": LOGIN_USERNAME,
        "password": LOGIN_PASSWORD
    })
    return session

# Estrai dettagli ticket da ID
def process_ticket(session, ticket_id):
    url = DETAIL_URL_TEMPLATE.format(id=ticket_id)
    response = session.get(url)

    if response.status_code != 200:
        print(f"[{ticket_id}] ❌ Ticket non trovato (HTTP {response.status_code})")
        return

    soup = BeautifulSoup(response.text, "html.parser")

    # Estrai dati con fallback
    subject = soup.select_one("h5 strong")
    subject_text = subject.text.strip() if subject else "(Nessun oggetto)"

    status = soup.select_one(".status-text")
    status_text = status.text.strip().lower() if status else "(stato non trovato)"

    print(f"[{ticket_id}] Stato: {status_text} - Oggetto: {subject_text}")

    if "risolto" not in status_text and ticket_id not in sent_tickets:
        sent_tickets.add(ticket_id)
        send_message(f"🆕 Nuovo ticket #{ticket_id}\n{subject_text}\n{url}")

# Loop principale
def main():
    global current_id
    send_message("✅ Bot avviato con successo e in ascolto.")

    session = get_logged_session()

    while True:
        try:
            process_ticket(session, current_id)
            current_id += 1
        except Exception as e:
            send_message(f"⚠️ Errore su ticket #{current_id}:\n{e}")
            current_id += 1
        time.sleep(5)

if __name__ == "__main__":
    main()
