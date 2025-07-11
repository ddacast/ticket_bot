import os
import time
import requests
from bs4 import BeautifulSoup

# Recupera le variabili d'ambiente
def get_env_var(key):
    value = os.environ.get(key)
    if not value:
        print(f"❌ Variabile d'ambiente mancante: {key}")
        exit(1)
    return value

# Config
TOKEN = get_env_var("BOT_TOKEN")
CHAT_ID = get_env_var("CHAT_ID")
USERNAME = get_env_var("USERNAME")
PASSWORD = get_env_var("PASSWORD")
LOGIN_URL = get_env_var("LOGIN_URL")  # https://ynap.kappa3.app/login
DETAIL_BASE_URL = get_env_var("DETAIL_BASE_URL")  # https://ynap.kappa3.app/home/ticketing/ticket/detail?id=

CHECK_INTERVAL = 60  # secondi
REMINDER_INTERVAL = 900  # 15 minuti

# Salva i ticket non risolti per reminder
unresolved = {}

# Invia messaggio Telegram
def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": text})

# Estrai e invia dettagli ticket
def check_ticket(session, ticket_id):
    url = f"{DETAIL_BASE_URL}{ticket_id}"
    resp = session.get(url)

    if resp.status_code != 200:
        return False  # Ticket non esiste

    soup = BeautifulSoup(resp.text, "html.parser")
    titolo = soup.select_one("div.card-body h5")
    stato = soup.find(string="Stato:")  # cerca label
    if not titolo or not stato:
        return False

    stato_text = stato.find_parent().text.strip().lower()
    if "risolto" in stato_text:
        return True

    # Estrai info
    subject = titolo.text.strip()
    text = f"🆕 Ticket #{ticket_id}\n📌 {subject}\n🔗 {url}"
    send_message(text)
    unresolved[ticket_id] = {"subject": subject, "url": url, "time": time.time()}
    return True

# Promemoria per i ticket non risolti
def send_reminders():
    now = time.time()
    for tid, data in unresolved.items():
        if now - data["time"] > REMINDER_INTERVAL:
            send_message(f"⏰ Promemoria: il ticket #{tid} non è ancora risolto.\n{data['subject']}\n{data['url']}")
            data["time"] = now

# Loop principale
def main():
    session = requests.Session()
    session.post(LOGIN_URL, data={"username": USERNAME, "password": PASSWORD})

    send_message("✅ Bot partito, controllo ticket per ID incrementale...")

    last_checked_id = int(os.environ.get("START_ID", "21950"))

    while True:
        try:
            found = check_ticket(session, last_checked_id)
            if found:
                last_checked_id += 1
            else:
                # Se non esiste o non valido, riprova tra un po'
                time.sleep(CHECK_INTERVAL)

            send_reminders()
        except Exception as e:
            send_message(f"⚠️ Errore: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
