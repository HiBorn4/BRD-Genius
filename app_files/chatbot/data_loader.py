import os
import json
import logging
from langchain.memory import ChatMessageHistory
from langchain.schema import messages_from_dict
from .file_manager import FileStorageManager
import config

storage = config.storage_type

filemanger= FileStorageManager(storage)  # Initialize file manager for local storage 

def load_brd_qa(user_id,unique_id) -> str:
    """
    Loads the BRD Questions
    """
    try:
        brd_frd_qa_results=filemanger.read_file(user_id,unique_id,"brd_questions.json")
        brd_qa_json_path =  "brd_questions.json"
    
        logging.info(f"Loaded BRD Questions from: {brd_qa_json_path}")
        return brd_frd_qa_results
    except FileNotFoundError:
        logging.error(f"BRD Questions file not found: {brd_qa_json_path}")
        return json.dumps({"error": "BRD Questions not found"})
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from BRD questions: {brd_qa_json_path}")
        return json.dumps({"error": "Invalid JSON in BRD questions"})
    except Exception as e:
        logging.error(f"Unexpected error loading BRD questions: {e}")
        return json.dumps({"error": f"Error loading questions : {str(e)}"})

def load_system_prompt_template() -> str:
    """
    Loads the system prompt template for the chatbot.
    """
    system_prompt_template_path = config.l4_prompt
    try:
        with open(system_prompt_template_path, 'r', encoding='utf-8') as f:
            system_prompt_template = f.read()
        logging.info(f"Loaded system prompt template from: {system_prompt_template_path}")
        return system_prompt_template
    except FileNotFoundError:
        logging.warning(f"System prompt template not found: {system_prompt_template_path}.")
    except Exception as e:
        logging.error(f"Error loading system prompt template: {e}")
        return "You are an AI assistant. Error loading system prompt."

def load_chat_memory(user_id,unique_id: str) -> ChatMessageHistory:
    """
    Loads chat history from a JSON file for the current session.
    """

    if filemanger.read_json_file(user_id,unique_id,"chatbot.json") is None:
        logging.info("No existing chat memory found. Starting fresh.")
        memory_data = {}
    else:
        try:
            memory_data = filemanger.read_json_file(user_id, unique_id, "chatbot.json")
            chatbot_memory_path =  "chatbot.json"
            logging.info(f"Loaded chat memory from: {chatbot_memory_path}")
        except json.JSONDecodeError:
            logging.error(f"Error decoding chat memory JSON from {chatbot_memory_path}. Starting fresh.")
            memory_data = {}
        except Exception as e:
            logging.error(f"Unexpected error loading chat memory: {e}. Starting fresh.")
            memory_data = {}
    
    retrieved_messages = messages_from_dict(memory_data)
    retrieved_chat_history = ChatMessageHistory(messages=retrieved_messages)
    return retrieved_chat_history