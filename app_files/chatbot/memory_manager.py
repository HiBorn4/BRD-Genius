import os
import json
import logging
from typing import List
from langchain.memory import ConversationBufferWindowMemory
from langchain.schema import messages_to_dict
from .file_manager import FileStorageManager
import config

storage = config.storage_type

filemanger = FileStorageManager(storage)  # Initialize file manager for local storage

def save_chat_memory(user_id, unique_id, memory: ConversationBufferWindowMemory, unique_id_folder: str):
    """
    Saves the current chat history to a JSON file for the current session.
    """
    chatbot_memory_path = os.path.join(unique_id_folder, "chatbot.json")
    try:
        memory_data = memory.chat_memory.messages
        ingest_to_db = messages_to_dict(memory_data)
        filemanger.save_json_file(user_id,unique_id,"chatbot.json", content=ingest_to_db)
        
        logging.info(f"Chat memory saved to: {chatbot_memory_path}")
    except Exception as e:
        logging.error(f"Error saving chat memory to {chatbot_memory_path}: {e}")

def return_chat_history_for_display(user_id, unique_id) -> List[dict]:
    """
    Converts the raw chat memory into a user-friendly format for display.
    """
    

    try:
        memory_data = filemanger.read_json_file(user_id, unique_id, filename="chatbot.json")
    except (json.JSONDecodeError, Exception) as e:
        logging.error(f"Error loading or decoding chat memory for history display from chatbot_memory_path: {e}")
        return []

    converted_data = []
    for i in range(0, len(memory_data), 2):
        human_entry = memory_data[i]
        ai_entry = memory_data[i + 1] if (i + 1) < len(memory_data) else None

        if not ai_entry:
            continue

        user_message = human_entry.get("data", {}).get("content", "")
        ai_content_str = ai_entry.get("data", {}).get("content", "")

        bot_message = ""
        if ai_content_str:
            try:
                ai_parsed = json.loads(ai_content_str)
                bot_message = ai_parsed.get("content", ai_content_str)
            except json.JSONDecodeError:
                bot_message = ai_content_str

        converted_data.append({"user": user_message, "bot": bot_message})

    logging.info("Chat history converted for display.")
    return converted_data