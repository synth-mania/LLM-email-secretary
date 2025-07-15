"""
Logic for managing email folders and moving emails between them.
"""
import logging
from typing import List, Dict, Optional

from email_processor import EmailProcessor
from config import EMAIL_CATEGORIES

# Configure logging
logger = logging.getLogger(__name__)


class FolderManager:
    """
    Manages email folders and handles moving emails between folders.
    """

    def __init__(self):
        """Initialize the folder manager."""
        self.email_processor = EmailProcessor()
        self.category_folders = EMAIL_CATEGORIES

    def ensure_category_folders_exist(self) -> bool:
        """
        Check if all folders for the defined categories exist.
        Note: This method does not create folders, as Proton Mail Bridge has limitations on folder creation.
        Users must create the folders manually through the Proton Mail interface.
        
        Returns:
            bool: True if all folders exist, False otherwise.
        """
        if not self.email_processor.connect():
            logger.error("Failed to connect to email server")
            return False
        
        success = True
        try:
            folders = self.email_processor.get_folders()
            for category, folder_name in self.category_folders.items():
                if folder_name not in folders:
                    logger.warning(f"Folder '{folder_name}' for category '{category}' does not exist. Please create it manually in Proton Mail.")
                    success = False
        finally:
            self.email_processor.disconnect()
        
        return success

    def get_available_folders(self) -> List[str]:
        """
        Get a list of all available folders in the mailbox.
        
        Returns:
            List[str]: List of folder names.
        """
        if not self.email_processor.connect():
            logger.error("Failed to connect to email server")
            return []
        
        try:
            folders = self.email_processor.get_folders()
            logger.info(f"Found {len(folders)} folders")
            return folders
        finally:
            self.email_processor.disconnect()

    def create_folder(self, folder_name: str) -> bool:
        """
        Create a new folder in the mailbox.
        
        Args:
            folder_name: Name of the folder to create.
            
        Returns:
            bool: True if the folder was created successfully, False otherwise.
        """
        if not self.email_processor.connect():
            logger.error("Failed to connect to email server")
            return False
        
        try:
            result = self.email_processor.create_folder_if_not_exists(folder_name)
            if result:
                logger.info(f"Created folder: {folder_name}")
            else:
                logger.error(f"Failed to create folder: {folder_name}")
            return result
        finally:
            self.email_processor.disconnect()

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
        if not self.email_processor.connect():
            logger.error("Failed to connect to email server")
            return False
        
        try:
            result = self.email_processor.move_email(email_id, source_folder, destination_folder)
            if result:
                logger.info(f"Moved email {email_id} from {source_folder} to {destination_folder}")
            else:
                logger.error(f"Failed to move email {email_id} from {source_folder} to {destination_folder}")
            return result
        finally:
            self.email_processor.disconnect()

    def get_folder_for_category(self, category: str) -> Optional[str]:
        """
        Get the folder name for a given category.
        
        Args:
            category: Category name.
            
        Returns:
            Optional[str]: Folder name for the category, or None if the category doesn't exist.
        """
        return self.category_folders.get(category)

    def add_category_folder(self, category: str, folder_name: str) -> bool:
        """
        Add a new category and associated folder.
        
        Args:
            category: Category name.
            folder_name: Folder name.
            
        Returns:
            bool: True if the category and folder were added successfully, False otherwise.
        """
        if category in self.category_folders:
            logger.warning(f"Category '{category}' already exists")
            return False
        
        # Create the folder if it doesn't exist
        if not self.create_folder(folder_name):
            return False
        
        # Add the category to the dictionary
        self.category_folders[category] = folder_name
        logger.info(f"Added category '{category}' with folder '{folder_name}'")
        return True

    def remove_category_folder(self, category: str) -> bool:
        """
        Remove a category from the manager.
        
        Args:
            category: Category name to remove.
            
        Returns:
            bool: True if the category was removed successfully, False otherwise.
        """
        if category not in self.category_folders:
            logger.warning(f"Category '{category}' does not exist")
            return False
        
        if category == 'requires_manual_intervention':
            logger.error("Cannot remove the 'requires_manual_intervention' category")
            return False
        
        # Remove the category from the dictionary
        del self.category_folders[category]
        logger.info(f"Removed category '{category}'")
        return True

    def update_category_folder(self, category: str, new_folder_name: str) -> bool:
        """
        Update the folder associated with a category.
        
        Args:
            category: Category name.
            new_folder_name: New folder name.
            
        Returns:
            bool: True if the category was updated successfully, False otherwise.
        """
        if category not in self.category_folders:
            logger.warning(f"Category '{category}' does not exist")
            return False
        
        # Create the folder if it doesn't exist
        if not self.create_folder(new_folder_name):
            return False
        
        # Update the category in the dictionary
        self.category_folders[category] = new_folder_name
        logger.info(f"Updated category '{category}' to use folder '{new_folder_name}'")
        return True
