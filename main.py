import time
import os
import requests
from bs4 import BeautifulSoup
from threading import Timer

# === CONFIG ===
TOKEN = os.environ["BOT_TOKEN"]
chat_id = os.environ["CHAT_ID"]

USERNAME = os.environ["LOGIN_USERNAME"]
PASSWORD = os.environ["LOGIN_PASSWORD"]

LOGIN_URL = https://ynap.kappa3.app/home/user/sign-in/logins
TICKETING_URL = "https://ynap.kappa3.app/home/ticketing"

TICKET_CHECK_INTERVAL = 60
FIRST_REMINDER_AFTER = 60
REMINDER_INTERVAL = 60

ticket_status = {}
reminder_timers = {}

session = requests.Session()


def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        response = session.post(url, data={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        })
        print(f"[DEBUG] INVIO ➜ chat_id: {chat_id}, status: {response.status_code}, response: {response.text}")
    except Exception as e:
        print(f"[ERROR] Errore invio messaggio Telegram: {e}")


def login():
    try:
        response = session.post(LOGIN_URL, data={
            "username": USERNAME,
            "password": PASSWORD
        })
        print(f"[DEBUG] Login status: {response.status_code}")
        if "incorrect" in response.text.lower():
            print("[ERROR] Login fallito: credenziali errate?")
        return response.status_code == 200
    except Exception as e:
        print(f"[ERROR] Login fallito: {e}")
        return False


def get_tickets():
    response = session.get(TICKETING_URL)
    soup = BeautifulSoup(response.text, "html.parser")

    with open("pagina.html", "w", encoding="utf-8") as f:
        f.write(response.text)

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

        print(f"[DEBUG] TICKET ➜ ID={ticket_id}, stato='{stato}', subject='{subject}'")

        tickets[int(ticket_id)] = {
            "subject": subject,
            "link": link,
            "stato": stato
        }

    print(f"[DEBUG] Totale ticket trovati: {len(tickets)}")
    return tickets


def check_ticket(ticket_id, data):
    stato = data["stato"].strip().lower()
    subject = data["subject"].replace("*", "").replace("_", "")
    link = data["link"]

    old_entry = ticket_status.get(ticket_id, {})
    old_stato = old_entry.get("stato")
    was_notified = old_entry.get("notificato", False)

    print(f"\n[DEBUG] Analizzo ticket #{ticket_id}")
    print(f"        Stato attuale:    '{stato}'")
    print(f"        Stato precedente: '{old_stato}'")
    print(f"        Già notificato?:  {was_notified}")

    ticket_status[ticket_id] = {"stato": stato, "notificato": was_notified}

    if old_stato and old_stato != stato:
        send_message(f"🔄 Ticket #{ticket_id} cambiato da *{old_stato}* a *{stato}*")

    if stato == "nuovo":
        send_message(f"🆕 Ticket #{ticket_id} è in stato *nuovo*\n_{subject}_\n🔗 {link}")
        ticket_status[ticket_id]["notificato"] = True

        if ticket_id not in reminder_timers:
            start_reminder(ticket_id, subject, link)

    if stato != "nuovo" and ticket_id in reminder_timers:
        reminder_timers[ticket_id].cancel()
        del reminder_timers[ticket_id]
        ticket_status[ticket_id]["notificato"] = False
        print(f"[INFO] Reminder disattivato per ticket {ticket_id}")


def start_reminder(ticket_id, subject, link):
    def send():
        stato_attuale = ticket_status.get(ticket_id, {}).get("stato")
        if stato_attuale == "nuovo":
            send_message(f"⏰ Ticket #{ticket_id} è ancora *nuovo*\n_{subject}_\n🔗 {link}")
            t = Timer(REMINDER_INTERVAL, send)
            t.start()
            reminder_timers[ticket_id] = t
        else:
            print(f"[INFO] Ticket {ticket_id} non è più nuovo. Reminder fermato.")

    t = Timer(FIRST_REMINDER_AFTER, send)
    t.start()
    reminder_timers[ticket_id] = t


def main():
    print("🤖 Avvio bot con login...\n")
    send_message("📡 *Avvio monitoraggio ticket...*")

    if not login():
        send_message("❌ *Login fallito!* Controlla le credenziali.")
        return

    send_message("✅ *Login riuscito! Monitoraggio attivo.*")

    while True:
        try:
            tickets = get_tickets()
            for ticket_id, data in tickets.items():
                check_ticket(ticket_id, data)
        except Exception as e:
            send_message(f"❌ Errore nel ciclo:\n`{str(e)}`")
        time.sleep(TICKET_CHECK_INTERVAL)


if __name__ == "__main__":
    main()
