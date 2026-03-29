import os
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

def ask_brd_qa(user_prompt: str, prompt_file_path = config.l3_prompt) -> str:
    """Send a user prompt to Azure OpenAI and return the assistant's response."""

    with open(prompt_file_path, 'r', encoding='utf-8') as f:
        SYSTEM_PROMPT=f.read()

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
        temperature=0.7,
        top_p=0.95,
        frequency_penalty=0,
        presence_penalty=0,
        stop=None,
        stream=False
    )
    
    return response.choices[0].message.content.strip()

# Example usage
if __name__ == "__main__":
    user_input = "Sample BRD content for analysis"
    reply = ask_brd_qa(user_input)
    print("Assistant:", reply)