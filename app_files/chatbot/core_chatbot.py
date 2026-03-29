import os
import json
from typing import List
import logging
import re

from langchain.memory import ConversationBufferWindowMemory

from .model_loader import load_bedrock_model
from .data_loader import load_brd_qa, load_system_prompt_template, load_chat_memory
from .prompt_builder import build_question_prompt
from .memory_manager import save_chat_memory, return_chat_history_for_display

class Chatbot:
    def __init__(self, user_id, unique_id: str):
        self.unique_id = unique_id
        self.user_id=user_id
        self.unique_id_folder = os.path.join("app_files/middleware", unique_id)
        os.makedirs(self.unique_id_folder, exist_ok=True)

        try:
            self.model = load_bedrock_model()
            self.brd_questions = load_brd_qa(self.user_id, self.unique_id)
            self.system_prompt_template = load_system_prompt_template()
            self.question_prompt = build_question_prompt(self.system_prompt_template, self.brd_questions)
            self.history_window = 20

            retrieved_chat_memory = load_chat_memory(self.user_id, self.unique_id)
            self.memory = ConversationBufferWindowMemory(
                k=self.history_window,
                return_messages=True,
                chat_memory=retrieved_chat_memory
            )

            self.chain = self.question_prompt | self.model
            self.last_bot_question = None
            logging.info(f"Chatbot initialized successfully for unique_id: {unique_id}")

        except Exception as e:
            logging.error(f"Error initializing chatbot: {e}")
            raise

    def run_chatbot(self, user_input: str) -> str:
        # Default case: user input sent to model
        try:
            input_data = {
                "input": user_input,
                "brd_questions": self.brd_questions,
                "history": self.memory.buffer_as_messages
            }

            logging.info(f"Invoking model with input: {user_input[:100]}...")
            response = self.chain.invoke(input_data)

            # Extract response content
            if hasattr(response, 'content'):
                res_content = response.content
            else:
                res_content = str(response)

            logging.info(f"Model response received: {res_content[:200]}...")

            # Attempt to extract and parse JSON from model output
            try:
                json_match = re.search(r'({[\s\S]*})', res_content)
                if not json_match:
                    self.last_bot_question = res_content
                    self.memory.save_context({"input": user_input}, {"output": res_content})
                    save_chat_memory(self.user_id,self.unique_id,self.memory, self.unique_id_folder)
                    return res_content

                json_str = json_match.group(1)
                json_str = json_str.replace("{{", "{").replace("}}", "}")
                json_str = re.sub(r"(\w+):", r'"\1":', json_str)
                json_str = json_str.replace("'", '"')

                parsed_response = json.loads(json_str)
            except json.JSONDecodeError as e:
                logging.warning(f"JSON decode error: {e}. Treating as plain text.")
                self.last_bot_question = res_content
                self.memory.save_context({"input": user_input}, {"output": res_content})
                save_chat_memory(self.user_id, self.unique_id, self.memory, self.unique_id_folder)
                return res_content

            response_content = parsed_response.get("content", "No content available")
            response_type = parsed_response.get("type")

            self.last_bot_question = response_content
            self.memory.save_context({"input": user_input}, {"output": json.dumps(parsed_response)})
            save_chat_memory(self.user_id, self.unique_id, self.memory, self.unique_id_folder)

            return response_content

        except Exception as e:
            logging.error(f"Unexpected error in run_chatbot: {e}", exc_info=True)
            if "404" in str(e) or "Resource not found" in str(e):
                return (
                    "Configuration Error: Please check your Azure OpenAI settings:\n"
                    "- AZURE_OPENAI_ENDPOINT\n"
                    "- AZURE_OPENAI_API_KEY\n"
                    "- AZURE_OPENAI_DEPLOYMENT_NAME\n"
                    "- AZURE_OPENAI_API_VERSION"
                )
            elif "401" in str(e) or "Unauthorized" in str(e):
                return "Authentication Error: Please check your Azure OpenAI API key."
            else:
                return f"An internal error occurred. Please try again. Error: {str(e)}"

    def get_chat_history(self) -> List[dict]:
        try:
            return return_chat_history_for_display(self.user_id, self.unique_id)
        except Exception as e:
            logging.error(f"Error getting chat history: {e}")
            return []
