import time
import requests
import os
from bs4 import BeautifulSoup
from threading import Timer

# Recupera e verifica le variabili d'ambiente
def get_env_var(key):
    value = os.environ.get(key)
    if not value:
        print(f"❌ Variabile d'ambiente mancante: {key}")
        exit(1)
    return value

# Variabili d’ambiente (matchano i nomi in Railway)
TOKEN = get_env_var("BOT_TOKEN")
CHAT_ID = get_env_var("CHAT_ID")
LOGIN_USERNAME = get_env_var("USERNAME")
LOGIN_PASSWORD = get_env_var("PASSWORD")
LOGIN_URL = get_env_var("LOGIN_URL")
TICKET_URL = get_env_var("TICKET_URL")

# Impostazioni
sent_tickets = {}
TICKET_CHECK_INTERVAL = 60   # ogni 60 secondi
REMINDER_INTERVAL = 60       # ogni 60 secondi dopo il primo
FIRST_REMINDER_AFTER = 900   # primo promemoria dopo 15 minuti

# Funzione per inviare messaggi Telegram
def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": text})
    except Exception as e:
        print(f"Errore nell'invio del messaggio Telegram: {e}")

# Funzione per controllare nuovi ticket
def check_new_tickets():
    session = requests.Session()

    # Login
    session.post(LOGIN_URL, data={
        "username": USERNAME,
        "password": PASSWORD
    })

    response = session.get(TICKET_URL)
    soup = BeautifulSoup(response.text, "html.parser")

    for row in soup.select("table.tkt-table tr"):
        ticket_id = row.get("data-key")
        if not ticket_id or ticket_id in sent_tickets:
            continue

        subject_tag = row.select_one("h5 a")
        subject = subject_tag.text.strip() if subject_tag else ""
        link = f"https://ynap.kappa3.app{subject_tag['href']}" if subject_tag else ""

        status_tag = row.select_one(".fa-ticket")
        status = status_tag.next_sibling.strip() if status_tag and status_tag.next_sibling else ""

        if status.lower() != "risolto":
            sent_tickets[ticket_id] = False
            send_message(f"🆕 Nuovo ticket #{ticket_id}\n{subject}\n{link}")
            Timer(FIRST_REMINDER_AFTER, send_reminder, args=[ticket_id, subject, link]).start()

# Funzione promemoria periodico
def send_reminder(ticket_id, subject, link):
    if sent_tickets.get(ticket_id) is False:
        send_message(f"⏰ Promemoria: il ticket #{ticket_id} non è stato risolto.\n{subject}\n{link}")
        Timer(REMINDER_INTERVAL, send_reminder, args=[ticket_id, subject, link]).start()

# Main loop
def main():
    send_message("✅ Bot avviato con successo e in ascolto.")
    while True:
        try:
            check_new_tickets()
        except Exception as e:
            send_message(f"⚠️ Errore durante il controllo ticket:\n{e}")
        time.sleep(TICKET_CHECK_INTERVAL)

if __name__ == "__main__":
    main()
