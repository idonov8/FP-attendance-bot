
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email(to_email, date, password):
    # gmail-generated 16-digit password
    link_to_form = "https://docs.google.com/forms/d/e/1FAIpQLSexjnmtLgWdfkMYsg1l7jQLNL3x1EAyEDv-1zybspIL8JvrDQ/viewform"
    from_email = "epc@meditationintelaviv.org"


    subject = f"A reminder for sending a summary for the {date} class"
    body = (f"Hey there :-) \nWe would like to kindly remind you to send a class summary before the upcoming class so"
            f" that you could attend it normally.\n\n"
            f"{link_to_form}\n\n\nLove,\nMikey")

    message = MIMEMultipart()
    message["From"] = f"FP Kadampa TLV <{from_email}>"
    message["To"] = to_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(from_email, password)
        server.send_message(message)
        print("Email sent successfully!")
    except Exception as e:
        print(f"Error sending email: {e}")
    finally:
        server.quit()

