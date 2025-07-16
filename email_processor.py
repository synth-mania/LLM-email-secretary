"""
Email processing module for fetching and manipulating emails via IMAP.
"""
import imaplib
import email
from email.header import decode_header
import logging
import os
import re
from typing import List, Dict, Tuple, Optional, Any
import time
import ssl

from config import EMAIL_CONFIG, PROCESSING_CONFIG, EMAIL_CATEGORIES

# Configure logging
logger = logging.getLogger(__name__)


class EmailProcessor:
    """
    Handles email operations including fetching, parsing, and moving emails between folders.
    Uses IMAP protocol to interact with the email server (Proton Mail Bridge).
    """

    def __init__(self):
        """Initialize the email processor with configuration from config.py."""
        self.imap_server = EMAIL_CONFIG['imap_server']
        self.imap_port = EMAIL_CONFIG['imap_port']
        self.username = EMAIL_CONFIG['username']
        self.password = EMAIL_CONFIG['password']
        self.use_ssl = EMAIL_CONFIG['use_ssl']
        self.connection = None
        self.folders_to_process = PROCESSING_CONFIG['folders_to_process']
        self.max_email_size_kb = PROCESSING_CONFIG['max_email_size_kb']
        self.include_attachments = PROCESSING_CONFIG['include_attachments']
        self.batch_size = PROCESSING_CONFIG['batch_size']
        self.max_emails_per_run = PROCESSING_CONFIG['max_emails_per_run']
        self.skip_processed = PROCESSING_CONFIG['skip_processed']

    def connect(self) -> bool:
        """
        Establish a connection to the IMAP server.
        
        Returns:
            bool: True if connection was successful, False otherwise.
        """
        try:
            # Try different connection methods
            try:
                if self.use_ssl:
                    # Try with SSL first
                    logger.debug("Attempting to connect with SSL")
                    self.connection = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
                else:
                    # Try without SSL
                    logger.debug("Attempting to connect without SSL")
                    self.connection = imaplib.IMAP4(self.imap_server, self.imap_port)
            except Exception as e:
                logger.debug(f"First connection attempt failed: {e}")
                # If the first attempt fails, try the opposite approach
                if self.use_ssl:
                    logger.debug("Retrying without SSL")
                    self.connection = imaplib.IMAP4(self.imap_server, self.imap_port)
                else:
                    logger.debug("Retrying with SSL")
                    self.connection = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            
            # Login to the server
            self.connection.login(self.username, self.password)
            
            logger.info(f"Successfully connected to {self.imap_server}")
            return True
        except imaplib.IMAP4.error as e:
            logger.error(f"Failed to login to IMAP server: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to IMAP server: {e}")
            return False

    def disconnect(self) -> None:
        """Close the connection to the IMAP server."""
        if self.connection:
            try:
                self.connection.logout()
                logger.info("Disconnected from IMAP server")
            except Exception as e:
                logger.error(f"Error during IMAP logout: {e}")
            finally:
                self.connection = None

    def get_folders(self) -> List[str]:
        """
        Get a list of all folders in the mailbox.
        
        Returns:
            List[str]: List of folder names.
        """
        if not self.connection:
            if not self.connect():
                return []
        
        try:
            status, folders = self.connection.list()
            if status != 'OK':
                logger.error(f"Failed to get folders: {status}")
                return []
            
            # Parse folder names from response
            folder_list = []
            for folder in folders:
                if isinstance(folder, bytes):
                    folder = folder.decode('utf-8', errors='replace')
                
                logger.debug(f"Raw folder entry: {folder}")
                
                # Try different regex patterns to extract folder names
                # Pattern 1: Standard quoted format at the end
                match = re.search(r'"([^"]*)"$', folder)
                if match:
                    folder_list.append(match.group(1))
                    continue
                
                # Pattern 2: Look for folder name after the last delimiter
                match = re.search(r'(?:\s|\|)\s*"?([^"]+)"?$', folder)
                if match:
                    folder_list.append(match.group(1))
                    continue
                
                # Pattern 3: Look for anything after "INBOX."
                match = re.search(r'INBOX\.(.+?)(?:\s|$)', folder)
                if match:
                    folder_list.append(match.group(1))
                    continue
                
                # Add INBOX if it's in the response
                if "INBOX" in folder:
                    if "INBOX" not in folder_list:
                        folder_list.append("INBOX")
            
            logger.info(f"Detected folders: {folder_list}")
            return folder_list
        except Exception as e:
            logger.error(f"Error getting folders: {e}")
            return []

    def create_folder_if_not_exists(self, folder_name: str) -> bool:
        """
        Create a folder if it doesn't already exist.
        
        Args:
            folder_name: Name of the folder to create.
            
        Returns:
            bool: True if folder exists or was created successfully, False otherwise.
        """
        if not self.connection:
            if not self.connect():
                return False
        
        try:
            folders = self.get_folders()
            if folder_name in folders:
                return True
            
            # Try different formats for folder creation
            # Some IMAP servers are picky about the format
            formats_to_try = [
                f'"{folder_name}"',  # Standard format with quotes
                folder_name,         # Without quotes
                f'INBOX.{folder_name}',  # As a subfolder of INBOX
                f'INBOX/{folder_name}',  # As a subfolder of INBOX with slash
                f'Folders/{folder_name}',  # As a subfolder of Folders
                f'Labels/{folder_name}'  # As a subfolder of Labels
            ]
            
            for folder_format in formats_to_try:
                try:
                    logger.debug(f"Attempting to create folder with format: {folder_format}")
                    status, response = self.connection.create(folder_format)
                    if status == 'OK':
                        logger.info(f"Created folder: {folder_name}")
                        return True
                except Exception as e:
                    logger.debug(f"Failed to create folder with format {folder_format}: {e}")
                    continue
            
            # If we get here, all formats failed
            logger.error(f"Failed to create folder {folder_name} with all attempted formats")
            return False
        except Exception as e:
            logger.error(f"Error creating folder {folder_name}: {e}")
            return False

    def select_folder(self, folder_name: str) -> int:
        """
        Select a folder to work with.
        
        Args:
            folder_name: Name of the folder to select.
            
        Returns:
            int: Number of messages in the folder, or -1 if selection failed.
        """
        if not self.connection:
            if not self.connect():
                return -1
        
        try:
            # Try different formats for folder selection
            formats_to_try = [
                folder_name,                # Standard format
                f'"{folder_name}"',         # Quoted format
                f'INBOX/{folder_name}',     # As a subfolder of INBOX with slash
                f'INBOX.{folder_name}',     # As a subfolder of INBOX with dot
                f'Folders/{folder_name}',   # As a subfolder of Folders
                f'Labels/{folder_name}'     # As a subfolder of Labels
            ]
            
            for folder_format in formats_to_try:
                try:
                    logger.debug(f"Attempting to select folder with format: {folder_format}")
                    status, data = self.connection.select(folder_format)
                    if status == 'OK':
                        message_count = int(data[0])
                        logger.info(f"Selected folder {folder_name} with {message_count} messages")
                        return message_count
                except Exception as e:
                    logger.debug(f"Failed to select folder with format {folder_format}: {e}")
                    continue
            
            # If we get here, all formats failed
            logger.error(f"Failed to select folder {folder_name} with all attempted formats")
            return -1
        except Exception as e:
            logger.error(f"Error selecting folder {folder_name}: {e}")
            return -1

    def search_emails(self, criteria: str = 'ALL') -> List[str]:
        """
        Search for emails matching the given criteria.
        
        Args:
            criteria: IMAP search criteria (default: 'ALL').
            
        Returns:
            List[str]: List of email IDs matching the criteria.
        """
        if not self.connection:
            logger.error("Not connected to IMAP server")
            return []
        
        try:
            status, data = self.connection.search(None, criteria)
            if status != 'OK':
                logger.error(f"Search failed: {data}")
                return []
            
            # Parse email IDs
            email_ids = data[0].split()
            return [eid.decode('utf-8') for eid in email_ids]
        except Exception as e:
            logger.error(f"Error searching emails: {e}")
            return []

    def get_unprocessed_emails(self, folder_name: str, limit: int = None) -> List[str]:
        """
        Get a list of unprocessed email IDs from the specified folder.
        
        Args:
            folder_name: Name of the folder to search in.
            limit: Maximum number of emails to return.
            
        Returns:
            List[str]: List of unprocessed email IDs.
        """
        if self.select_folder(folder_name) <= 0:
            return []
        
        # If we're not skipping processed emails, just get all emails
        if not self.skip_processed:
            email_ids = self.search_emails('ALL')
        else:
            try:
                # Try to search for emails without our processed flag
                # Some IMAP servers might not support KEYWORD search
                email_ids = self.search_emails('NOT KEYWORD PROCESSED')
            except Exception as e:
                logger.warning(f"Failed to search with KEYWORD criteria: {e}")
                # Fall back to getting all emails
                email_ids = self.search_emails('ALL')
                
                # We'll filter processed emails manually later in the process_emails method
        
        # Apply limit if specified
        if limit and len(email_ids) > limit:
            return email_ids[:limit]
        
        return email_ids

    def fetch_email(self, email_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch and parse an email by ID.
        
        Args:
            email_id: ID of the email to fetch.
            
        Returns:
            Optional[Dict[str, Any]]: Parsed email data or None if fetching failed.
        """
        if not self.connection:
            logger.error("Not connected to IMAP server")
            return None
        
        try:
            status, data = self.connection.fetch(email_id, '(RFC822)')
            if status != 'OK':
                logger.error(f"Failed to fetch email {email_id}: {data}")
                return None
            
            raw_email = data[0][1]
            email_message = email.message_from_bytes(raw_email)
            
            # Check email size
            email_size_kb = len(raw_email) / 1024
            if email_size_kb > self.max_email_size_kb:
                logger.warning(f"Email {email_id} exceeds size limit ({email_size_kb:.2f} KB > {self.max_email_size_kb} KB)")
                return None
            
            # Parse email data
            subject = self._decode_header(email_message.get('Subject', ''))
            sender = self._decode_header(email_message.get('From', ''))
            date = self._decode_header(email_message.get('Date', ''))
            
            # Get email body
            body = self._get_email_body(email_message)
            
            # Get attachments if needed
            attachments = []
            if self.include_attachments:
                attachments = self._get_attachments(email_message)
            
            return {
                'id': email_id,
                'subject': subject,
                'sender': sender,
                'date': date,
                'body': body,
                'attachments': attachments,
                'raw_message': email_message
            }
        except Exception as e:
            logger.error(f"Error fetching email {email_id}: {e}")
            return None

    def _decode_header(self, header: str) -> str:
        """
        Decode email header.
        
        Args:
            header: Email header to decode.
            
        Returns:
            str: Decoded header.
        """
        if not header:
            return ""
        
        try:
            decoded_header = decode_header(header)
            header_parts = []
            
            for content, encoding in decoded_header:
                if isinstance(content, bytes):
                    if encoding:
                        header_parts.append(content.decode(encoding or 'utf-8', errors='replace'))
                    else:
                        header_parts.append(content.decode('utf-8', errors='replace'))
                else:
                    header_parts.append(str(content))
            
            return ''.join(header_parts)
        except Exception as e:
            logger.error(f"Error decoding header: {e}")
            return header

    def _get_email_body(self, email_message) -> str:
        """
        Extract the body text from an email message.
        
        Args:
            email_message: Email message object.
            
        Returns:
            str: Email body text.
        """
        body = ""
        
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                
                # Skip attachments
                if "attachment" in content_disposition:
                    continue
                
                if content_type == "text/plain":
                    try:
                        payload = part.get_payload(decode=True)
                        charset = part.get_content_charset() or 'utf-8'
                        body += payload.decode(charset, errors='replace')
                    except Exception as e:
                        logger.error(f"Error decoding plain text part: {e}")
                elif content_type == "text/html" and not body:
                    # Use HTML content if no plain text is available
                    try:
                        payload = part.get_payload(decode=True)
                        charset = part.get_content_charset() or 'utf-8'
                        html_body = payload.decode(charset, errors='replace')
                        # Simple HTML to text conversion
                        body += re.sub('<[^<]+?>', ' ', html_body)
                    except Exception as e:
                        logger.error(f"Error decoding HTML part: {e}")
        else:
            # Not multipart - get the content directly
            content_type = email_message.get_content_type()
            try:
                payload = email_message.get_payload(decode=True)
                charset = email_message.get_content_charset() or 'utf-8'
                
                if content_type == "text/plain":
                    body = payload.decode(charset, errors='replace')
                elif content_type == "text/html":
                    html_body = payload.decode(charset, errors='replace')
                    body = re.sub('<[^<]+?>', ' ', html_body)
                else:
                    body = f"[Unsupported content type: {content_type}]"
            except Exception as e:
                logger.error(f"Error decoding email body: {e}")
        
        return body

    def _get_attachments(self, email_message) -> List[Dict[str, Any]]:
        """
        Extract attachments from an email message.
        
        Args:
            email_message: Email message object.
            
        Returns:
            List[Dict[str, Any]]: List of attachment information.
        """
        attachments = []
        
        for part in email_message.walk():
            content_disposition = str(part.get("Content-Disposition"))
            
            if "attachment" in content_disposition:
                filename = part.get_filename()
                if filename:
                    # Decode filename if needed
                    if isinstance(filename, bytes):
                        filename = filename.decode('utf-8', errors='replace')
                    
                    content_type = part.get_content_type()
                    size = len(part.get_payload(decode=True))
                    
                    attachments.append({
                        'filename': filename,
                        'content_type': content_type,
                        'size': size
                    })
        
        return attachments

    def folder_exists(self, folder_name: str) -> bool:
        """
        Check if a folder actually exists by trying to select it.
        
        Args:
            folder_name: Name of the folder to check.
            
        Returns:
            bool: True if the folder exists, False otherwise.
        """
        if not self.connection:
            if not self.connect():
                return False
        
        try:
            # Get the raw folder list first for debugging
            status, folders_raw = self.connection.list()
            if status == 'OK':
                logger.debug(f"Raw folder list from IMAP server:")
                for f in folders_raw:
                    if isinstance(f, bytes):
                        f_str = f.decode('utf-8', errors='replace')
                    else:
                        f_str = str(f)
                    logger.debug(f"  {f_str}")
            
            # Check if the folder exists in the folder list
            folders = self.get_folders()
            if folder_name in folders:
                logger.info(f"Folder '{folder_name}' exists in folder list")
                return True
            
            # Try different formats for the folder name
            formats_to_check = [
                folder_name.upper(),        # Uppercase
                folder_name.lower(),        # Lowercase
                f'INBOX/{folder_name}',     # As a subfolder of INBOX with slash
                f'INBOX.{folder_name}',     # As a subfolder of INBOX with dot
                f'Folders/{folder_name}',   # As a subfolder of Folders
                f'Labels/{folder_name}'     # As a subfolder of Labels
            ]
            
            for folder_format in formats_to_check:
                if folder_format in folders:
                    logger.info(f"Folder '{folder_name}' exists with format: {folder_format}")
                    return True
            
            # Try to select the folder directly using different formats
            formats_to_try = [
                folder_name,                # Standard format
                f'"{folder_name}"',         # Quoted format
                folder_name.upper(),        # Uppercase
                folder_name.lower(),        # Lowercase
                f'INBOX/{folder_name}',     # As a subfolder of INBOX with slash
                f'INBOX.{folder_name}',     # As a subfolder of INBOX with dot
                f'Folders/{folder_name}',   # As a subfolder of Folders
                f'Labels/{folder_name}'     # As a subfolder of Labels
            ]
            
            for folder_format in formats_to_try:
                try:
                    logger.debug(f"Trying to select folder with format: {folder_format}")
                    status, data = self.connection.select(folder_format)
                    if status == 'OK':
                        # Deselect the folder by selecting INBOX
                        self.connection.select('INBOX')
                        logger.info(f"Verified folder '{folder_name}' exists with format: {folder_format}")
                        return True
                except Exception as e:
                    logger.debug(f"Exception when selecting {folder_format}: {e}")
                    continue
            
            # If we get here, the folder doesn't exist
            logger.warning(f"Folder '{folder_name}' does not exist or cannot be selected")
            return False
        except Exception as e:
            logger.error(f"Error checking if folder '{folder_name}' exists: {e}")
            return False

    def move_email(self, email_id: str, source_folder: str, destination_folder: str) -> bool:
        """
        Move an email from one folder to another.
        
        Args:
            email_id: ID of the email to move.
            source_folder: Source folder name.
            destination_folder: Destination folder name.
            
        Returns:
            bool: True if the move was successful, False otherwise.
        """
        if not self.connection:
            if not self.connect():
                return False
        
        # Check if destination folder actually exists by trying to select it
        if not self.folder_exists(destination_folder):
            logger.warning(f"Destination folder '{destination_folder}' does not exist. Please create it manually in Proton Mail.")
            logger.warning(f"Marking email as processed without moving it.")
            self.mark_as_processed(email_id)
            return False
        
        # Select source folder
        if self.select_folder(source_folder) <= 0:
            return False
        
        # Maximum number of retries
        max_retries = 3
        retry_delay = 2  # seconds
        
        for retry in range(max_retries):
            try:
                # Try to use the MOVE command directly if supported
                try:
                    logger.debug(f"Attempting to move email {email_id} using MOVE command")
                    # Check if MOVE is supported
                    capabilities = self.connection.capabilities
                    if b'MOVE' in capabilities:
                        logger.debug("Server supports MOVE command")
                        status, data = self.connection.uid('MOVE', email_id, destination_folder)
                        if status == 'OK':
                            logger.info(f"Successfully moved email {email_id} from {source_folder} to {destination_folder} using MOVE command")
                            return True
                    else:
                        logger.debug("Server does not support MOVE command, falling back to copy+delete")
                except Exception as e:
                    logger.debug(f"Error using MOVE command: {e}")
                
                # Fall back to copy+delete method
                # Try different formats for the destination folder
                formats_to_try = [
                    destination_folder,                # Standard format
                    f'"{destination_folder}"',         # Quoted format
                    f'INBOX/{destination_folder}',     # As a subfolder of INBOX with slash
                    f'INBOX.{destination_folder}',     # As a subfolder of INBOX with dot
                    f'Folders/{destination_folder}',   # As a subfolder of Folders
                    f'Labels/{destination_folder}',    # As a subfolder of Labels
                    destination_folder.upper(),        # Uppercase
                    destination_folder.lower()         # Lowercase
                ]
                
                copy_success = False
                for folder_format in formats_to_try:
                    try:
                        logger.debug(f"Trying to copy email to folder format: {folder_format}")
                        status, data = self.connection.copy(email_id, folder_format)
                        if status == 'OK':
                            logger.info(f"Successfully copied email {email_id} to {destination_folder} using format {folder_format}")
                            copy_success = True
                            break
                    except Exception as e:
                        logger.debug(f"Failed to copy email with format {folder_format}: {e}")
                        continue
                
                if not copy_success:
                    if retry < max_retries - 1:
                        logger.warning(f"Failed to copy email on attempt {retry+1}, retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        continue
                    else:
                        logger.error(f"Failed to copy email {email_id} to {destination_folder} with all attempted formats after {max_retries} retries")
                        # Mark as processed even if we couldn't move it
                        self.mark_as_processed(email_id)
                        return False
                
                # Mark the original email for deletion
                status, data = self.connection.store(email_id, '+FLAGS', '\\Deleted')
                if status != 'OK':
                    logger.error(f"Failed to mark email {email_id} for deletion: {data}")
                    # Even if deletion fails, we've at least copied the email
                    # Mark as processed and return partial success
                    self.mark_as_processed(email_id)
                    return True
                
                # Expunge to actually delete the email
                status, data = self.connection.expunge()
                if status != 'OK':
                    logger.error(f"Failed to expunge mailbox: {data}")
                    # Even if expunge fails, we've at least copied the email and marked for deletion
                    # Mark as processed and return partial success
                    self.mark_as_processed(email_id)
                    return True
                
                logger.info(f"Successfully moved email {email_id} from {source_folder} to {destination_folder}")
                return True
                
            except Exception as e:
                logger.error(f"Error moving email {email_id} (attempt {retry+1}): {e}")
                if retry < max_retries - 1:
                    logger.warning(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"Failed to move email after {max_retries} attempts")
                    # Mark as processed even if we couldn't move it
                    self.mark_as_processed(email_id)
                    return False
        
        return False

    def mark_as_processed(self, email_id: str) -> bool:
        """
        Mark an email as processed by adding a custom flag.
        
        Args:
            email_id: ID of the email to mark.
            
        Returns:
            bool: True if marking was successful, False otherwise.
        """
        if not self.connection:
            logger.error("Not connected to IMAP server")
            return False
        
        try:
            status, data = self.connection.store(email_id, '+FLAGS', 'PROCESSED')
            if status == 'OK':
                logger.info(f"Marked email {email_id} as processed")
                return True
            else:
                logger.error(f"Failed to mark email {email_id} as processed: {data}")
                return False
        except Exception as e:
            logger.error(f"Error marking email as processed: {e}")
            return False

    def process_emails(self, processor_func) -> Tuple[int, int]:
        """
        Process emails from configured folders using the provided processor function.
        
        Args:
            processor_func: Function that takes an email dict and returns a category.
            
        Returns:
            Tuple[int, int]: (Number of emails processed, number of emails successfully categorized)
        """
        if not self.connect():
            return 0, 0
        
        processed_count = 0
        success_count = 0
        
        # Check if we're in dry run mode (don't move emails, just classify)
        dry_run = os.environ.get('DRY_RUN', 'false').lower() == 'true'
        if dry_run:
            logger.info("Running in DRY RUN mode - emails will be classified but not moved")
        
        # Verify that destination folders exist
        folder_exists_cache = {}
        for category, folder_name in EMAIL_CATEGORIES.items():
            folder_exists_cache[folder_name] = self.folder_exists(folder_name)
            if not folder_exists_cache[folder_name]:
                logger.warning(f"Destination folder '{folder_name}' for category '{category}' does not exist.")
                logger.warning(f"Please create it manually in Proton Mail or emails will be classified but not moved.")
        
        try:
            for folder in self.folders_to_process:
                logger.info(f"Processing folder: {folder}")
                
                # Get unprocessed emails
                remaining = self.max_emails_per_run - processed_count
                if remaining <= 0:
                    break
                
                email_ids = self.get_unprocessed_emails(folder, limit=remaining)
                logger.info(f"Found {len(email_ids)} unprocessed emails in {folder}")
                
                # Process emails in batches
                for i in range(0, len(email_ids), self.batch_size):
                    batch = email_ids[i:i + self.batch_size]
                    
                    for email_id in batch:
                        email_data = self.fetch_email(email_id)
                        if not email_data:
                            continue
                        
                        processed_count += 1
                        
                        try:
                            # Call the processor function to get the category
                            category = processor_func(email_data)
                            
                            if category and category in EMAIL_CATEGORIES:
                                destination_folder = EMAIL_CATEGORIES[category]
                                
                                # Check if we should run in dry run mode
                                # Either explicitly enabled or the destination folder doesn't exist
                                should_dry_run = dry_run or not folder_exists_cache.get(destination_folder, False)
                                
                                if should_dry_run:
                                    # In dry run mode, just log the classification and mark as processed
                                    dry_run_reason = "DRY RUN mode" if dry_run else f"folder '{destination_folder}' does not exist"
                                    logger.info(f"[{dry_run_reason}] Email {email_id} - Subject: '{email_data.get('subject', '')}' - "
                                               f"From: '{email_data.get('sender', '')}' would be moved to {destination_folder}")
                                    self.mark_as_processed(email_id)
                                    success_count += 1
                                else:
                                    # Move the email to the appropriate folder
                                    if self.move_email(email_id, folder, destination_folder):
                                        success_count += 1
                                    else:
                                        # If move fails, at least mark as processed
                                        logger.warning(f"Failed to move email to {destination_folder}, marking as processed only")
                                        self.mark_as_processed(email_id)
                            else:
                                # Unknown category, just mark as processed
                                logger.warning(f"Unknown category '{category}' for email {email_id}")
                                self.mark_as_processed(email_id)
                        except Exception as e:
                            logger.error(f"Error processing email {email_id}: {e}")
                            # Mark as processed to avoid reprocessing
                            self.mark_as_processed(email_id)
                    
                    # Small delay between batches to avoid overwhelming the server
                    time.sleep(1)
        finally:
            self.disconnect()
        
        return processed_count, success_count
