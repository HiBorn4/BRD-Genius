import os
import json
import logging
from typing import List, Dict, Any, Optional
from .core_chatbot import Chatbot
from .file_manager import FileStorageManager
import config

storage = config.storage_type

filemanager= FileStorageManager(storage)

class ChatbotAPI:
    def __init__(self):
        self.active_chatbots = {}
    
    def initialize_chatbot(self, user_id, unique_id: str, chatbot_history: Optional[List[Dict]] = None) -> Dict[str, Any]:
        try:
            
            # Handle chat history
            if chatbot_history is None:
                chatbot_history = [
                    {
                        "type": "human",
                        "data": {
                        "content": "hi bhavya"
                        }
                    }
                ]
            
            # Save the chat history to the memory file if provided
            if chatbot_history and len(chatbot_history) > 1:  # More than just the default "hi bhavya"
                self._save_history_to_memory(user_id, unique_id, chatbot_history)
            
            # Initialize chatbot
            if unique_id not in self.active_chatbots:
                self.active_chatbots[unique_id] = Chatbot(user_id=user_id,unique_id=unique_id)
            
            chatbot_instance = self.active_chatbots[unique_id]
            
            # If this is a fresh session (only "hi bhavya"), get initial prompt
            if len(chatbot_history) == 1 and chatbot_history[0]["data"]["content"] == "hi bhavya":
                initial_response = chatbot_instance.run_chatbot("Ask me questions regarding the BRD/FRD analysis")
                
                # Create the updated history (removing "hi bhavya" and adding the initial exchange)
                updated_history = [
                    {
                        "type": "human",
                        "data" : {
                            "content": "Ask me questions regarding the BRD/FRD analysis"
                            }
                    },
                    {
                        "type": "ai",
                        "data": {
                            "content": initial_response
                        }
                    }
                ]

                # Save the updated history to memory
                self._save_history_to_memory(user_id, unique_id, updated_history)
                
                return {
                    "status": "success",
                    "bot_response": initial_response,
                    "session_id": unique_id,
                    "chat_history": self.get_chat_history(user_id, unique_id)
                }
            else:
                # Return the last bot message from existing history
                last_bot_message = ""
                for i in range(len(chatbot_history) - 1, -1, -1):
                    if chatbot_history[i]["type"] == "ai":
                        last_bot_message = chatbot_history[i]["content"]
                        break

                return {
                    "status": "success",
                    "bot_response": last_bot_message,
                    "session_id": unique_id,
                    "chat_history": self.get_chat_history(user_id, unique_id)
                }
                
        except Exception as e:
            logging.error(f"Error initializing chatbot: {e}")
            return {
                "status": "error",
                "error": str(e),
                "bot_response": "Failed to initialize chatbot. Please try again."
            }
    
    def send_message(self, user_id, unique_id: str, user_message: str, chatbot_history: List[Dict]) -> Dict[str, Any]:
        """
        Send a message to the chatbot and get response.
        
        Args:
            unique_id: Unique identifier for the chatbot session
            user_message: User's message
            chatbot_history: Current chat history
            
        Returns:
            Dict containing bot response and updated history
        """
        try:
            # Get or create chatbot instance
            if unique_id not in self.active_chatbots:
                self.active_chatbots[unique_id] = Chatbot(user_id=user_id,unique_id=unique_id)
            
            chatbot_instance = self.active_chatbots[unique_id]
            chatbot_history = chatbot_history
            # Regular message processing
            bot_response = chatbot_instance.run_chatbot(user_message)
            
            # Create updated history
            updated_history = chatbot_history.copy()
            updated_history.append({
                "type": "human",
                "data": {
                    "content": user_message
                }
            })
            updated_history.append({
                "type": "ai",
                "data": {
                    "content": bot_response
                }
            })
            
            return {
                "status": "success",
                "bot_response": bot_response,
                "session_id": unique_id,
                "chat_history": self.get_chat_history(user_id, unique_id)
            }
            
        except Exception as e:
            logging.error(f"Error processing message: {e}")
            return {
                "status": "error",
                "error": str(e),
                "bot_response": "An error occurred while processing your message. Please try again."
            }
    
    def _save_history_to_memory(self, user_id, unique_id: str, chatbot_history: List[Dict]):
        """
        Convert the chatbot history format to the internal memory format and save it.
        """
        try:
            # Convert to the internal memory format
            memory_data = []
            for entry in chatbot_history:
                if entry["type"] == "human":
                    memory_data.append({
                        "type": "human",
                        "data" : {
                            "content": entry["content"] 
                        }
                    })
                elif entry["type"] == "ai":
                    memory_data.append({
                        "type": "ai",
                        "data": {
                            "content": entry["content"]
                        }
                    })
            
            chatbot_memory_path = self.filemanager.save_json_file(
                user_id=user_id,
                unique_id=unique_id,
                filename="chatbot.json",
                content=memory_data
            )

            
            
            logging.info(f"Chat history saved to memory: {chatbot_memory_path}")
            
        except Exception as e:
            logging.error(f"Error saving history to memory: {e}")
    
    def get_chat_history(self, user_id:str, unique_id: str) -> List[Dict]:
        """
        Get chat history from JSON file and return it as a list of {'human': ..., 'ai': ...} pairs.
        """
        try:
            raw_data = filemanager.read_json_file(user_id, unique_id, filename='chatbot.json')

            if not isinstance(raw_data, list):
                logging.warning("Chat history data is not a list")
                return []

            paired_history = []
            current_pair = {}

            for entry in raw_data:
                message_type = entry.get("type")
                content = entry.get("data", {}).get("content")

                if message_type == "human":
                    current_pair = {"human": content}
                elif message_type == "ai" and "human" in current_pair:
                    current_pair["ai"] = content
                    paired_history.append(current_pair)
                    current_pair = {}

            return paired_history

        except Exception as e:
            logging.error(f"Error getting chat history: {e}")
            return []

        except Exception as e:
            logging.error(f"Error getting chat history: {e}")
            return []


# Global instance for the API
chatbot_api = ChatbotAPI()

# Main API functions to be called from main.py
def initialize_chatbot_session(user_id, unique_id: str) -> Dict[str, Any]:
    """
    Initialize a chatbot session.
    
    Args:
        unique_id: Unique identifier for the session
        chatbot_history: Optional chat history (defaults to [{"type": "human", "content": "hi bhavya"}])
    
    Returns:
        Dict with status, bot_response, updated_history, and session_id
    """
    return chatbot_api.initialize_chatbot(user_id, unique_id)

def send_message_to_chatbot(user_id, unique_id: str, user_message: str) -> Dict[str, Any]:
    """
    Send a message to the chatbot.
    
    Args:
        unique_id: Unique identifier for the session
        user_message: User's message
        chatbot_history: Current chat history
    
    Returns:
        Dict with status, bot_response, and session_id
    """
    chatbot_history = filemanager.read_json_file(user_id=user_id,unique_id=unique_id,filename="chatbot.json")
    return chatbot_api.send_message(user_id, unique_id, user_message, chatbot_history)