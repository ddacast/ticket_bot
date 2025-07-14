import requests

# ✅ Dati di configurazione
TOKEN = "7849103119:AAErLG-ekv-a3VEoMGtwzsqWcd_G8vMyaAw"
chat_id = "1357205243"

# ✅ Funzione per inviare messaggi
def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        response = requests.post(url, data={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"  # Se usi * o _ o altri simboli
        })
        print(f"[DEBUG] Status: {response.status_code} - Risposta: {response.text}")
    except Exception as e:
        print(f"[ERROR] Errore invio: {e}")

# ✅ Invio di test
if __name__ == "__main__":
    send_message("✅ *Test riuscito!* Il bot funziona 💬")
