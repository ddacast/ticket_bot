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

LOGIN_URL = "https://ynap.kappa3.app/home/user/sign-in/login"
DETAIL_URL = "https://ynap.kappa3.app/home/ticketing/ticket/detail?id="

TICKET_CHECK_INTERVAL = 60
FIRST_REMINDER_AFTER = 60
REMINDER_INTERVAL = 60

ticket_status = {}
reminder_timers = {}
session = requests.Session()

last_checked_id = 21900  # puoi partire da un ID vicino all’ultimo ticket noto


def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        response = session.post(url, data={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        })
        print(f"[DEBUG] INVIO ➜ chat_id: {chat_id}, status: {response.status_code}")
    except Exception as e:
        print(f"[ERROR] Telegram: {e}")


def login():
    try:
        # STEP 1: prendi la pagina login per estrarre il CSRF token
        login_page = session.get(LOGIN_URL)
        soup = BeautifulSoup(login_page.text, "html.parser")
        csrf_token = soup.find("input", {"name": "_csrf"})["value"]

        # STEP 2: invia la POST con tutti i campi
        payload = {
            "_csrf": csrf_token,
            "LoginForm[identity]": USERNAME,
            "LoginForm[password]": PASSWORD,
            "LoginForm[rememberMe]": "1"
        }

        headers = {
            "Referer": LOGIN_URL,
            "Origin": "https://ynap.kappa3.app"
        }

        response = session.post(LOGIN_URL, data=payload, headers=headers)

        print(f"[DEBUG] Login status: {response.status_code}")

        if "logout" in response.text.lower() or "dashboard" in response.text.lower():
            return True
        else:
            print("[ERROR] Login non riuscito: token o credenziali sbagliate?")
            return False

    except Exception as e:
        print(f"[ERROR] Login fallito: {e}")
        return False


def parse_ticket(ticket_id):
    url = f"{DETAIL_URL}{ticket_id}"
    response = session.get(url)

    if response.status_code != 200:
        print(f"[DEBUG] Ticket {ticket_id} non trovato (status {response.status_code})")
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    subject_tag = soup.select_one("h5")
    subject = subject_tag.text.strip() if subject_tag else f"Ticket #{ticket_id}"

    stato = "non trovato"
    for strong in soup.find_all("strong"):
        if "stato" in strong.text.lower():
            stato_tag = strong.find_next()
            stato = stato_tag.text.strip().lower() if stato_tag else "non trovato"
            break

    print(f"[DEBUG] Ticket {ticket_id} ➜ stato: '{stato}'")

    return {
        "id": ticket_id,
        "subject": subject,
        "stato": stato,
        "link": url
    }


def check_ticket(data):
    ticket_id = data["id"]
    stato = data["stato"]
    subject = data["subject"].replace("*", "").replace("_", "")
    link = data["link"]

    old_entry = ticket_status.get(ticket_id, {})
    old_stato = old_entry.get("stato")
    was_notified = old_entry.get("notificato", False)

    ticket_status[ticket_id] = {"stato": stato, "notificato": was_notified}

    if old_stato and old_stato != stato:
        send_message(f"🔄 Ticket #{ticket_id} cambiato da *{old_stato}* a *{stato}*")

    if stato == "nuovo" and not was_notified:
        send_message(f"🆕 Ticket #{ticket_id} è in stato *nuovo*\n_{subject}_\n🔗 {link}")
        ticket_status[ticket_id]["notificato"] = True
        if ticket_id not in reminder_timers:
            start_reminder(ticket_id, subject, link)

    if stato != "nuovo" and ticket_id in reminder_timers:
        reminder_timers[ticket_id].cancel()
        del reminder_timers[ticket_id]
        ticket_status[ticket_id]["notificato"] = False


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
    global last_checked_id

    print("🤖 Avvio bot con login e monitoraggio ticket...")
    send_message("📡 *Bot attivo con ricerca automatica dei ticket*")

    if not login():
        send_message("❌ *Login fallito!* Controlla le credenziali in Railway.")
        return

    send_message("✅ *Login riuscito!* Inizio monitoraggio...")

    while True:
        try:
            for ticket_id in range(last_checked_id, last_checked_id + 100):
                data = parse_ticket(ticket_id)
                if data:
                    check_ticket(data)
            last_checked_id += 100
        except Exception as e:
            send_message(f"❌ Errore:\n`{str(e)}`")

        time.sleep(TICKET_CHECK_INTERVAL)


if __name__ == "__main__":
    main()
