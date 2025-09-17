
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
            all_emails = [email.lower() for email in self.attendance.col_values(7)]
            # Get all names from column 8
            all_names = self.attendance.col_values(8)
            
            # Find the index of the email
            if email.lower() in all_emails:
                index = all_emails.index(email)
                if index < len(all_names):
                    return all_names[index]
            return "Unknown"
        except Exception:
            return "Unknown"

    def send_email(self, to_email, date):
        """
        ---- FOR NOW DON'T USE ----
        Send a summary reminder email to students who missed a previous class 
        but haven't submitted their class summary yet.
        
        This is a follow-up reminder sent to students who were absent from a class
        and still need to submit their summary before attending the next class.
        """
        # gmail-generated 16-digit password
        link_to_form = os.getenv('FORM_LINK', "https://docs.google.com/forms/d/e/1FAIpQLSexjnmtLgWdfkMYsg1l7jQLNL3x1EAyEDv-1zybspIL8JvrDQ/viewform")
        from_email = os.getenv('FROM_EMAIL', "epc@meditationintelaviv.org")
        name = self._get_student_name_by_email(to_email)

        subject = f"תזכורת לשליחת סיכום לשיעור {date}"
        body = (f"שלום {name} :-) \nאנחנו רוצים להזכיר לך בעדינות לשלוח סיכום שיעור (עבור {date}) לפני השיעור הבא כדי"
                f" שתוכל להשתתף בו כרגיל.\n\n"
                f"{link_to_form}\n\n\nבאהבה,\nמיקי")

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
            server.login(from_email, os.getenv('GMAIL_PASSWORD'))
            server.send_message(message)
            print("Email sent successfully!")
        except Exception as e:
            print(f"Error sending email: {e}")
        finally:
            server.quit()

    def send_missed_class_reminder(self, to_email, date):
        """
        Send a missed class reminder email to students who just missed a class.
        
        This is an immediate notification sent to students who were absent from 
        yesterday's class, providing them with class materials and summary form 
        to help them catch up before the next class.
        """
        # gmail-generated 16-digit password
        link_to_form = os.getenv('FORM_LINK', "https://docs.google.com/forms/d/e/1FAIpQLSexjnmtLgWdfkMYsg1l7jQLNL3x1EAyEDv-1zybspIL8JvrDQ/viewform")
        dropbox_link = os.getenv('DROPBOX_LINK', "")
        from_email = os.getenv('FROM_EMAIL', "epc@meditationintelaviv.org")
        name = self._get_student_name_by_email(to_email)

        subject = f"השלמת שיעור קדמפה FP"
        body = (
            f'<div dir="rtl" style="text-align:right; font-family:Arial, sans-serif;">'
            f'שלום {name} :-)<br>'
            f'שמנו לב שפספסת את השיעור האחרון ({date}). הנה הקלטת השיעור וטופס הסיכום שיעזרו לך להשלים:<br><br>'
            f'<b>הקלטת השיעור:</b> <a href="{dropbox_link}">{dropbox_link}</a><br>'
            f'<b>טופס הגשת סיכום:</b> <a href="{link_to_form}">{link_to_form}</a><br><br>'
            f'אנא עיין בחומרים והגש את הסיכום שלך לפני השיעור הבא.<br><br>'
            f'באהבה,<br>קדמפה בוט 🤖'
            f'</div>'
        )

        if self.debug_mode:
            print(f"would send missed class reminder to: {to_email}")
            return

        message = MIMEMultipart()
        message["From"] = f"FP Kadampa TLV <{from_email}>"
        message["To"] = to_email
        message["Subject"] = subject
        message.attach(MIMEText(body, "html"))
        try:
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(from_email, os.getenv('GMAIL_PASSWORD'))
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
                self.send_email(email, date)

    def send_missed_class_reminders_loop(self, emails, date):
        for email in emails:
            if self.debug_mode:
                name = self._get_student_name_by_email(email)
                print(f"Sending missed class reminder to {name} ({email}) for {date}")
            else:
                print(f"Sending missed class reminder to {email} for {date}")
            self.send_missed_class_reminder(email, date)

    def send_admin_summary(self, missed_class_emails, summary_reminder_emails):
        """
        Send a summary email to the admin with details about all emails sent.
        
        This provides the admin with a complete overview of which students
        received missed class reminders and summary reminders.
        """
        admin_email = os.getenv('ADMIN_EMAIL')
        if not admin_email:
            print("⚠️ ADMIN_EMAIL not set in environment variables - skipping admin summary")
            return
            
        from_email = os.getenv('FROM_EMAIL', "epc@meditationintelaviv.org")
        
        subject = f"📊 סיכום שליחת הודעות - {self.this_week}"
        
        # Build the summary content
        summary_content = f"שלום,\n\nהנה סיכום שליחת ההודעות עבור {self.this_week}:\n\n"
        
        # Missed class reminders section
        summary_content += f"📧 הודעות על שיעור חסר ({self.this_week}): {len(missed_class_emails)}\n"
        if missed_class_emails:
            for email in missed_class_emails:
                name = self._get_student_name_by_email(email)
                summary_content += f"   - {name} ({email})\n"
        else:
            summary_content += "   - אין תלמידים שפספסו את השיעור\n"
        
        summary_content += "\n"
        
        # Summary reminders section
        '''
        summary_content += f"📧 תזכורות סיכום ({self.last_week}): {len(summary_reminder_emails)}\n"
        if summary_reminder_emails:
            for email in summary_reminder_emails:
                name = self._get_student_name_by_email(email)
                summary_content += f"   - {name} ({email})\n"
        else:
            summary_content += "   - אין תלמידים שצריכים תזכורת לסיכום\n"
        
        summary_content += f"\nסה\"כ הודעות שנשלחו: {len(missed_class_emails) + len(summary_reminder_emails)}\n\n"
        summary_content += "בברכה,\nקדמפה בוט 🤖"
        
        if self.debug_mode:
            print("=" * 60)
            print("DEBUG MODE - ADMIN SUMMARY EMAIL")
            print("=" * 60)
            print(f"To: {admin_email}")
            print(f"From: FP Kadampa TLV <{from_email}>")
            print(f"Subject: {subject}")
            print("-" * 40)
            print("Body:")
            print(summary_content)
            print("=" * 60)
            return
        '''
        message = MIMEMultipart()
        message["From"] = f"FP Kadampa TLV <{from_email}>"
        message["To"] = admin_email
        message["Subject"] = subject
        message.attach(MIMEText(summary_content, "plain"))
        
        try:
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(from_email, os.getenv('GMAIL_PASSWORD'))
            server.send_message(message)
            print("Admin summary sent successfully!")
        except Exception as e:
            print(f"Error sending admin summary: {e}")
        finally:
            server.quit()

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
        # self.send_emails_loop(last_week_to_emails, self.last_week)
        
        # Send admin summary after all student emails are sent
        self.send_admin_summary(this_week_missing_emails, last_week_to_emails)


if __name__ == "__main__":
    import sys
    
    # Check for debug mode flag
    debug_mode = "--debug" in sys.argv or "-d" in sys.argv
    
    if debug_mode:
        print("🐛 DEBUG MODE ENABLED - No emails will be sent")
        print("=" * 50)
    
    fp_bot = FP_bot(debug_mode=debug_mode)
    fp_bot.run()