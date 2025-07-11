
import time
import requests
from bs4 import BeautifulSoup
from threading import Timer

TOKEN = "7849103119:AAErLG-ekv-a3VEoMGtwzsqWcd_G8vMyaAw"
CHAT_ID = "7900732843"

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
    # Inserire qui le credenziali se richiesto login
    # session.post("https://ynap.kappa3.app/login", data={"username": "...", "password": "..."})

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
