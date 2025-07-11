import time
import requests
import os
from bs4 import BeautifulSoup

# Recupera e verifica le variabili d'ambiente
def get_env_var(key):
    value = os.environ.get(key)
    if not value:
        print(f"❌ Variabile d'ambiente mancante: {key}")
        exit(1)
    return value

# Variabili d’ambiente
BOT_TOKEN = get_env_var("BOT_TOKEN")
CHAT_ID = get_env_var("CHAT_ID")
LOGIN_USERNAME = get_env_var("USERNAME")
LOGIN_PASSWORD = get_env_var("PASSWORD")
LOGIN_URL = get_env_var("LOGIN_URL")
TICKET_BASE_URL = "https://ynap.kappa3.app/home/ticketing/ticket/detail?id="

# Inizio da ID (da modificare se necessario)
current_id = 21954

# Funzione invio messaggi Telegram
def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": text})
    except Exception as e:
        print(f"[ERROR] Telegram message failed: {e}")

# Funzione parsing ticket
def parse_ticket(html):
    soup = BeautifulSoup(html, "html.parser")
    get_right = lambda icon: soup.find("i", class_=icon).find_parent().find_next_sibling().text.strip()

    try:
        area = get_right("fa-briefcase")
        priority = soup.find("select", {"id": "ch_priority"}).find("option", selected=True).text.strip()
        status = soup.find("select", {"id": "ch_status"}).find("option", selected=True).text.strip()
        agent = soup.find("select", {"id": "ch_agent"}).find("option", selected=True).text.strip()
        machine = soup.find("select", {"id": "ch_device"}).find("option", selected=True).text.strip()
    except Exception as e:
        print(f"[DEBUG] Errore parsing dettagli: {e}")
        return None

    return {
        "area": area,
        "priority": priority,
        "status": status,
        "agent": agent,
        "machine": machine
    }

# Funzione principale
def main():
    print("🤖 Bot avviato e in ascolto...")

    session = requests.Session()
    session.post(LOGIN_URL, data={"username": LOGIN_USERNAME, "password": LOGIN_PASSWORD})

    global current_id
    while True:
        print(f"\n[INFO] Controllo ticket ID: {current_id}")
        url = f"{TICKET_BASE_URL}{current_id}"
        print(f"[DEBUG] URL: {url}")
        try:
            r = session.get(url)
            print(f"[DEBUG] Status Code: {r.status_code}")
            if r.status_code == 200:
                data = parse_ticket(r.text)
                if data and data["status"].lower() not in ["risolto", "chiuso"]:
                    msg = (
                        f"🆕 Ticket #{current_id}\n"
                        f"🔹 Area: {data['area']}\n"
                        f"🔸 Priorità: {data['priority']}\n"
                        f"📌 Stato: {data['status']}\n"
                        f"👤 Agente: {data['agent']}\n"
                        f"🖥️ Macchina: {data['machine']}\n"
                        f"🔗 {url}"
                    )
                    send_message(msg)
                else:
                    print(f"[{current_id}] ⚠️ Ticket ignorato (risolto/chiuso o parsing fallito)")
            else:
                print(f"[{current_id}] ⚠️ Ticket non esistente o accesso negato")
        except Exception as e:
            print(f"[ERROR] Errore durante richiesta per ticket {current_id}: {e}")

        current_id += 1
        time.sleep(5)  # Evita flood, puoi aumentare

if __name__ == "__main__":
    main()
