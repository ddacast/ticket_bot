import time
import os
import requests
from bs4 import BeautifulSoup
import json
import fcntl

# Config
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
USERNAME = os.environ.get("USERNAME")
PASSWORD = os.environ.get("PASSWORD")
LOGIN_URL = os.environ.get("LOGIN_URL")
DETAIL_URL = "https://ynap.kappa3.app/home/ticketing/ticket/detail?id="

# Intervalli
CHECK_INTERVAL = 60  # ogni 60 secondi
STATUS_LOG_FILE = "ticket_status_log.json"
CHECK_RANGE = 100
LOCK_FILE = "/tmp/ticket_bot.lock"


def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": text})
    except Exception as e:
        print(f"[ERROR] Telegram: {e}")


def load_status_log():
    if os.path.exists(STATUS_LOG_FILE):
        with open(STATUS_LOG_FILE, "r") as f:
            return json.load(f)
    return {}


def save_status_log(data):
    with open(STATUS_LOG_FILE, "w") as f:
        json.dump(data, f)


def create_lock_file():
    global lock_fp
    try:
        lock_fp = open(LOCK_FILE, "w")
        fcntl.lockf(lock_fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        print("\n⚠️ Il bot è già in esecuzione (lock file attivo).\n")
        exit(1)


def remove_lock_file():
    global lock_fp
    try:
        fcntl.lockf(lock_fp, fcntl.LOCK_UN)
        lock_fp.close()
        os.remove(LOCK_FILE)
    except:
        pass


status_log = load_status_log()


def get_ticket_state(html):
    soup = BeautifulSoup(html, "html.parser")
    stato = "non disponibile"
    for row in soup.find_all("div", class_="row listdetail"):
        label_div = row.find("div", class_="col-md-5") or row.find("div", class_="col-md-6")
        value_div = row.find("div", class_="col-md-7") or row.find("div", class_="col-md-6")
        if not label_div or not value_div:
            continue
        label = label_div.get_text(strip=True).lower()
        if "stato" in label:
            selected = value_div.find("option", selected=True)
            stato = selected.text.strip().lower() if selected else value_div.get_text(strip=True).lower()
            break
    return stato


def parse_full_details(html):
    soup = BeautifulSoup(html, "html.parser")
    details = {
        "area": "Non disponibile",
        "priorità": "Non disponibile",
        "stato": "Non disponibile",
        "agente": "Non disponibile",
        "macchina": "Non disponibile"
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
        elif "agente" in label:
            selected = value_div.find("option", selected=True)
            details["agente"] = selected.text.strip() if selected else value_div.get_text(strip=True)
        elif "macchina" in label:
            selected = value_div.find("option", selected=True)
            details["macchina"] = selected.text.strip() if selected else value_div.get_text(strip=True)

    return details


def check_ticket(session, ticket_id):
    print(f"\n[INFO] Controllo ticket ID: {ticket_id}")
    url = DETAIL_URL + str(ticket_id)
    try:
        response = session.get(url)
        if response.status_code != 200 or "Dettagli" not in response.text:
            print(f"[{ticket_id}] ❌ Ticket non valido o non trovato.")
            return False

        stato = get_ticket_state(response.text)
        stato_prec = status_log.get(str(ticket_id), "")

        if stato != stato_prec:
            print(f"[DEBUG] Stato del ticket {ticket_id} cambiato da '{stato_prec}' a '{stato}'")
            if stato_prec:
                send_message(f"ℹ️ Ticket #{ticket_id} passato da '{stato_prec}' a '{stato}'")
            status_log[str(ticket_id)] = stato
            save_status_log(status_log)

        if stato == "nuovo" and stato_prec != "nuovo":
            details = parse_full_details(response.text)
            subject = f"📌 Ticket #{ticket_id}"
            message = (
                f"{subject}\n"
                f"Area: {details['area']}\n"
                f"Priorità: {details['priorità']}\n"
                f"Stato: {details['stato']}\n"
                f"Agente: {details['agente']}\n"
                f"Macchina: {details['macchina']}\n"
                f"🔗 {url}"
            )
            send_message(message)

        return True

    except Exception as e:
        print(f"[ERROR] ticket {ticket_id}: {e}")
        return False


def main():
    create_lock_file()
    try:
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
            for tid in range(current_id - CHECK_RANGE, current_id + 1):
                check_ticket(session, tid)
            current_id += 1
            time.sleep(CHECK_INTERVAL)

    finally:
        remove_lock_file()


if __name__ == "__main__":
    main()
