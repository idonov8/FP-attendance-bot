# FP-attendance-bot
This is a script that helps people that missed a class get back on track :)

## Overview
The FP attendance bot automatically tracks student attendance and sends reminder emails to help students stay on track with their meditation course. It integrates with Google Sheets to track attendance and sends two types of reminders:

1. **Missed Class Reminders**: Sent the day after a missed class with class materials and summary form
2. **Summary Reminders**: Sent to students who missed a class but haven't submitted their required summary

## Setup Instructions

### Prerequisites
- Python 3.6 or higher
- Gmail account for sending emails
- Google Sheet with public access (read-only)

### 1. Install Dependencies
```bash
# Using pip
pip install -r requirements.txt

# Or install individually
pip install gspread python-dotenv
```

### 2. Google Sheets Setup

#### Create a Public Google Sheet
1. Create a new Google Sheet (name doesn't matter)
2. Create two worksheets:
   - **"Form Responses 1"**: For summary submissions
   - **"Form Responses 2"**: For attendance records

#### Make Sheet Public
1. Click "Share" in the top-right corner
2. Click "Change to anyone with the link"
3. Set permission to "Viewer" (read-only)
4. Copy the sheet URL

#### Set up Google Forms (Optional but Recommended)
1. Create a Google Form for attendance tracking
2. Link it to the "Form Responses 2" worksheet
3. Create another Google Form for summary submissions
4. Link it to the "Form Responses 1" worksheet

#### Configure Sheet Structure

**Attendance Sheet ("Form Responses 2")**:
- Column 2: Class dates
- Column 3: Present students (comma-separated names)
- Column 7: Student email addresses
- Column 8: All student names

**Summary Sheet ("Form Responses 1")**:
- Column 3: Student email addresses
- Column 6: Submission dates

### 3. Gmail Setup

1. Enable 2-factor authentication on your Gmail account
2. Generate an App Password:
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Generate a password for "Mail"

### 4. Environment Variables Setup

Create a `.env` file in your project root with the following variables:

```bash
# Google Sheets Configuration (Public Sheet URL)
SPREADSHEET_URL=https://docs.google.com/spreadsheets/d/your_sheet_id_here/edit

# Email Configuration
FROM_EMAIL=your_email@example.com
GMAIL_PASSWORD=your_app_password_here

# Links
FORM_LINK=https://docs.google.com/forms/d/e/your_form_link_here
DROPBOX_LINK=https://www.dropbox.com/sh/your_folder_link_here
```

**Important**: The `.env` file is already in `.gitignore` to keep your credentials secure.

### 5. Configure Dropbox Link

1. Create a Dropbox folder with your class materials
2. Share the folder and get the sharing link
3. Add the link to your `.env` file as `DROPBOX_LINK`

## Usage

### Running the Bot

**Normal mode (sends emails):**
```bash
python email_sending.py
```

**Debug mode (prints emails to console):**
```bash
python email_sending.py --debug
# or
python email_sending.py -d
```

### What the Bot Does
1. **Reads attendance data** from Google Sheets
2. **Sends missed class reminders** to students who missed the current week's class (includes Dropbox materials + summary form)
3. **Sends summary reminders** to students who missed last week's class but haven't submitted their summary

### Debug Mode
Debug mode is perfect for testing and development. When enabled, it will:
- Show which students missed classes
- Display email content in the console instead of sending
- Show detailed information about the data being processed
- Help you verify the bot is working correctly before sending real emails

**Debug mode output example:**
```
🐛 DEBUG MODE ENABLED - No emails will be sent
==================================================
📅 Current week: 2024-01-15
📅 Last week: 2024-01-08

📧 Students who missed this week (2024-01-15): 2
   - student1@example.com
   - student2@example.com

📧 Students who missed last week but haven't submitted summary: 1
   - student3@example.com

============================================================
DEBUG MODE - MISSED CLASS REMINDER EMAIL
============================================================
To: student1@example.com
From: FP Kadampa TLV <epc@meditationintelaviv.org>
Subject: Class materials and summary form for 2024-01-15
----------------------------------------
Body:
Hey there :-) 
We noticed you missed yesterday's class (2024-01-15). Here are the class materials and summary form to help you catch up:

Class materials: https://www.dropbox.com/sh/your_folder_link_here
Summary submission form: https://docs.google.com/forms/d/e/your_form_link_here

Please review the materials and submit your summary before the next class.

Love,
Mikey
============================================================
```

### Scheduling (Optional)
To run automatically, set up a cron job or task scheduler:
```bash
# Run daily at 9 AM
0 9 * * * /usr/bin/python3 /path/to/your/email_sending.py
```

## File Structure
```
FP-attendance-bot/
├── email_sending.py          # Main bot script
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables (create this)
├── .gitignore               # Git ignore rules
└── README.md                # This file
```

**Important files to add:**
- `service_account.json` - Google service account key (download from Google Cloud Console)
- `.env` - Environment variables with your configuration

## Troubleshooting

### Common Issues
1. **"gspread" import error**: Install with `pip install gspread`
2. **"SPREADSHEET_URL must be set" error**: Make sure you've created a `.env` file with the `SPREADSHEET_URL` variable
3. **Sheet access error**: Verify the Google Sheet is set to "Anyone with the link can view"
4. **Email sending fails**: Check Gmail app password and 2FA settings

### Testing
Before running the full bot, test individual components:
1. Test Google Sheets connection
2. Test email sending with a single address
3. Verify sheet structure matches expected format

## Security Notes
- Keep your `.env` file secure and never commit it to version control
- Use app passwords instead of your main Gmail password
- Since the sheet is public, be careful not to include sensitive information in the sheet
