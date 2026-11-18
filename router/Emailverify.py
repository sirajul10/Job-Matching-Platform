import os
import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv

load_dotenv()


def sendEmail(subject: str, content: str, to_address: str) -> bool:
    sender = os.getenv("EMAIL_ADDRESS")
    password = os.getenv("EMAIL_APP_PASSWORD")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_address
    msg.set_content(content)

    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)
        return True
    except (smtplib.SMTPException, OSError) as e:
        print(f"Email failed: {e}")
        return False