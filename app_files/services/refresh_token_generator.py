import os
import config
import urllib
import logging
import msal
import re

CLIENT_ID = os.getenv("AZURE_BOT_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_BOT_CLIENT_SECRET")
TENANT_ID = os.getenv("AZURE_BOT_TENANT_ID")

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
TOKEN_ENDPOINT = f"{AUTHORITY}/oauth2/v2.0/token"
GRAPH_API_ENDPOINT = config.graph_api_endpoint
SCOPES = config.azure_bot_scopes
REDIRECT_URI = config.azure_bot_redirect_uri

def get_tokens_interactively(user_id):
    app = msal.ConfidentialClientApplication(
        client_id=CLIENT_ID,
        client_credential=CLIENT_SECRET,
        authority=AUTHORITY
    )

    # Step 1: Create auth URL. MSAL handles adding 'offline_access' automatically
    # for this flow, so we only need to pass our API scopes.
    auth_url = app.get_authorization_request_url(
        scopes=SCOPES,  # <-- FIX: Use SCOPES directly
        redirect_uri=REDIRECT_URI,
        state=user_id
    )

    return auth_url


def create_refresh_token(auth_code):
    app = msal.ConfidentialClientApplication(
        client_id=CLIENT_ID,
        client_credential=CLIENT_SECRET,
        authority=AUTHORITY
    )    
    # Exchange code for tokens
    result = app.acquire_token_by_authorization_code(
        code=auth_code,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )

    if "access_token" in result and "refresh_token" in result:
        # Use a unique identifier from the id_token if available
        user_token = result.get("id_token_claims", {}).get("oid", "unknown_user")
        logging.info("Tokens acquired successfully.")
        return result["access_token"], result["refresh_token"], user_token
    else:
        logging.error("Failed to acquire tokens.")
        logging.error(result.get("error_description"))
        return None, None, None
    
def extract_user_id(link: str) -> str:
    """
    Extracts the SharePoint user ID from either:
    - Direct SharePoint/OneDrive links
    - Teams Recap links with embedded fileUrl or sitePath parameters
    """
    # If it's a Teams Recap link, try to extract the 'fileUrl' or 'sitePath' param
    if "teams.microsoft.com" in link:
        parsed_url = urllib.parse.urlparse(link)
        query_params = urllib.parse.parse_qs(parsed_url.query)

        for key in ['fileUrl', 'sitePath']:
            if key in query_params:
                decoded_url = urllib.parse.unquote(query_params[key][0])
                match = re.search(r'/personal/([^/]+)/', decoded_url)
                if match:
                    return match.group(1)

    # Fallback: try to match directly in the original (or already decoded) link
    decoded_url = urllib.parse.unquote(link)
    match = re.search(r'/personal/([^/]+)/', decoded_url)
    if match:
        return match.group(1)

    return None  # If no match is found


def extract_filename(link: str) -> str:
    """
    Extracts the filename from a SharePoint or OneDrive link.
    Specifically looks into the 'id' query parameter if present.
    """
    parsed_url = urllib.parse.urlparse(link)
    query_params = urllib.parse.parse_qs(parsed_url.query)

    # Look for 'id' query parameter which usually contains the file path
    if 'id' in query_params:
        # Decode the URL-encoded path
        file_path = urllib.parse.unquote(query_params['id'][0])

        # Try to extract the filename from the path
        match = re.search(r'/([^/]+\.\w+)$', file_path)
        if match:
            return match.group(1)

    # Fallback: try to extract from the full decoded URL
    decoded_url = urllib.parse.unquote(link)
    match = re.search(r'/([^/]+\.\w+)(?:\?|$)', decoded_url)
    if match:
        return match.group(1)

    return None  # No filename found