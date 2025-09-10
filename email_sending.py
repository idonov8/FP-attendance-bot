
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import gspread
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class FP_bot:
    def __init__(self, debug_mode=False):
        # Use Google Sheets with authentication
        spreadsheet_url = os.getenv('SPREADSHEET_URL')
        if not spreadsheet_url:
            raise ValueError("SPREADSHEET_URL must be set in .env file")
        
        self.debug_mode = debug_mode
        
        # Extract sheet ID from URL
        # URL format: https://docs.google.com/spreadsheets/d/SHEET_ID/edit
        if '/d/' in spreadsheet_url and '/edit' in spreadsheet_url:
            sheet_id = spreadsheet_url.split('/d/')[1].split('/')[0]
        else:
            raise ValueError("Invalid SPREADSHEET_URL format. Expected: https://docs.google.com/spreadsheets/d/SHEET_ID/edit")
        
        try:
            # Try to use service account first
            self.sa = gspread.service_account()
            self.sh = self.sa.open_by_key(sheet_id)
            if self.debug_mode:
                print(f"✅ Connected to Google Sheet: {self.sh.title}")
        except FileNotFoundError:
            print("❌ Service account not found. Please set up authentication:")
            print("1. Go to Google Cloud Console")
            print("2. Create a service account and download the JSON key")
            print("3. Save it as 'service_account.json' in this directory")
            print("4. Share your Google Sheet with the service account email")
            raise ValueError("Service account required for Google Sheets access")
        except Exception as e:
            print(f"❌ Error connecting to Google Sheets: {e}")
            raise
        
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

    def _get_student_name_by_email(self, email):
        """Get student name by email address"""
        try:
            # Get all emails from column 7
            all_emails = self.attendance.col_values(7)
            # Get all names from column 8
            all_names = self.attendance.col_values(8)
            
            # Find the index of the email
            if email in all_emails:
                index = all_emails.index(email)
                if index < len(all_names):
                    return all_names[index]
            return "Unknown"
        except Exception:
            return "Unknown"

    def send_email(self, to_email, date, password):
        # gmail-generated 16-digit password
        link_to_form = os.getenv('FORM_LINK', "https://docs.google.com/forms/d/e/1FAIpQLSexjnmtLgWdfkMYsg1l7jQLNL3x1EAyEDv-1zybspIL8JvrDQ/viewform")
        from_email = os.getenv('FROM_EMAIL', "epc@meditationintelaviv.org")

        subject = f"A reminder for sending a summary for the {date} class"
        body = (f"Hey there :-) \nWe would like to kindly remind you to send a class summary (for {date}) before the upcoming class so"
                f" that you could attend it normally.\n\n"
                f"{link_to_form}\n\n\nLove,\nMikey")

        if self.debug_mode:
            print("=" * 60)
            print("DEBUG MODE - SUMMARY REMINDER EMAIL")
            print("=" * 60)
            print(f"To: {to_email}")
            print(f"From: FP Kadampa TLV <{from_email}>")
            print(f"Subject: {subject}")
            print("-" * 40)
            print("Body:")
            print(body)
            print("=" * 60)
            return

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

    def send_missed_class_reminder(self, to_email, date, password):
        # gmail-generated 16-digit password
        link_to_form = os.getenv('FORM_LINK', "https://docs.google.com/forms/d/e/1FAIpQLSexjnmtLgWdfkMYsg1l7jQLNL3x1EAyEDv-1zybspIL8JvrDQ/viewform")
        dropbox_link = os.getenv('DROPBOX_LINK', "YOUR_DROPBOX_LINK_HERE")  # Set in .env file
        from_email = os.getenv('FROM_EMAIL', "epc@meditationintelaviv.org")

        subject = f"Class materials and summary form for {date}"
        body = (f"Hey there :-) \nWe noticed you missed yesterday's class ({date}). Here are the class materials and summary form to help you catch up:\n\n"
                f"Class materials: {dropbox_link}\n"
                f"Summary submission form: {link_to_form}\n\n"
                f"Please review the materials and submit your summary before the next class.\n\n"
                f"Love,\nMikey")

        if self.debug_mode:
            print("=" * 60)
            print("DEBUG MODE - MISSED CLASS REMINDER EMAIL")
            print("=" * 60)
            print(f"To: {to_email}")
            print(f"From: FP Kadampa TLV <{from_email}>")
            print(f"Subject: {subject}")
            print("-" * 40)
            print("Body:")
            print(body)
            print("=" * 60)
            return

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
            print("Missed class reminder sent successfully!")
        except Exception as e:
            print(f"Error sending missed class reminder: {e}")
        finally:
            server.quit()

    def send_emails_loop(self, emails, date):
        for email in emails:
            if self.debug_mode:
                name = self._get_student_name_by_email(email)
                print(f"Sending summary reminder to {name} ({email}) for {date}")
            else:
                print(email, date)
            self.send_email(email, date, "")

    def send_missed_class_reminders_loop(self, emails, date):
        for email in emails:
            if self.debug_mode:
                name = self._get_student_name_by_email(email)
                print(f"Sending missed class reminder to {name} ({email}) for {date}")
            else:
                print(f"Sending missed class reminder to {email} for {date}")
            self.send_missed_class_reminder(email, date, "")

    def run(self):
        self.google_sheets_reading_date()
        
        if self.debug_mode:
            print(f"📅 Current week: {self.this_week}")
            print(f"📅 Last week: {self.last_week}")
            print()
        
        last_week_to_emails = list(set(self.missing_students_emails(self.last_week)) - set(self.completed_students_emails(self.last_week)))
        this_week_missing_emails = self.missing_students_emails(self.this_week)

        if self.debug_mode:
            print(f"📧 Students who missed this week ({self.this_week}): {len(this_week_missing_emails)}")
            if this_week_missing_emails:
                for email in this_week_missing_emails:
                    name = self._get_student_name_by_email(email)
                    print(f"   - {name} ({email})")
            print()
            
            print(f"📧 Students who missed last week but haven't submitted summary: {len(last_week_to_emails)}")
            if last_week_to_emails:
                for email in last_week_to_emails:
                    name = self._get_student_name_by_email(email)
                    print(f"   - {name} ({email})")
            print()

        # Send missed class reminders (day after class) - no need to check if summary was submitted
        self.send_missed_class_reminders_loop(this_week_missing_emails, self.this_week)
        
        # Send summary reminders for last week (only to those who haven't submitted)
        self.send_emails_loop(last_week_to_emails, self.last_week)


if __name__ == "__main__":
    import sys
    
    # Check for debug mode flag
    debug_mode = "--debug" in sys.argv or "-d" in sys.argv
    
    if debug_mode:
        print("🐛 DEBUG MODE ENABLED - No emails will be sent")
        print("=" * 50)
    
    fp_bot = FP_bot(debug_mode=debug_mode)
    fp_bot.run()