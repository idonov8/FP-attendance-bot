
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import gspread
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import sys
import traceback

# Load environment variables
load_dotenv()


class FP_bot:
    def __init__(self, debug_mode=False):
        # Use Google Sheets with authentication
        spreadsheet_url = os.getenv('SPREADSHEET_URL')
        if not spreadsheet_url:
            raise ValueError("SPREADSHEET_URL must be set in .env file")
        
        self.debug_mode = debug_mode
        self.logs = []  # Store all execution logs
        
        # Extract sheet ID from URL
        # URL format: https://docs.google.com/spreadsheets/d/SHEET_ID/edit
        if '/d/' in spreadsheet_url and '/edit' in spreadsheet_url:
            sheet_id = spreadsheet_url.split('/d/')[1].split('/')[0]
        else:
            raise ValueError("Invalid SPREADSHEET_URL format. Expected: https://docs.google.com/spreadsheets/d/SHEET_ID/edit")
        
        try:
            # Try to use service account first
            # Check for service account file in current directory or default location
            service_account_path = 'service_account.json'
            if os.path.exists(service_account_path):
                self.sa = gspread.service_account(filename=service_account_path)
            else:
                # Fall back to default location (~/.config/gspread/service_account.json)
                self.sa = gspread.service_account()
            self.sh = self.sa.open_by_key(sheet_id)
            if self.debug_mode:
                self._log(f"✅ Connected to Google Sheet: {self.sh.title}")
        except FileNotFoundError:
            self._log("❌ Service account not found. Please set up authentication:")
            self._log("1. Go to Google Cloud Console")
            self._log("2. Create a service account and download the JSON key")
            self._log("3. Save it as 'service_account.json' in this directory")
            self._log("4. Share your Google Sheet with the service account email")
            raise ValueError("Service account required for Google Sheets access")
        except Exception as e:
            self._log(f"❌ Error connecting to Google Sheets: {e}")
            raise
        
        self.summaries = self.sh.worksheet("Form Responses 1")
        self.attendance = self.sh.worksheet("Form Responses 2")
        self.this_week = ''
        self.last_week = ''
    
    def _log(self, message):
        """Log a message and also print it"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.logs.append(log_entry)
        print(message)

    def google_sheets_reading_date(self):
        self.this_week = self.attendance.col_values(2)[-1]
        self.last_week = self.attendance.col_values(2)[-2]

    def validate_recent_class(self):
        """
        Validate that the this_week class date is within the last 7 days.
        Returns True if valid, False otherwise.
        """
        if not self.this_week:
            return False
            
        try:
            # Parse the date string (assuming format like "2024-01-15" or similar)
            # Try different common date formats
            date_formats = [
                "%Y-%m-%d",      # 2024-01-15
                "%d/%m/%Y",      # 15/01/2024
                "%m/%d/%Y",      # 01/15/2024
                "%d-%m-%Y",      # 15-01-2024
                "%Y/%m/%d",      # 2024/01/15
            ]
            
            class_date = None
            for fmt in date_formats:
                try:
                    class_date = datetime.strptime(self.this_week, fmt).date()
                    break
                except ValueError:
                    continue
            
            if class_date is None:
                self._log(f"❌ Unable to parse date format: {self.this_week}")
                return False
            
            # Check if the class date is within the last 7 days
            seven_days_ago = datetime.now().date() - timedelta(days=7)
            today = datetime.now().date()
            
            if self.debug_mode:
                self._log(f"📅 Class date: {class_date}")
                self._log(f"📅 7 days ago: {seven_days_ago}")
                self._log(f"📅 Today: {today}")
            
            # Class should be between 7 days ago and today (inclusive)
            if seven_days_ago <= class_date <= today:
                return True
            else:
                return False
                
        except Exception as e:
            self._log(f"❌ Error validating class date: {e}")
            return False

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
            self._log("=" * 60)
            self._log("DEBUG MODE - SUMMARY REMINDER EMAIL")
            self._log("=" * 60)
            self._log(f"To: {to_email}")
            self._log(f"From: FP Kadampa TLV <{from_email}>")
            self._log(f"Subject: {subject}")
            self._log("-" * 40)
            self._log("Body:")
            self._log(body)
            self._log("=" * 60)
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
            self._log(f"✅ Email sent successfully to {to_email}!")
        except Exception as e:
            self._log(f"❌ Error sending email to {to_email}: {e}")
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
            self._log(f"would send missed class reminder to: {to_email}")
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
            self._log(f"✅ Missed class reminder sent successfully to {to_email}!")
        except Exception as e:
            self._log(f"❌ Error sending missed class reminder to {to_email}: {e}")
        finally:
            server.quit()

    def send_emails_loop(self, emails, date):
        for email in emails:
            if self.debug_mode:
                name = self._get_student_name_by_email(email)
                self._log(f"Sending summary reminder to {name} ({email}) for {date}")
            else:
                self._log(f"Processing summary reminder for {email} on {date}")
                self.send_email(email, date)

    def send_missed_class_reminders_loop(self, emails, date):
        for email in emails:
            if self.debug_mode:
                name = self._get_student_name_by_email(email)
                self._log(f"Sending missed class reminder to {name} ({email}) for {date}")
            else:
                self._log(f"Sending missed class reminder to {email} for {date}")
            self.send_missed_class_reminder(email, date)

    def send_admin_summary(self, missed_class_emails=None, summary_reminder_emails=None):
        """
        Send a summary email to the admin(s) with details about all emails sent and execution logs.
        
        This provides the admin with a complete overview of which students
        received missed class reminders and summary reminders, plus all execution logs.
        Always sends, even if no emails were sent or if errors occurred.
        
        Supports multiple admin emails via comma-separated ADMIN_EMAIL env variable.
        """
        admin_email_str = os.getenv('ADMIN_EMAIL')
        if not admin_email_str:
            self._log("⚠️ ADMIN_EMAIL not set in environment variables - skipping admin summary")
            return
        
        # Parse admin emails - support comma-separated list
        admin_emails = [email.strip() for email in admin_email_str.split(',') if email.strip()]
        if not admin_emails:
            self._log("⚠️ No valid admin emails found - skipping admin summary")
            return
        
        # Default to empty lists if not provided
        if missed_class_emails is None:
            missed_class_emails = []
        if summary_reminder_emails is None:
            summary_reminder_emails = []
            
        from_email = os.getenv('FROM_EMAIL', "epc@meditationintelaviv.org")
        
        # Use this_week if available, otherwise use current date
        date_str = self.this_week if self.this_week else datetime.now().strftime("%Y-%m-%d")
        subject = f"📊 FP Bot Email Summary - {date_str}"
        
        # Build the summary content in English
        summary_content = f"Hello,\n\nHere is the email sending summary for {date_str}:\n\n"
        
        # Missed class reminders section
        summary_content += f"📧 Missed class reminders ({date_str}): {len(missed_class_emails)}\n"
        if missed_class_emails:
            for email in missed_class_emails:
                name = self._get_student_name_by_email(email)
                summary_content += f"   - {name} ({email})\n"
        else:
            summary_content += "   - No students missed the class\n"
        
        summary_content += "\n"
        
        # Summary reminders section (currently commented out in code)
        summary_content += f"📧 Summary reminders ({self.last_week if self.last_week else 'N/A'}): {len(summary_reminder_emails)}\n"
        if summary_reminder_emails:
            for email in summary_reminder_emails:
                name = self._get_student_name_by_email(email)
                summary_content += f"   - {name} ({email})\n"
        else:
            summary_content += "   - No students need summary reminders\n"
        
        summary_content += f"\nTotal emails sent: {len(missed_class_emails) + len(summary_reminder_emails)}\n\n"
        
        # Add execution logs section
        summary_content += "=" * 60 + "\n"
        summary_content += "📋 Full Execution Logs:\n"
        summary_content += "=" * 60 + "\n\n"
        if self.logs:
            for log_entry in self.logs:
                summary_content += f"{log_entry}\n"
        else:
            summary_content += "No logs available\n"
        
        summary_content += "\n" + "=" * 60 + "\n"
        summary_content += "Best regards,\nFP Kadampa Bot 🤖"
        
        if self.debug_mode:
            self._log("=" * 60)
            self._log("DEBUG MODE - ADMIN SUMMARY EMAIL")
            self._log("=" * 60)
            self._log(f"To: {', '.join(admin_emails)}")
            self._log(f"From: FP Kadampa TLV <{from_email}>")
            self._log(f"Subject: {subject}")
            self._log("-" * 40)
            self._log("Body:")
            self._log(summary_content)
            self._log("=" * 60)
            return
        
        # Send email to all admin emails
        success_count = 0
        for admin_email in admin_emails:
            try:
                message = MIMEMultipart()
                message["From"] = f"FP Kadampa TLV <{from_email}>"
                message["To"] = admin_email
                message["Subject"] = subject
                message.attach(MIMEText(summary_content, "plain"))
                
                server = smtplib.SMTP("smtp.gmail.com", 587)
                server.starttls()
                server.login(from_email, os.getenv('GMAIL_PASSWORD'))
                server.send_message(message)
                server.quit()
                success_count += 1
                self._log(f"✅ Admin summary sent successfully to {admin_email}!")
            except Exception as e:
                self._log(f"❌ Error sending admin summary to {admin_email}: {e}")
        
        if success_count == len(admin_emails):
            self._log(f"✅ Admin summary sent successfully to all {success_count} admin(s)!")
        elif success_count > 0:
            self._log(f"⚠️ Admin summary sent to {success_count} out of {len(admin_emails)} admin(s)")
        else:
            self._log(f"❌ Failed to send admin summary to any of the {len(admin_emails)} admin(s)")

    def run(self):
        """
        Main execution method. Always sends admin summary at the end, regardless of errors.
        """
        missed_class_emails = []
        summary_reminder_emails = []
        
        try:
            self._log("🚀 Starting FP Bot execution...")
            self.google_sheets_reading_date()
            
            if self.debug_mode:
                self._log(f"📅 Current week: {self.this_week}")
                self._log(f"📅 Last week: {self.last_week}")
                self._log("")
            
            # Validate that there was a class in the last 7 days
            if not self.validate_recent_class():
                self._log("❌ There was no class in the last week, or I'm missing some data")
                self._log(f"Last data is from: {self.this_week}")
                # Still send admin summary even if validation fails
            else:
                try:
                    last_week_to_emails = list(set(self.missing_students_emails(self.last_week)) - set(self.completed_students_emails(self.last_week)))
                    this_week_missing_emails = self.missing_students_emails(self.this_week)
                    
                    # Store for admin summary
                    missed_class_emails = this_week_missing_emails
                    summary_reminder_emails = last_week_to_emails

                    if self.debug_mode:
                        self._log(f"📧 Students who missed this week ({self.this_week}): {len(this_week_missing_emails)}")
                        if this_week_missing_emails:
                            for email in this_week_missing_emails:
                                name = self._get_student_name_by_email(email)
                                self._log(f"   - {name} ({email})")
                        self._log("")
                        
                        self._log(f"📧 Students who missed last week but haven't submitted summary: {len(last_week_to_emails)}")
                        if last_week_to_emails:
                            for email in last_week_to_emails:
                                name = self._get_student_name_by_email(email)
                                self._log(f"   - {name} ({email})")
                        self._log("")

                    # Send missed class reminders (day after class) - no need to check if summary was submitted
                    self.send_missed_class_reminders_loop(this_week_missing_emails, self.this_week)
                    
                    # Send summary reminders for last week (only to those who haven't submitted)
                    # self.send_emails_loop(last_week_to_emails, self.last_week)
                except Exception as e:
                    self._log(f"❌ Error during email processing: {e}")
                    self._log(f"Traceback: {traceback.format_exc()}")
        except Exception as e:
            self._log(f"❌ Critical error in run(): {e}")
            self._log(f"Traceback: {traceback.format_exc()}")
        finally:
            # Always send admin summary, no matter what happened
            self._log("📧 Sending admin summary email...")
            try:
                self.send_admin_summary(missed_class_emails, summary_reminder_emails)
            except Exception as e:
                self._log(f"❌ Failed to send admin summary: {e}")
                # Last resort - try to print the error
                print(f"CRITICAL: Could not send admin summary: {e}")


if __name__ == "__main__":
    import sys
    
    # Check for debug mode flag
    debug_mode = "--debug" in sys.argv or "-d" in sys.argv
    
    if debug_mode:
        print("🐛 DEBUG MODE ENABLED - No emails will be sent")
        print("=" * 50)
    
    fp_bot = FP_bot(debug_mode=debug_mode)
    fp_bot.run()