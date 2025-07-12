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

# Variabili d'ambiente
TOKEN = get_env_var("BOT_TOKEN")
CHAT_ID = get_env_var("CHAT_ID")
LOGIN_USERNAME = get_env_var("USERNAME")
LOGIN_PASSWORD = get_env_var("PASSWORD")
LOGIN_URL = get_env_var("LOGIN_URL")
DETAIL_URL = get_env_var("DETAIL_URL")  # es: https://ynap.kappa3.app/home/ticketing/ticket/detail?id=

# Impostazioni
TICKET_CHECK_INTERVAL = 60  # secondi
REMINDER_INTERVAL = 60
FIRST_REMINDER_AFTER = 900

sent_tickets = {}
current_id = int(os.environ.get("START_ID", 21954))

# Telegram

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": text})
    except Exception as e:
        print(f"[ERROR] Invio messaggio Telegram: {e}")

# Login

def login():
    session = requests.Session()
    session.post(LOGIN_URL, data={
        "username": LOGIN_USERNAME,
        "password": LOGIN_PASSWORD
    })
    return session

# Parsing dettagli ticket

def parse_ticket_details(soup):
    def estrai_dropdown_valore(id_):
        dropdown = soup.select_one(f'select#{id_} option[selected]')
        return dropdown.text.strip() if dropdown else "Non disponibile"

    def estrai_testuale(etichetta):
        rows = soup.select("div.row.listdetail")
        for row in rows:
            label = row.select_one("div.col-md-5")
            value = row.select_one("div.col-md-7")
            if label and etichetta.lower() in label.text.lower():
                return value.text.strip() if value else "Non disponibile"
        return "Non disponibile"

    area = estrai_testuale("Area")
    priorita = estrai_dropdown_valore("ch_priority")
    stato = estrai_dropdown_valore("ch_status")
    agente = estrai_dropdown_valore("ch_agent")
    macchina = estrai_dropdown_valore("ch_device")

    return area, priorita, stato, agente, macchina

# Controllo ticket

def check_ticket(session, ticket_id):
    url = f"{DETAIL_URL}{ticket_id}"
    print(f"[INFO] Controllo ticket ID: {ticket_id}")
    print(f"[DEBUG] URL: {url}")

    try:
        response = session.get(url)
        print(f"[DEBUG] Status Code: {response.status_code}")
        if response.status_code != 200:
            return False

        soup = BeautifulSoup(response.text, "html.parser")
        area, priorita, stato, agente, macchina = parse_ticket_details(soup)

        print(f"[DEBUG] Estratti dettagli: area={area}, priorita={priorita}, stato={stato}, agente={agente}, macchina={macchina}")

        if stato.lower() in ["risolto", "chiuso"]:
            return False

        if stato.lower() not in ["nuovo", "in lavorazione"]:
            print(f"[{ticket_id}] ⚠️ Ticket ignorato (stato non gestito)")
            return False

        if ticket_id not in sent_tickets:
            link = f"{DETAIL_URL}{ticket_id}"
            msg = f"🆕 Nuovo Ticket #{ticket_id}\nArea: {area}\nPriorità: {priorita}\nStato: {stato}\nAgente: {agente}\nMacchina: {macchina}\n{link}"
            send_message(msg)
            sent_tickets[ticket_id] = False
            Timer(FIRST_REMINDER_AFTER, send_reminder, args=[ticket_id, msg]).start()
            return True

    except Exception as e:
        print(f"[DEBUG] Errore parsing dettagli: {e}")
        print(f"[{ticket_id}] ⚠️ Ticket ignorato (risolto/chiuso o parsing fallito)")

    return False

# Promemoria

def send_reminder(ticket_id, msg):
    if sent_tickets.get(ticket_id) is False:
        send_message(f"⏰ Promemoria: il ticket #{ticket_id} non risulta ancora risolto.\n{msg}")
        Timer(REMINDER_INTERVAL, send_reminder, args=[ticket_id, msg]).start()

# Main loop

def main():
    global current_id
    send_message("🤖 Bot avviato e in ascolto...")
    session = login()

    while True:
        check_ticket(session, current_id)
        current_id += 1
        time.sleep(TICKET_CHECK_INTERVAL)

if __name__ == "__main__":
    main()
