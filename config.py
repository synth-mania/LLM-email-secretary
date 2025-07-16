"""
Configuration settings for the Email Classifier application.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Email (IMAP) Configuration
# These are typically provided by Proton Mail Bridge
EMAIL_CONFIG = {
    'imap_server': os.getenv('IMAP_SERVER', 'localhost'),
    'imap_port': int(os.getenv('IMAP_PORT', 1143)),  # Default Proton Mail Bridge IMAP port
    'username': os.getenv('EMAIL_USERNAME', ''),
    'password': os.getenv('EMAIL_PASSWORD', ''),
    'use_ssl': os.getenv('IMAP_USE_SSL', 'False').lower() == 'true',
}

# LLM API Configuration
LLM_CONFIG = {
    'api_endpoint': os.getenv('LLM_API_ENDPOINT', 'http://localhost:8000/v1'),  # Default for many local LLM servers
    'api_key': os.getenv('LLM_API_KEY', ''),  # May not be needed for local servers
    'model': os.getenv('LLM_MODEL', 'default'),  # Model identifier if needed
    'temperature': float(os.getenv('LLM_TEMPERATURE', 0.1)),  # Lower for more deterministic responses
    'max_tokens': int(os.getenv('LLM_MAX_TOKENS', 1024)),
    'timeout': int(os.getenv('LLM_TIMEOUT', 30)),  # Timeout in seconds
}

# Email Processing Configuration
PROCESSING_CONFIG = {
    'batch_size': int(os.getenv('BATCH_SIZE', 10)),  # Number of emails to process in one batch
    'max_emails_per_run': int(os.getenv('MAX_EMAILS_PER_RUN', 100)),  # Maximum emails to process in one run
    'include_attachments': os.getenv('INCLUDE_ATTACHMENTS', 'False').lower() == 'true',
    'max_email_size_kb': int(os.getenv('MAX_EMAIL_SIZE_KB', 500)),  # Skip emails larger than this
    'folders_to_process': os.getenv('FOLDERS_TO_PROCESS', 'INBOX').split(','),
    'skip_processed': os.getenv('SKIP_PROCESSED', 'True').lower() == 'true',  # Skip already processed emails
}

# Email Categories and Corresponding Folders
# These are the categories that the LLM will classify emails into
# The key is the category name, and the value is the folder name in Proton Mail
# Note: Folder names should include the 'Folders/' or 'Labels/' prefix as exposed by Proton Mail Bridge
EMAIL_CATEGORIES = {
    'requires_manual_intervention': 'Folders/ManualReview',
    'bills': 'Folders/Bills',
    'promotional': 'Folders/Promotions',
    # Add more categories as needed
}

# LLM Prompt Configuration
# This is the prompt that will be sent to the LLM for classification
CLASSIFICATION_PROMPT_TEMPLATE = """
You are an email classification assistant. Your task is to categorize the following email into exactly one of these categories:
{categories}

Category Definitions:
- 'requires_manual_intervention': Emails that need personal attention, such as personal correspondence, important questions, or anything that requires a human response. This includes emails from friends, family, or colleagues discussing personal matters.
- 'bills': Emails related to financial transactions, invoices, receipts, payment confirmations, account statements, or any financial notifications.
- 'promotional': Marketing emails, newsletters, advertisements, special offers, updates from companies, or any non-personal mass communications.

Email:
Subject: {subject}
From: {sender}
Date: {date}
Body:
{body}

Guidelines for classification:
1. For emails that are part of ongoing conversations (like "Re:" threads), classify based on the content and context, not just the subject line.
2. Newsletters and updates from companies should generally be 'promotional' unless they contain billing information.
3. Only use 'requires_manual_intervention' when the email truly needs personal attention or response.
4. Account statements, payment confirmations, and receipts should be classified as 'bills'.

Analyze the content and respond with only the category name that best matches this email.
"""

# Logging Configuration
LOGGING_CONFIG = {
    'log_level': os.getenv('LOG_LEVEL', 'INFO'),
    'log_file': os.getenv('LOG_FILE', 'email_classifier.log'),
    'log_to_console': os.getenv('LOG_TO_CONSOLE', 'True').lower() == 'true',
}
