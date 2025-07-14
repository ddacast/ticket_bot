import time
import requests
from bs4 import BeautifulSoup
from threading import Timer

# Configurazione
TOKEN = "7849103119:AAErLG-ekv-a3VEoMGtwzsqWcd_G8vMyaAw"
CHAT_ID = ["1357205243"]  # Aggiungi qui gli altri chat_id

TICKET_CHECK_INTERVAL = 60  # ogni 60 secondi
FIRST_REMINDER_AFTER = 60   # primo promemoria dopo 1 minuto
REMINDER_INTERVAL = 60      # promemoria ogni 1 minuto

# Stato dei ticket
ticket_status = {}          # {id: {"stato": ..., "notificato": True/False}}
reminder_timers = {}        # {ticket_id: Timer()}


def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    for chat_id in CHAT_ID:
        try:
            response = requests.post(url, data={"chat_id": chat_id, "text": text})
            print(f"[DEBUG] Messaggio inviato a chat_id: {chat_id} - Status code: {response.status_code}")
        except Exception as e:
            print(f"[ERROR] Telegram (chat_id: {chat_id}): {e}")


def get_tickets():
    url = "https://ynap.kappa3.app/home/ticketing"
    session = requests.Session()
    response = session.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    tickets = {}
    for row in soup.select("table.tkt-table tr"):
        ticket_id = row.get("data-key")
        if not ticket_id or not ticket_id.isdigit():
            continue

        subject_tag = row.select_one("h5 a")
        subject = subject_tag.text.strip() if subject_tag else ""
        link = f"https://ynap.kappa3.app{subject_tag['href']}" if subject_tag else ""

        status_tag = row.select_one(".fa-ticket")
        stato = status_tag.next_sibling.strip().lower() if status_tag and status_tag.next_sibling else ""

        tickets[int(ticket_id)] = {
            "subject": subject,
            "link": link,
            "stato": stato
        }

    return tickets


def check_ticket(ticket_id, data):
    stato = data["stato"]
    subject = data["subject"]
    link = data["link"]

    old_entry = ticket_status.get(ticket_id, {})
    old_stato = old_entry.get("stato")
    was_notified = old_entry.get("notificato", False)

    # Aggiorna stato corrente
    ticket_status[ticket_id] = {"stato": stato, "notificato": was_notified}

    # Se lo stato è cambiato
    if old_stato and old_stato != stato:
        send_message(f"🔄 Ticket #{ticket_id} cambiato da *{old_stato}* a *{stato}*")

    # Ticket nuovo, mai notificato
    if stato == "nuovo" and not was_notified:
        send_message(f"🆕 Ticket #{ticket_id} è in stato *nuovo*\n{subject}\n🔗 {link}")
        ticket_status[ticket_id]["notificato"] = True
        start_reminder(ticket_id, subject, link)

    # Ticket non più nuovo → stop promemoria
    if stato != "nuovo" and ticket_id in reminder_timers:
        reminder_timers[ticket_id].cancel()
        del reminder_timers[ticket_id]
        ticket_status[ticket_id]["notificato"] = False
        print(f"[INFO] Reminder disattivato per ticket {ticket_id}")


def start_reminder(ticket_id, subject, link):
    def send():
        stato_attuale = ticket_status.get(ticket_id, {}).get("stato")
        if stato_attuale == "nuovo":
            send_message(f"⏰ Ticket #{ticket_id} è ancora *nuovo*\n{subject}\n🔗 {link}")
            t = Timer(REMINDER_INTERVAL, send)
            t.start()
            reminder_timers[ticket_id] = t
        else:
            print(f"[INFO] Il ticket {ticket_id} non è più nuovo. Stop reminder.")

    t = Timer(FIRST_REMINDER_AFTER, send)
    t.start()
    reminder_timers[ticket_id] = t


def main():
    print("🤖 Bot avviato. Controllo attivo ogni 60 secondi...\n")
    while True:
        try:
            tickets = get_tickets()
            for ticket_id, data in tickets.items():
                check_ticket(ticket_id, data)
        except Exception as e:
            send_message(f"❌ Errore nel ciclo: {e}")
        time.sleep(TICKET_CHECK_INTERVAL)


if __name__ == "__main__":
    main()
