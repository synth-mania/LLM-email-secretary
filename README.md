# Email Classifier

An automated system that uses an OpenAI-compatible LLM to classify emails from Proton Mail and organize them into appropriate folders.

## Overview

This application connects to a Proton Mail account via Proton Mail Bridge, processes emails using a locally hosted LLM (llama.cpp or ollama), and automatically categorizes them into predefined folders.

## Features

- Connects to Proton Mail via Proton Mail Bridge using IMAP
- Processes emails through a local LLM server
- Classifies emails into customizable categories
- Automatically moves emails to appropriate folders
- Supports a "dry run" mode that classifies without moving emails
- Runs on a schedule via cron

## Requirements

- Python 3.8+
- Proton Mail Bridge (installed and configured)
- Local LLM server (llama.cpp or ollama)
- GTX 1060 6GB GPU or equivalent for LLM inference

## Project Structure

```
email_classifier/
├── config.py            # Configuration settings
├── email_processor.py   # Email fetching and manipulation logic
├── llm_client.py        # Client for interacting with your local LLM
├── classifier.py        # Core classification logic
├── folder_manager.py    # Logic for moving emails to appropriate folders
├── main.py              # Entry point that ties everything together
├── requirements.txt     # Dependencies
└── README.md            # Documentation
```

## Setup

1. Install Proton Mail Bridge and configure it for your account
2. Set up your local LLM server (llama.cpp or ollama)
3. Clone this repository
4. Install dependencies: `pip install -r requirements.txt`
5. Configure the application by editing `config.py`
6. Run the application: `python main.py`

## Configuration

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` to set:
   - IMAP server details (provided by Proton Mail Bridge)
   - Email credentials
   - LLM server endpoint
   - Processing options

   **Note for Proton Mail Bridge users**: If your Proton Mail Bridge shows "STARTTLS" as the security setting, set `IMAP_USE_SSL=False` in your `.env` file. The application will automatically handle the STARTTLS connection.

3. **Important**: Create folders in Proton Mail that match the folder names in `config.py`:
   - By default, you need to create folders named: `ManualReview`, `Bills`, and `Promotions` in the "Folders" section of Proton Mail
   - The application will look for these folders with the 'Folders/' prefix (e.g., 'Folders/ManualReview')
   - The application cannot create these folders automatically due to Proton Mail Bridge limitations
   - You can create these folders through the Proton Mail web interface or mobile app

4. You can also customize email categories by editing `config.py`:
   - Email categories and corresponding folders
   - Classification prompt template

## Usage

### Creating Folders in Proton Mail

Before running the application, you need to create the following folders in your Proton Mail account:

1. `ManualReview` - For emails that require manual intervention
2. `Bills` - For bill-related emails
3. `Promotions` - For promotional emails

You can create these folders through the Proton Mail web interface or mobile app:

1. Log in to your Proton Mail account
2. Click on the "Folders/Labels" section in the sidebar
3. Click "Add folder" or "New folder" (make sure you're creating a folder, not a label)
4. Enter the folder name (e.g., "ManualReview")
5. Click "Create"

Repeat for each required folder.

**Important Note**: The application expects these folders to be created as "Folders" in Proton Mail, not "Labels". When accessed through IMAP, they will appear with the 'Folders/' prefix (e.g., 'Folders/ManualReview'). The application is configured to look for them with this prefix.

### Standard Mode

Run the application to process and move emails:

```bash
python main.py
```

The application will:
1. Connect to your Proton Mail account via Proton Mail Bridge
2. Check if the required folders exist
3. Process unread emails in your inbox
4. Classify each email using the LLM
5. Move emails to the appropriate folders (if they exist)
6. Mark emails as processed

### Dry Run Mode

If you're having issues with folder creation or email moving, or just want to test the classification without actually moving emails, use the dry run mode:

```bash
DRY_RUN=true python main.py
```

In dry run mode, the application will:
- Connect to your email account
- Classify emails using the LLM
- Log the classification results
- Mark emails as processed (so they won't be processed again)
- NOT attempt to move emails to folders

This is useful for:
- Testing the classification accuracy
- Working around Proton Mail Bridge limitations
- Creating a log of classifications for manual organization

### Automatic Dry Run for Missing Folders

The application will automatically switch to dry run mode for any category folders that don't exist. For example, if you've created the `ManualReview` folder but not the `Bills` or `Promotions` folders, the application will:

- Move emails classified as "requires_manual_intervention" to the `ManualReview` folder
- Log emails classified as "bills" or "promotional" without moving them
- Mark all emails as processed

This allows you to gradually set up your folder structure while still processing and classifying all emails.

## Scheduling

To run the classifier daily, add a cron job:

```bash
# Edit crontab
crontab -e

# Add a line to run daily at 2 AM
0 2 * * * cd /path/to/email_classifier && python main.py
```

## License

[MIT License](LICENSE)
