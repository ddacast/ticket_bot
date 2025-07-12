import os
import time
import requests
from bs4 import BeautifulSoup

TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
LOGIN_USERNAME = os.environ["LOGIN_USERNAME"]
LOGIN_PASSWORD = os.environ["LOGIN_PASSWORD"]

LOGIN_URL = "https://ynap.kappa3.app/login"
BASE_URL = "https://ynap.kappa3.app/home/ticketing/ticket/detail?id="


def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        response = requests.post(url, data={"chat_id": CHAT_ID, "text": text})
        print(f"[DEBUG] Telegram response: {response.status_code}")
    except Exception as e:
        print(f"[ERROR] Telegram send failed: {e}")


def parse_ticket(html):
    soup = BeautifulSoup(html, "html.parser")

    def find_detail(label_text):
        rows = soup.select(".row.listdetail")
        for row in rows:
            label_div = row.select_one(".col-md-5")
            if label_div and label_div.text.strip().lower().startswith(label_text.lower()):
                value_div = row.select_one(".col-md-7, .col-md-6")
                if value_div:
                    select = value_div.find("select")
                    if select:
                        selected_option = select.find("option", selected=True)
                        if selected_option:
                            return selected_option.text.strip()
                    else:
                        return value_div.text.strip()
        return "Non disponibile"

    area = find_detail("Area:")
    priority = find_detail("Priority:")
    status = find_detail("Stato:")
    agent = find_detail("Agente:")
    machine = find_detail("Macchina:")

    print(f"[DEBUG] Estratti dettagli: area={area}, priorità={priority}, stato={status}, agente={agent}, macchina={machine}")

    return {
        "area": area,
        "priority": priority,
        "status": status,
        "agent": agent,
        "machine": machine
    }


def main():
    print("\n🤖 Bot avviato e in ascolto...\n")

    ticket_id = int(os.environ.get("START_ID", 1))
    consecutive_failures = 0
    max_failures = 20

    while True:
        print(f"[INFO] Controllo ticket ID: {ticket_id}")
        url = BASE_URL + str(ticket_id)
        print(f"[DEBUG] URL: {url}")

        try:
            session = requests.Session()
            login_payload = {"username": LOGIN_USERNAME, "password": LOGIN_PASSWORD}
            session.post(LOGIN_URL, data=login_payload)

            res = session.get(url)
            print(f"[DEBUG] Status Code: {res.status_code}")

            if res.status_code == 200:
                parsed = parse_ticket(res.text)
                if parsed["status"] in ["Risolto", "Chiuso"] or parsed["status"] == "Non disponibile":
                    print(f"[{ticket_id}] ⚠️ Ticket ignorato (risolto/chiuso o parsing fallito)\n")
                    consecutive_failures += 1
                else:
                    msg = (
                        f"📩 Ticket #{ticket_id}\n"
                        f"📍 Area: {parsed['area']}\n"
                        f"⚙️ Macchina: {parsed['machine']}\n"
                        f"👤 Agente: {parsed['agent']}\n"
                        f"🚦 Stato: {parsed['status']}\n"
                        f"❗ Priorità: {parsed['priority']}\n"
                        f"🔗 {url}"
                    )
                    send_message(msg)
                    consecutive_failures = 0
            else:
                print(f"[DEBUG] Ticket {ticket_id} non trovato (HTTP {res.status_code})\n")
                consecutive_failures += 1

        except Exception as e:
            print(f"[ERROR] Errore durante il controllo del ticket {ticket_id}: {e}")
            consecutive_failures += 1

        if consecutive_failures >= max_failures:
            print(f"[STOP] Raggiunto limite massimo di {max_failures} fallimenti consecutivi. Termino.")
            break

        ticket_id += 1
        time.sleep(1)


if __name__ == "__main__":
    main()
