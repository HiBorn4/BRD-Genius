class Config:
    def __init__(self):
        self.database_url = "sqlite:///example.db"
        self.debug_mode = True
        self.api_key

port = 8501
storage_type = 'gcs' # 'gcs' or 'local'
file_type = {'txt', 'pdf', 'docx', 'mp4','mp3'}
chunk_size = 15
chunk_thread = 8
l2_prompt = "app_files/prompts/l2_transcript_analysis_prompt.md"
l3_prompt = "app_files/prompts/l3_brd_qa.txt"
l4_prompt = "app_files/prompts/l4_chatbot_prompts.txt"
l5_prompt = "app_files/prompts/l5_brd_gen.txt"
gcs_bucket_name = 'brd001'
chatbot_model = "anthropic.claude-3-5-sonnet-20240620-v1:0"
project_id = "epod-icr-dev-399519"
secret_id = "epod-icr-dev-399519_appspot"
database_id = "mgcdepod-01"
secret_id_env = "gpt-endpoints"
project_id_env = "epod-icr-dev-399519"
brd_document_path = "app_files/templates/brd.docx"
azure_bot_scopes = ["Files.Read.All", "Sites.Read.All", "User.Read"]
graph_api_endpoint = "https://graph.microsoft.com/v1.0"
transcribe_azure_api_version = "2024-02-01"
azure_api_version = "2024-02-15-preview"
azure_bot_redirect_uri = "https://epodcr01-568063304711.asia-south1.run.app/auth/callback" 
firestore_db = "BRD_db"