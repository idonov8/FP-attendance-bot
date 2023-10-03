
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import gspread


class FP_bot:
    def __init__(self):
        self.sa = gspread.service_account()
        self.sh = self.sa.open("השלמות שיעורים")
        self.summaries = self.sh.worksheet("Form Responses 1")
        self.attendance = self.sh.worksheet("Form Responses 2")
        self.this_week = ''
        self.last_week = ''

    def google_sheets_reading_date(self):
        self.this_week = self.attendance.col_values(2)[-1]
        self.last_week = self.attendance.col_values(2)[-2]

    def completed_students_emails(self, date):
        list_of_completed_students_emails = []

        indexes = [i for i, x in enumerate(self.summaries.col_values(6)) if x == date]
        for ind in indexes:
            list_of_completed_students_emails.append(self.summaries.row_values(ind + 1)[3].lower())

        return list_of_completed_students_emails

    def missing_students_emails(self, date):
        row_num = self.attendance.col_values(2).index(date) + 1
        all_students = self.attendance.col_values(8)

        present_students = self.attendance.cell(row_num, 3).value.split(", ")
        missing_students = list(set(all_students) - set(present_students) - {""})


        missing_students_emails = []
        for student in missing_students:
            index = self.attendance.col_values(8).index(student)
            missing_students_emails.append(self.attendance.col_values(7)[index].lower())

        return missing_students_emails

    @staticmethod
    def send_email(to_email, date, password):
        # gmail-generated 16-digit password
        link_to_form = "https://docs.google.com/forms/d/e/1FAIpQLSexjnmtLgWdfkMYsg1l7jQLNL3x1EAyEDv-1zybspIL8JvrDQ/viewform"
        from_email = "epc@meditationintelaviv.org"


        subject = f"A reminder for sending a summary for the {date} class"
        body = (f"Hey there :-) \nWe would like to kindly remind you to send a class summary (for {date}) before the upcoming class so"
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

    def send_emails_loop(self, emails, date):
        for email in emails:
            print(email, date)
            self.send_email(email, date, "")

    def run(self):
        self.google_sheets_reading_date()
        last_week_to_emails = list(set(self.missing_students_emails(self.last_week)) - set(self.completed_students_emails(self.last_week)))
        # this_week_to_emails = list(set(self.missing_students_emails(self.this_week)) - set(self.completed_students_emails(self.this_week)))

        self.send_emails_loop(last_week_to_emails, self.last_week)
        # self.send_emails_loop(this_week_to_emails, self.this_week)


if __name__ == "__main__":
    fp_bot = FP_bot()
    fp_bot.run()