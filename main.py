import requests
from bs4 import BeautifulSoup
import time

# === CONFIG ===
BOT_TOKEN = "7849103119:AAErLG-ekv-a3VEoMGtwzsqWcd_G8vMyaAw"
CHAT_ID = "7900732843"  # <-- Sostituisci con il tuo ID Telegram
START_ID = 21954         # Ticket iniziale da cui partire
DELAY = 60               # Ogni quanti secondi controllare

# === FUNZIONI ===
def estrai_dettagli_ticket(ticket_id):
    url = f"https://ynap.kappa3.app/home/ticketing/ticket/detail?id={ticket_id}"
    headers = {"User-Agent": "Mozilla/5.0"}
    print(f"[DEBUG] Controllo ticket: {ticket_id} → {url}")
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"[DEBUG] Status Code: {response.status_code}")
        if response.status_code != 200:
            return f"[{ticket_id}] ❌ Ticket non trovato (HTTP {response.status_code})", None

        soup = BeautifulSoup(response.text, "html.parser")

        def get_val_by_icon(icon_class):
            icon = soup.find("i", class_=icon_class)
            if not icon:
                return "Non disponibile"
            row = icon.find_parent("div", class_="row listdetail")
            if not row:
                return "Non disponibile"
            span = row.find("span", class_="right")
            if span:
                return span.text.strip()
            select = row.find("select")
            if select and select.find("option", selected=True):
                return select.find("option", selected=True).text.strip()
            return "Non disponibile"

        area = get_val_by_icon("fa-briefcase")
        priorita = get_val_by_icon("fa-bullseye")
        stato = get_val_by_icon("fa-ticket")
        agente = get_val_by_icon("fa-user")
        macchina = get_val_by_icon("fa-microchip")

        print(f"[DEBUG] Estratti: area={area}, priorità={priorita}, stato={stato}, agente={agente}, macchina={macchina}")

        if stato == "Non disponibile" and macchina == "Non disponibile":
            return f"[{ticket_id}] ⚠️ Ticket senza oggetto o stato — ignorato", None

        messaggio = (
            f"📌 Ticket #{ticket_id}\n"
            f"📍 Area: {area}\n"
            f"⚠️ Priorità: {priorita}\n"
            f"🏷 Stato: {stato}\n"
            f"👤 Agente: {agente}\n"
            f"🤖 Macchina: {macchina}\n"
            f"🔗 {url}"
        )

        return f"[{ticket_id}] ✅ Ticket valido", messaggio

    except Exception as e:
        print(f"[ERROR] Ticket {ticket_id} parsing failed: {e}")
        return f"[{ticket_id}] 💥 Errore: {e}", None


def invia_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg}
    try:
        r = requests.post(url, json=payload)
        print(f"[DEBUG] Telegram response: {r.status_code}")
    except Exception as e:
        print(f"[ERROR] Telegram invio fallito: {e}")


# === CICLO PRINCIPALE ===
if __name__ == "__main__":
    print("🤖 Bot avviato e in ascolto...")

    ticket_id = START_ID
    while True:
        print(f"\n[INFO] Controllo ticket ID: {ticket_id}")
        stato, messaggio = estrai_dettagli_ticket(ticket_id)
        print(stato)
        if messaggio:
            invia_telegram(messaggio)
        ticket_id += 1
        time.sleep(DELAY)
