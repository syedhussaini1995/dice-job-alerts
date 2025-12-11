import os
import smtplib
from email.mime.text import MIMEText

#EMAIL_USER = os.getenv("EMAIL_USER")
#EMAIL_PASS = os.getenv("EMAIL_PASS")

EMAIL_USER = os.environ.get('EMAIL_USER')
EMAIL_PASS = os.environ.get('EMAIL_PASS')



def send_test_email():
    subject = "Test Email from Python"
    body = "Hello! This is a test email sent from your Python script."

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_USER
    # Sends email to yourself
    msg["To"] = EMAIL_USER  

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, EMAIL_USER, msg.as_string())

        print("Test email sent successfully!")
    except Exception as e:
        print("Failed to send email:")
        print(e)

send_test_email()
