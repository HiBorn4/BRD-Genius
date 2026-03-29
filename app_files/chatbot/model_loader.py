import logging
from langchain.chat_models import init_chat_model
import config

model_name = config.chatbot_model

def load_bedrock_model():
    try:
        # Using anthropic.claude-3-5-sonnet-20240620-v1:0 as specified in your original snippet
        model = init_chat_model(
            model_name, 
            model_provider="bedrock", 
            model_kwargs=dict(max_tokens=1024*5, temperature=0)
        )
        logging.info("Chatbot model loaded (Amazon Bedrock).")
        return model
    except Exception as e:
        logging.error(f"Error loading Bedrock model: {e}")
        raise