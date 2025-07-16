#!/usr/bin/env python3
"""
Script to create the necessary folders for email classification.
"""
import logging
import sys
import os
from email_processor import EmailProcessor
from config import EMAIL_CATEGORIES

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def create_category_folders():
    """Create folders for each email category if they don't exist."""
    processor = EmailProcessor()
    
    if not processor.connect():
        logger.error("Failed to connect to email server")
        return False
    
    try:
        # Get existing folders
        existing_folders = processor.get_folders()

        for existing_folder in existing_folders:
            print(f"Found existing folder: {existing_folder}\n")

        logger.info(f"Existing folders: {existing_folders}")
        
        # Create folders for each category
        success = True
        for category, folder_name in EMAIL_CATEGORIES.items():
            if folder_name in existing_folders:
                logger.info(f"Folder '{folder_name}' for category '{category}' already exists")
                continue
            
            logger.info(f"Creating folder '{folder_name}' for category '{category}'")
            if processor.create_folder_if_not_exists(folder_name):
                logger.info(f"Successfully created folder '{folder_name}'")
            else:
                logger.error(f"Failed to create folder '{folder_name}'")
                success = False
        
        return success
    finally:
        processor.disconnect()

if __name__ == "__main__":
    logger.info("Creating category folders...")
    if create_category_folders():
        logger.info("All category folders created successfully")
    else:
        logger.warning("Some category folders could not be created")
