def main():
    if is_already_running():
        print("\n⚠️ Il bot è già in esecuzione. Uscita.\n")
        return

    print(f"[DEBUG] Process PID: {os.getpid()}")
    print("\n🤖 Bot avviato e in ascolto...\n")
    send_message("🤖 Bot avviato e in ascolto...")

    session = requests.Session()
    try:
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
        redirect_location = login_response.headers.get("Locat
