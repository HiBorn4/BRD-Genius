import os
import json
from openai import AzureOpenAI
import config

# Load env variables
OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")

# Azure OpenAI client
client = AzureOpenAI(
    api_key=OPENAI_API_KEY,
    azure_endpoint=OPENAI_ENDPOINT,
    api_version=config.azure_api_version
)

def clean_chatbot_data(chatbot_data):
    """Clean and simplify the chatbot.json data structure."""
    cleaned_data = []
    
    for entry in chatbot_data:
        if entry.get("type") == "human":
            cleaned_entry = {
                "type": "human",
                "content": entry.get("data", {}).get("content", "")
            }
            cleaned_data.append(cleaned_entry)
        elif entry.get("type") == "ai":
            cleaned_entry = {
                "type": "ai", 
                "content": entry.get("data", {}).get("content", "")
            }
            cleaned_data.append(cleaned_entry)
    
    return cleaned_data


def ask_brd_gen(brd_content: str, chat_history: str, additional_content: str, prompt_file_path = config.l5_prompt) -> str:
    """Send BRD content, chat history, and additional content to Azure OpenAI and return the updated BRD."""

    with open(prompt_file_path, 'r', encoding='utf-8') as f:
        SYSTEM_PROMPT = f.read()

    # Format user prompt with the actual content
    user_prompt = f"""Please generate the updated BRD based on the following information:

Current BRD Content:
{brd_content}

Chat History:
{chat_history}

Additional Content:
{additional_content}"""

    messages = [
        {
            "role": "system",
            "content": [
                {"type": "text", "text": SYSTEM_PROMPT}
            ]
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": user_prompt}
            ]
        }
    ]
    
    response = client.chat.completions.create(
        model=OPENAI_DEPLOYMENT,
        messages=messages,
        max_tokens=4000,
        temperature=0.5,
        top_p=0.95,
        frequency_penalty=0,
        presence_penalty=0,
        stop=None,
        stream=False
    )
    return response.choices[0].message.content.strip().replace("\n","")

def brd_gen(unique_id, brd, chatbot, content):
    """Generate an updated BRD based on existing BRD, chatbot conversation, and additional files."""
    brd_file = "app_files/middleware/" + str(unique_id) + '/brd.html'
    # Convert cleaned chatbot data to string for the prompt
    chat_history_str = json.dumps(chatbot, indent=2, ensure_ascii=False)

    # Generate updated BRD
    try:
        updated_brd_content = ask_brd_gen(brd, chat_history_str, content)
        
        return updated_brd_content
        
    except Exception as e:
        print(f"Error generating updated BRD: {e}")
        return None