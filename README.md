# Email Classifier

An automated system that uses an OpenAI-compatible LLM to classify emails from Proton Mail and organize them into appropriate folders.

## Overview

This application connects to a Proton Mail account via Proton Mail Bridge, processes emails using a locally hosted LLM (llama.cpp or ollama), and automatically categorizes them into predefined folders.

## Features

- Connects to Proton Mail via Proton Mail Bridge using IMAP
- Processes emails through a local LLM server
- Classifies emails into customizable categories
- Automatically moves emails to appropriate folders
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

Edit `config.py` to set:
- IMAP server details (provided by Proton Mail Bridge)
- Email credentials
- LLM server endpoint
- Email categories and corresponding folders
- Processing options

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
