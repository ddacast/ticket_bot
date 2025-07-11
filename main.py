import time
import requests
import os
from bs4 import BeautifulSoup
from threading import Timer

# Recupera token e chat ID dalle variabili ambiente
TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
LOGIN_USERNAME = os.environ["LOGIN_USERNAME"]
LOGIN_PASSWORD = os.environ["LOGIN_PASSWORD"]

sent_tickets = {}
TICKET_CHECK_INTERVAL = 60  # secondi
REMINDER_INTERVAL = 60      # secondi
FIRST_REMINDER_AFTER = 900  # 15 minuti

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": text})

def check_new_tickets():
    url = "https://ynap.kappa3.app/home/ticketing"
    session = requests.Session()

    # Effettua login
    login_url = "https://ynap.kappa3.app/login"
    session.post(login_url, data={
        "username": LOGIN_USERNAME,
        "password": LOGIN_PASSWORD
    })

    response = session.get(url)
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

def send_reminder(ticket_id, subject, link):
    if sent_tickets.get(ticket_id) is False:
        send_message(f"⏰ Promemoria: il ticket #{ticket_id} non è stato risolto.\n{subject}\n{link}")
        Timer(REMINDER_INTERVAL, send_reminder, args=[ticket_id, subject, link]).start()

def main():
    while True:
        try:
            check_new_tickets()
        except Exception as e:
            send_message(f"Errore: {e}")
        time.sleep(TICKET_CHECK_INTERVAL)

if __name__ == "__main__":
    main()
