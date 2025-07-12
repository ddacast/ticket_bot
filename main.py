import time
import os
import requests
from bs4 import BeautifulSoup
from threading import Timer

# Config
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
USERNAME = os.environ.get("USERNAME")
PASSWORD = os.environ.get("PASSWORD")
LOGIN_URL = os.environ.get("LOGIN_URL")
DETAIL_URL = "https://ynap.kappa3.app/home/ticketing/ticket/detail?id="

# Intervalli
CHECK_INTERVAL = 60  # ogni 60 secondi
FIRST_REMINDER_AFTER = 900  # 15 minuti
REMINDER_INTERVAL = 600  # 10 minuti

sent_tickets = {}

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": text})
    except Exception as e:
        print(f"[ERROR] Telegram: {e}")

def parse_ticket_detail(html):
    soup = BeautifulSoup(html, "html.parser")
    details = {}

    def get_detail(label):
        tag = soup.find("div", string=lambda s: s and label in s)
        if tag:
            sibling = tag.find_next_sibling("div")
            return sibling.text.strip() if sibling else "Non disponibile"
        return "Non disponibile"

    details["area"] = get_detail("Area")
    details["priorità"] = get_detail("Priority")
    details["stato"] = get_detail("Stato")
    details["agente"] = get_detail("Agente")
    details["macchina"] = get_detail("Macchina")

    details["stato_attuale"] = details["stato"]

    return details

def check_ticket(session, ticket_id):
    print(f"\n[INFO] Controllo ticket ID: {ticket_id}")
    url = DETAIL_URL + str(ticket_id)
    print(f"[DEBUG] URL: {url}")
    try:
        response = session.get(url)
        print(f"[DEBUG] Status Code: {response.status_code}")
        print(f"[DEBUG] Response length: {len(response.text)}")

        if response.status_code != 200 or "Dettagli" not in response.text:
            print(f"[{ticket_id}] ❌ Ticket non valido o non trovato.")
            return

        details = parse_ticket_detail(response.text)
        print(f"[DEBUG] Estratti dettagli: {details}")

        stato = details["stato_attuale"].lower()
        if "risolto" in stato or "chiuso" in stato:
            print(f"[{ticket_id}] ✅ Ticket risolto o chiuso.")
            return

        subject = f"📌 Ticket #{ticket_id}"
        link = url
        message = f"{subject}\nArea: {details['area']}\nPriorità: {details['priorità']}\nStato: {details['stato']}\nAgente: {details['agente']}\nMacchina: {details['macchina']}\n🔗 {link}"

        send_message(message)
        sent_tickets[ticket_id] = stato

        if stato == "nuovo":
            print(f"[{ticket_id}] ⏰ Ticket in attesa, promemoria programmato.")
            Timer(FIRST_REMINDER_AFTER, send_reminder, args=[ticket_id, message]).start()

    except Exception as e:
        print(f"[ERROR] ticket {ticket_id}: {e}")

def send_reminder(ticket_id, message):
    stato_corrente = sent_tickets.get(ticket_id)
    if stato_corrente and stato_corrente == "nuovo":
        send_message(f"🔔 Promemoria ticket #{ticket_id} ancora da prendere in carico.\n{message}")
        Timer(REMINDER_INTERVAL, send_reminder, args=[ticket_id, message]).start()

def main():
    print("\n🤖 Bot avviato e in ascolto...\n")
    send_message("🤖 Bot avviato e in ascolto...")

    session = requests.Session()

    # Prima richiesta per ottenere il token CSRF
    login_page = session.get(LOGIN_URL)
    soup = BeautifulSoup(login_page.text, "html.parser")
    csrf = soup.find("input", {"name": "_csrf"})
    csrf_token = csrf["value"] if csrf else ""

    payload = {
        "_csrf": csrf_token,
        "LoginForm[identity]": USERNAME,
        "LoginForm[password]": PASSWORD,
        "LoginForm[rememberMe]": "1",
        "login-button": "Login"
    }

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": LOGIN_URL
    }

    login_response = session.post(LOGIN_URL, data=payload, headers=headers, allow_redirects=False)
    print(f"[DEBUG] Login status code: {login_response.status_code}")
    redirect_location = login_response.headers.get("Location", "")
    print(f"[DEBUG] Redirected to: {redirect_location}")

    login_successful = "/home" in redirect_location and "/sign-in" not in redirect_location
    print(f"[DEBUG] Login successful: {login_successful}")

    if not login_successful:
        print("[ERROR] Login fallito. Controlla credenziali o URL di login.")
        return

    current_id = int(os.environ.get("START_ID", 21900))

    while True:
        check_ticket(session, current_id)
        current_id += 1
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
