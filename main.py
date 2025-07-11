def ticket_exists(session, ticket_id):
    detail_url = f"{DETAIL_URL_BASE}{ticket_id}"
    r = session.get(detail_url)
    if "Ticket non trovato" in r.text or r.status_code != 200:
        return None

    soup = BeautifulSoup(r.text, "html.parser")

    # TAG CORRETTI
    subject_tag = soup.select_one("div.ticket-data h4")
    status_tag = soup.select_one("span.tkt-status")

    subject = subject_tag.text.strip() if subject_tag else None
    status = status_tag.text.strip() if status_tag else None

    if not subject or not status:
        print(f"[{ticket_id}] ⚠️ Ticket senza oggetto o stato — ignorato")
        return None

    return {
        "id": ticket_id,
        "subject": subject,
        "status": status,
        "link": detail_url
    }
