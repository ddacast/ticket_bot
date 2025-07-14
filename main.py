def check_ticket(ticket_id, data):
    stato = data["stato"].strip().lower()
    subject = data["subject"].replace("*", "").replace("_", "")
    link = data["link"]

    old_entry = ticket_status.get(ticket_id, {})
    old_stato = old_entry.get("stato")
    was_notified = old_entry.get("notificato", False)

    # Debug dettagliato
    print(f"[DEBUG] Analizzo ticket {ticket_id}")
    print(f"        Stato attuale:     '{stato}'")
    print(f"        Stato precedente:  '{old_stato}'")
    print(f"        Già notificato?:   {was_notified}")

    # Aggiorna la mappa dello stato
    ticket_status[ticket_id] = {"stato": stato, "notificato": was_notified}

    # 🔁 Se è cambiato stato, invia notifica
    if old_stato and old_stato != stato:
        print(f"        🔁 Stato cambiato: invio notifica")
        send_message(f"🔄 Ticket #{ticket_id} cambiato da *{old_stato}* a *{stato}*")

    # ✅ Invia immediatamente se è nuovo (anche al primo giro)
    if stato == "nuovo":
        print(f"        🆕 Stato NUOVO: invio messaggio iniziale")
        send_message(f"🆕 Ticket #{ticket_id} in stato *nuovo*\n_{subject}_\n🔗 {link}")
        ticket_status[ticket_id]["notificato"] = True

        if ticket_id not in reminder_timers:
            print(f"        ⏰ Avvio promemoria")
            start_reminder(ticket_id, subject, link)

    # 🛑 Ferma reminder se non è più nuovo
    if stato != "nuovo" and ticket_id in reminder_timers:
        print(f"        🛑 Non è più nuovo: stop promemoria")
        reminder_timers[ticket_id].cancel()
        del reminder_timers[ticket_id]
        ticket_status[ticket_id]["notificato"] = False
