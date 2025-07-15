"""
Client for interacting with an OpenAI-compatible LLM API.
"""
import json
import logging
import requests
from typing import Dict, Any, Optional

from config import LLM_CONFIG

# Configure logging
logger = logging.getLogger(__name__)


class LLMClient:
    """
    Client for interacting with an OpenAI-compatible LLM API.
    Supports local LLM servers like llama.cpp or ollama that implement the OpenAI API format.
    """

    def __init__(self):
        """Initialize the LLM client with configuration from config.py."""
        self.api_endpoint = LLM_CONFIG['api_endpoint']
        self.api_key = LLM_CONFIG['api_key']
        self.model = LLM_CONFIG['model']
        self.temperature = LLM_CONFIG['temperature']
        self.max_tokens = LLM_CONFIG['max_tokens']
        self.timeout = LLM_CONFIG['timeout']
        
        # Ensure the API endpoint ends with a slash if it doesn't already
        if not self.api_endpoint.endswith('/'):
            self.api_endpoint += '/'
        
        # Set up headers for API requests
        self.headers = {
            'Content-Type': 'application/json'
        }
        
        # Add API key to headers if provided
        if self.api_key:
            self.headers['Authorization'] = f'Bearer {self.api_key}'

    def _build_completion_url(self) -> str:
        """
        Build the URL for the completions endpoint.
        
        Returns:
            str: The completions API URL.
        """
        return f"{self.api_endpoint}completions"

    def _build_chat_url(self) -> str:
        """
        Build the URL for the chat completions endpoint.
        
        Returns:
            str: The chat completions API URL.
        """
        return f"{self.api_endpoint}chat/completions"

    def get_completion(self, prompt: str) -> Optional[str]:
        """
        Get a completion from the LLM using the completions endpoint.
        
        Args:
            prompt: The prompt to send to the LLM.
            
        Returns:
            Optional[str]: The generated text, or None if the request failed.
        """
        url = self._build_completion_url()
        
        payload = {
            'model': self.model,
            'prompt': prompt,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens
        }
        
        try:
            response = requests.post(
                url,
                headers=self.headers,
                data=json.dumps(payload),
                timeout=self.timeout
            )
            
            response.raise_for_status()
            result = response.json()
            
            if 'choices' in result and len(result['choices']) > 0:
                return result['choices'][0].get('text', '').strip()
            else:
                logger.error(f"Unexpected response format: {result}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting completion: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding response: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None

    def get_chat_completion(self, messages: list) -> Optional[str]:
        """
        Get a completion from the LLM using the chat completions endpoint.
        
        Args:
            messages: List of message objects in the format expected by the chat API.
            
        Returns:
            Optional[str]: The generated text, or None if the request failed.
        """
        url = self._build_chat_url()
        
        payload = {
            'model': self.model,
            'messages': messages,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens
        }
        
        try:
            response = requests.post(
                url,
                headers=self.headers,
                data=json.dumps(payload),
                timeout=self.timeout
            )
            
            response.raise_for_status()
            result = response.json()
            
            if 'choices' in result and len(result['choices']) > 0:
                return result['choices'][0].get('message', {}).get('content', '').strip()
            else:
                logger.error(f"Unexpected response format: {result}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting chat completion: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding response: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None

    def classify_email(self, email_data: Dict[str, Any], categories: list) -> Optional[str]:
        """
        Classify an email into one of the provided categories using the LLM.
        
        Args:
            email_data: Dictionary containing email data.
            categories: List of category names.
            
        Returns:
            Optional[str]: The predicted category, or None if classification failed.
        """
        from config import CLASSIFICATION_PROMPT_TEMPLATE
        
        # Format the categories as a comma-separated list
        categories_str = ", ".join([f"'{cat}'" for cat in categories])
        
        # Format the prompt using the template from config
        prompt = CLASSIFICATION_PROMPT_TEMPLATE.format(
            categories=categories_str,
            subject=email_data.get('subject', ''),
            sender=email_data.get('sender', ''),
            date=email_data.get('date', ''),
            body=email_data.get('body', '')[:10000]  # Limit body length to avoid token limits
        )
        
        # Try chat completion first, fall back to regular completion if it fails
        messages = [
            {"role": "system", "content": "You are an email classification assistant."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            result = self.get_chat_completion(messages)
            if not result:
                logger.warning("Chat completion failed, falling back to regular completion")
                result = self.get_completion(prompt)
            
            if result:
                # Clean up the result to extract just the category name
                result = result.strip().lower()
                
                # Check if the result matches any of the categories
                for category in categories:
                    if category.lower() in result:
                        return category
                
                logger.warning(f"LLM response '{result}' doesn't match any category")
                return None
            else:
                logger.error("Failed to get a response from the LLM")
                return None
        except Exception as e:
            logger.error(f"Error classifying email: {e}")
            return None

    def test_connection(self) -> bool:
        """
        Test the connection to the LLM API.
        
        Returns:
            bool: True if the connection is successful, False otherwise.
        """
        try:
            # Simple test prompt
            test_prompt = "Hello, this is a test."
            
            # Try chat completion first
            messages = [
                {"role": "user", "content": test_prompt}
            ]
            
            result = self.get_chat_completion(messages)
            if result is not None:
                logger.info("Successfully connected to LLM API (chat)")
                return True
            
            # Fall back to regular completion
            result = self.get_completion(test_prompt)
            if result is not None:
                logger.info("Successfully connected to LLM API (completion)")
                return True
            
            logger.error("Failed to get a response from the LLM API")
            return False
        except Exception as e:
            logger.error(f"Error testing LLM connection: {e}")
            return False
