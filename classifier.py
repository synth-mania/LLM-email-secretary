"""
Core classification logic for categorizing emails using the LLM.
"""
import logging
from typing import Dict, Any, Optional, List

from config import EMAIL_CATEGORIES
from llm_client import LLMClient

# Configure logging
logger = logging.getLogger(__name__)


class EmailClassifier:
    """
    Handles the classification of emails into predefined categories using an LLM.
    """

    def __init__(self):
        """Initialize the email classifier."""
        self.llm_client = LLMClient()
        self.categories = list(EMAIL_CATEGORIES.keys())
        logger.info(f"Initialized classifier with categories: {self.categories}")

    def test_llm_connection(self) -> bool:
        """
        Test the connection to the LLM API.
        
        Returns:
            bool: True if the connection is successful, False otherwise.
        """
        return self.llm_client.test_connection()

    def classify_email(self, email_data: Dict[str, Any]) -> Optional[str]:
        """
        Classify an email into one of the predefined categories.
        
        Args:
            email_data: Dictionary containing email data.
            
        Returns:
            Optional[str]: The predicted category, or None if classification failed.
        """
        if not email_data:
            logger.error("Cannot classify empty email data")
            return None
        
        try:
            # Extract relevant email information for logging
            email_id = email_data.get('id', 'unknown')
            subject = email_data.get('subject', '')
            sender = email_data.get('sender', '')
            
            logger.info(f"Classifying email {email_id} - Subject: '{subject}' - From: '{sender}'")
            
            # Use the LLM client to classify the email
            category = self.llm_client.classify_email(email_data, self.categories)
            
            if category:
                logger.info(f"Email {email_id} classified as '{category}'")
                return category
            else:
                logger.warning(f"Failed to classify email {email_id}")
                # Default to 'requires_manual_intervention' if classification fails
                return 'requires_manual_intervention'
        except Exception as e:
            logger.error(f"Error during classification: {e}")
            # Default to 'requires_manual_intervention' on error
            return 'requires_manual_intervention'

    def get_available_categories(self) -> List[str]:
        """
        Get the list of available categories.
        
        Returns:
            List[str]: List of category names.
        """
        return self.categories

    def add_category(self, category: str, folder: str) -> bool:
        """
        Add a new category to the classifier.
        
        Args:
            category: Name of the category.
            folder: Name of the folder to move emails to.
            
        Returns:
            bool: True if the category was added successfully, False otherwise.
        """
        if category in self.categories:
            logger.warning(f"Category '{category}' already exists")
            return False
        
        try:
            # Add the category to the list
            self.categories.append(category)
            
            # Add the category to the EMAIL_CATEGORIES dictionary
            EMAIL_CATEGORIES[category] = folder
            
            logger.info(f"Added category '{category}' with folder '{folder}'")
            return True
        except Exception as e:
            logger.error(f"Error adding category: {e}")
            return False

    def remove_category(self, category: str) -> bool:
        """
        Remove a category from the classifier.
        
        Args:
            category: Name of the category to remove.
            
        Returns:
            bool: True if the category was removed successfully, False otherwise.
        """
        if category not in self.categories:
            logger.warning(f"Category '{category}' does not exist")
            return False
        
        if category == 'requires_manual_intervention':
            logger.error("Cannot remove the 'requires_manual_intervention' category")
            return False
        
        try:
            # Remove the category from the list
            self.categories.remove(category)
            
            # Remove the category from the EMAIL_CATEGORIES dictionary
            if category in EMAIL_CATEGORIES:
                del EMAIL_CATEGORIES[category]
            
            logger.info(f"Removed category '{category}'")
            return True
        except Exception as e:
            logger.error(f"Error removing category: {e}")
            return False
