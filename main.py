"""
Main entry point for the Email Classifier application.
"""
import argparse
import logging
import os
import sys
import time
from datetime import datetime

from config import LOGGING_CONFIG, EMAIL_CATEGORIES, PROCESSING_CONFIG
from email_processor import EmailProcessor
from classifier import EmailClassifier
from folder_manager import FolderManager

# Configure logging
def setup_logging():
    """Set up logging configuration."""
    log_level = getattr(logging, LOGGING_CONFIG['log_level'].upper(), logging.INFO)
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(LOGGING_CONFIG['log_file'])
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Configure logging
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.FileHandler(LOGGING_CONFIG['log_file']),
            logging.StreamHandler() if LOGGING_CONFIG['log_to_console'] else logging.NullHandler()
        ]
    )

# Main logger
logger = logging.getLogger(__name__)


def process_emails():
    """
    Process emails from the configured folders.
    
    Returns:
        tuple: (processed_count, success_count)
    """
    # Initialize components
    email_processor = EmailProcessor()
    classifier = EmailClassifier()
    folder_manager = FolderManager()
    
    # Ensure category folders exist
    if not folder_manager.ensure_category_folders_exist():
        logger.warning("Some category folders could not be created")
    
    # Test LLM connection
    if not classifier.test_llm_connection():
        logger.error("Failed to connect to LLM API")
        return 0, 0
    
    # Define the processor function that will be called for each email
    def classify_and_get_category(email_data):
        """Classify an email and return the category."""
        return classifier.classify_email(email_data)
    
    # Process emails
    return email_processor.process_emails(classify_and_get_category)


def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(description='Email Classifier')
    parser.add_argument('--test', action='store_true', help='Test connections without processing emails')
    parser.add_argument('--list-folders', action='store_true', help='List available email folders')
    parser.add_argument('--list-categories', action='store_true', help='List available categories')
    parser.add_argument('--add-category', nargs=2, metavar=('CATEGORY', 'FOLDER'), help='Add a new category and folder')
    parser.add_argument('--remove-category', metavar='CATEGORY', help='Remove a category')
    parser.add_argument('--process', action='store_true', help='Process emails (default action)')
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging()
    
    logger.info("Starting Email Classifier")
    
    try:
        # Test connections
        if args.test:
            logger.info("Testing connections...")
            
            # Test email connection
            email_processor = EmailProcessor()
            if email_processor.connect():
                logger.info("Email connection successful")
                email_processor.disconnect()
            else:
                logger.error("Email connection failed")
            
            # Test LLM connection
            classifier = EmailClassifier()
            if classifier.test_llm_connection():
                logger.info("LLM connection successful")
            else:
                logger.error("LLM connection failed")
            
            return
        
        # List folders
        if args.list_folders:
            folder_manager = FolderManager()
            folders = folder_manager.get_available_folders()
            
            if folders:
                logger.info("Available folders:")
                for folder in folders:
                    print(f"- {folder}")
            else:
                logger.warning("No folders found or failed to retrieve folders")
            
            return
        
        # List categories
        if args.list_categories:
            classifier = EmailClassifier()
            categories = classifier.get_available_categories()
            
            if categories:
                logger.info("Available categories:")
                for category in categories:
                    folder = EMAIL_CATEGORIES.get(category, "Unknown")
                    print(f"- {category} -> {folder}")
            else:
                logger.warning("No categories found")
            
            return
        
        # Add category
        if args.add_category:
            category, folder = args.add_category
            
            folder_manager = FolderManager()
            classifier = EmailClassifier()
            
            if folder_manager.add_category_folder(category, folder) and classifier.add_category(category, folder):
                logger.info(f"Added category '{category}' with folder '{folder}'")
            else:
                logger.error(f"Failed to add category '{category}' with folder '{folder}'")
            
            return
        
        # Remove category
        if args.remove_category:
            category = args.remove_category
            
            folder_manager = FolderManager()
            classifier = EmailClassifier()
            
            if folder_manager.remove_category_folder(category) and classifier.remove_category(category):
                logger.info(f"Removed category '{category}'")
            else:
                logger.error(f"Failed to remove category '{category}'")
            
            return
        
        # Process emails (default action)
        if args.process or not any([args.test, args.list_folders, args.list_categories, args.add_category, args.remove_category]):
            start_time = time.time()
            processed_count, success_count = process_emails()
            end_time = time.time()
            
            logger.info(f"Processed {processed_count} emails, {success_count} successfully categorized")
            logger.info(f"Processing took {end_time - start_time:.2f} seconds")
    
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1
    
    logger.info("Email Classifier completed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
