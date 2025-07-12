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
FIRST_REMINDER_AFTER = 60  # 1 minuto
REMINDER_INTERVAL = 60  # 1 minuto

sent_tickets = {}
pending_reminders = {}

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": text})
    except Exception as e:
        print(f"[ERROR] Telegram: {e}")

def parse_ticket_detail(html):
    soup = BeautifulSoup(html, "html.parser")
    details = {
        "area": "Non disponibile",
        "priorità": "Non disponibile",
        "stato": "Non disponibile",
        "agente": "Non disponibile",
        "macchina": "Non disponibile",
        "stato_attuale": "Non disponibile"
    }

    for row in soup.find_all("div", class_="row listdetail"):
        label_div = row.find("div", class_="col-md-5") or row.find("div", class_="col-md-6")
        value_div = row.find("div", class_="col-md-7") or row.find("div", class_="col-md-6")
        if not label_div or not value_div:
            continue
        label = label_div.get_text(strip=True).lower()

        if "area" in label:
            details["area"] = value_div.get_text(strip=True)
        elif "priorit" in label:
            selected = value_div.find("option", selected=True)
            details["priorità"] = selected.text.strip() if selected else value_div.get_text(strip=True)
        elif "stato" in label:
            selected = value_div.find("option", selected=True)
            stato = selected.text.strip() if selected else value_div.get_text(strip=True)
            details["stato"] = stato
            details["stato_attuale"] = stato
        elif "agente" in label:
            selected = value_div.find("option", selected=True)
            details["agente"] = selected.text.strip() if selected else value_div.get_text(strip=True)
        elif "macchina" in label:
            selected = value_div.find("option", selected=True)
            details["macchina"] = selected.text.strip() if selected else value_div.get_text(strip=True)

    return details

def check_ticket(session, ticket_id):
    print(f"\n[INFO] Controllo ticket ID: {ticket_id}")
    print(f"[DEBUG] Lista ticket già notificati: {list(sent_tickets.keys())}")
    url = DETAIL_URL + str(ticket_id)
    print(f"[DEBUG] URL: {url}")
    try:
        response = session.get(url)
        print(f"[DEBUG] Status Code: {response.status_code}")
        print(f"[DEBUG] Response length: {len(response.text)}")

        if response.status_code != 200 or "Dettagli" not in response.text:
            print(f"[{ticket_id}] ❌ Ticket non valido o non trovato.")
            return False

        details = parse_ticket_detail(response.text)
        print(f"[DEBUG] Estratti dettagli: {details}")

        stato = details["stato_attuale"].lower()
        if "risolto" in stato or "chiuso" in stato:
            print(f"[{ticket_id}] ✅ Ticket risolto o chiuso.")
            if ticket_id in pending_reminders:
                pending_reminders[ticket_id].cancel()
                del pending_reminders[ticket_id]
                send_message(f"🛑 Ticket #{ticket_id} passato a '{stato}'. Promemoria annullato: il ticket ha ricevuto risposta.")
            return False

        subject = f"📌 Ticket #{ticket_id}"
        link = url
        message = f"{subject}\nArea: {details['area']}\nPriorità: {details['priorità']}\nStato: {details['stato']}\nAgente: {details['agente']}\nMacchina: {details['macchina']}\n🔗 {link}"

        stato_prec = sent_tickets.get(ticket_id)
        sent_tickets[ticket_id] = stato

        if stato != "nuovo":
            print(f"[{ticket_id}] ⏩ Ticket non nuovo: stato = {stato}. Nessuna notifica inviata.")
            if stato_prec == "nuovo":
                send_message(f"🛑 Ticket #{ticket_id} passato da 'nuovo' a '{stato}'. Promemoria disattivato.")
            if ticket_id in pending_reminders:
                pending_reminders[ticket_id].cancel()
                del pending_reminders[ticket_id]
            return True

        if stato_prec != "nuovo":
            print(f"[DEBUG] Ticket {ticket_id} è tornato a 'nuovo'. Invio nuova notifica.")
            send_message(message)
            timer = Timer(FIRST_REMINDER_AFTER, send_reminder, args=[ticket_id, message])
            timer.start()
            pending_reminders[ticket_id] = timer
        elif stato_prec is None:
            print(f"[DEBUG] Nuovo ticket trovato, ID: {ticket_id}, non ancora notificato.")
            send_message(message)
            print(f"[{ticket_id}] ⏰ Ticket in attesa, promemoria programmato.")
            timer = Timer(FIRST_REMINDER_AFTER, send_reminder, args=[ticket_id, message])
            timer.start()
            pending_reminders[ticket_id] = timer
        else:
            print(f"[DEBUG] Ticket già notificato e ancora in stato 'nuovo': {ticket_id}")

        return True

    except Exception as e:
        print(f"[ERROR] ticket {ticket_id}: {e}")
        return False

def send_reminder(ticket_id, message):
    stato_corrente = sent_tickets.get(ticket_id)
    if stato_corrente and stato_corrente == "nuovo":
        send_message(f"🔔 Promemoria ticket #{ticket_id} ancora da prendere in carico.\n{message}")
        timer = Timer(REMINDER_INTERVAL, send_reminder, args=[ticket_id, message])
        timer.start()
        pending_reminders[ticket_id] = timer

def is_already_running():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", 65432))  # Porta libera
        return False
    except socket.error:
        return True

def main():
    if is_already_running():
        print("\n⚠️ Il bot è già in esecuzione. Uscita.\n")
        return

    import os
    print(f"[DEBUG] Process PID: {os.getpid()}")
    print("\n🤖 Bot avviato e in ascolto...\n")
    send_message("🤖 Bot avviato e in ascolto...")

    session = requests.Session()
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

    current_id = 21958

    while True:
        success = check_ticket(session, current_id)
        if success:
            current_id += 1
        else:
            print(f"[INFO] Ticket {current_id} non trovato, rimanendo su questo ID...")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
