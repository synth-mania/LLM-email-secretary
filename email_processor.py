"""
Email processing module for fetching and manipulating emails via IMAP.
"""
import imaplib
import email
from email.header import decode_header
import logging
import re
from typing import List, Dict, Tuple, Optional, Any
import time

from config import EMAIL_CONFIG, PROCESSING_CONFIG

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
            if self.use_ssl:
                # Use SSL/TLS from the beginning
                self.connection = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            else:
                # Start with plain connection, STARTTLS will be used if supported by server
                self.connection = imaplib.IMAP4(self.imap_server, self.imap_port)
                # Note: imaplib.IMAP4 automatically handles STARTTLS if the server supports it
            
            self.connection.login(self.username, self.password)
            logger.info(f"Successfully connected to {self.imap_server}")
            return True
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
                    folder = folder.decode('utf-8')
                # Extract folder name using regex
                match = re.search(r'"([^"]*)"$', folder)
                if match:
                    folder_list.append(match.group(1))
            
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
            
            status, response = self.connection.create(f'"{folder_name}"')
            if status == 'OK':
                logger.info(f"Created folder: {folder_name}")
                return True
            else:
                logger.error(f"Failed to create folder {folder_name}: {response}")
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
            status, data = self.connection.select(f'"{folder_name}"')
            if status == 'OK':
                message_count = int(data[0])
                logger.info(f"Selected folder {folder_name} with {message_count} messages")
                return message_count
            else:
                logger.error(f"Failed to select folder {folder_name}: {data}")
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
            # Search for emails without our processed flag
            email_ids = self.search_emails('NOT KEYWORD "PROCESSED"')
        
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
        
        # Ensure destination folder exists
        if not self.create_folder_if_not_exists(destination_folder):
            return False
        
        # Select source folder
        if self.select_folder(source_folder) <= 0:
            return False
        
        try:
            # Copy the email to the destination folder
            status, data = self.connection.copy(email_id, f'"{destination_folder}"')
            if status != 'OK':
                logger.error(f"Failed to copy email {email_id} to {destination_folder}: {data}")
                return False
            
            # Mark the original email for deletion
            status, data = self.connection.store(email_id, '+FLAGS', '\\Deleted')
            if status != 'OK':
                logger.error(f"Failed to mark email {email_id} for deletion: {data}")
                return False
            
            # Expunge to actually delete the email
            status, data = self.connection.expunge()
            if status != 'OK':
                logger.error(f"Failed to expunge mailbox: {data}")
                return False
            
            logger.info(f"Successfully moved email {email_id} from {source_folder} to {destination_folder}")
            return True
        except Exception as e:
            logger.error(f"Error moving email {email_id}: {e}")
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
                                
                                # Move the email to the appropriate folder
                                if self.move_email(email_id, folder, destination_folder):
                                    success_count += 1
                                else:
                                    # If move fails, at least mark as processed
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
