from flask import Flask, jsonify, request, redirect, abort, Response,stream_with_context
import jwt
import traceback
from datetime import datetime, timedelta
from flask_cors import CORS
from google.cloud import secretmanager
import config
import json
import os
import logging
import io
import jwt
import traceback
from dotenv import load_dotenv
from pathlib import Path
import sys
import uuid

storage = config.storage_type

if storage == "gcs":
    def load_env_from_secret(secret_id=config.secret_id_env, project_id=config.project_id_env, version_id='4'):
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"   
        response = client.access_secret_version(name=name)
        payload = response.payload.data.decode("UTF-8")
        config = json.loads(payload)

        # Inject into os.environ
        for key, value in config.items():
            os.environ[key] = value

    load_env_from_secret()
elif storage == "local":
    load_dotenv()

from processing import brd_qa, generate_brd, chatbot_conversation, chatbot_initialization,intial_upload, extraction_files, download_video, download_brd, session_delete
from app_files.services.firestore_helper import create_entry, get_entry, store_user_token, get_user_token, delete_entry
from app_files.services.refresh_token_generator import get_tokens_interactively, create_refresh_token, extract_user_id, extract_filename

port_no = config.port

logging.basicConfig(level=logging.INFO,format='%(asctime)s - %(levelname)s - %(message)s',  handlers=[logging.StreamHandler(sys.stdout)])

app = Flask(__name__)
CORS(app)

# # Initialize Firebase App
# cred = credentials.Certificate("brd001-firebase-adminsdk-fbsvc-20e67bbc71.json")
# firebase_admin.initialize_app(cred)
obj_list={}
SECRET_KEY = "aurfakefriendshipnahihongi"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
ALLOWED_USERS = {"user1", "user2"} 

def create_access_token(user_id: str):
    try:    
        if isinstance(user_id, dict) and 'sub' in user_id:
            print("user id: ", user_id["sub"])
            user_id = user_id['sub']
        
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        iat = datetime.utcnow()  # Use datetime object for issued_at
        to_encode = {
            "sub": user_id,
            "iat": int(iat.timestamp()),
            "exp": expire
        }
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt, iat, expire
    except Exception as e:
        logging.error(f"Error creating access token: {e}")
        traceback.print_exc()
        abort(500, description="Token creation failed")

def add_usertoken(user_id, token, iat, expire):
    logging.info(f"Token added to DB: user_id={user_id}, iat={iat}, expire={expire}")
    # Add logic to store the user token in the database
    print(f"Token added to DB: user_id={user_id}, token={token}, iat={iat}, expire={expire}")

@app.route('/brdfrdgeneration/brdfrdgeneration', methods=['GET'])
def brd_frd_generation():
    return 'Welcome to BRD/FRD Generation API'

@app.route("/brdfrdgeneration/authsuccesslogin", methods=["GET"])
def handle_upload():
    token = request.args.get("jwt_token")
    if not token:
        abort(400, description="Token not provided")

    try:
        # Decode the JWT token and verify signature (you should validate the signature in production)
        payload = jwt.decode(token, "", options={"verify_signature": False})
        print('PAYLOAD :', payload)
        user_id = payload.get("user")
        if not user_id:
            logging.error("User ID not found in token")
            abort(400, description="User ID not found in token")

        # Check user access
        if True or user_id in ALLOWED_USERS:
            new_token_data = {"sub": user_id}
            new_token, iat, expire = create_access_token(new_token_data)
            print("after create access token")
            add_usertoken(user_id, new_token, iat, expire)
            print("token added to the database: ", new_token)
            # Redirect to the frontend middleware or access page with user info
            redirect_url = f"https://brdgen-dev.m-devsecops.com/middleware?user={new_token}"
            store_user_token(user_id, redirect_url)
            logging.info(f"Redirecting user {user_id} to {redirect_url}")
            redirect_uri = get_tokens_interactively(user_id)
            print("success redirect url: ", redirect_uri)
            return redirect(redirect_uri)
        else:
            redirect_url = f"https://mazusofiwa2.azurewebsites.net/user-not-found"
            logging.warning(f"User {user_id} not found, redirecting to {redirect_url}")
            print("user not found redirect url: ", redirect_url)
            return redirect(redirect_url)

    except jwt.ExpiredSignatureError:
        logging.error("JWT signature expired")
        abort(401, description="Token expired")
    except jwt.DecodeError:
        logging.error("JWT decoding failed")
        abort(401, description="Invalid token")
    except Exception as e:
        logging.error(f"Error in handle_upload: {e}")
        traceback.print_exc()
        abort(500, description="An error occurred while processing the request")


@app.route("/auth/callback", methods=["GET"])
def handle_auth_callback():
    try:
        # Get auth code from query params
        auth_code = request.args.get("code")
        user_id = request.args.get("state")
        access_token, refresh_token, user_token = create_refresh_token(auth_code)
        redirect_url = get_user_token(user_id)
        store_user_token(user_id, refresh_token)
        logging.info(f"success redirect url to  {redirect_url}")
        print("success redirect url: ", redirect_url)
        return redirect(redirect_url)

    except Exception as e:
        logging.exception("Unexpected error during auth callback.")
        return jsonify({"error": str(e)}), 500

@app.route('/brdfrdgeneration/upload', methods=['POST'])
def upload_file():
    try:
        # token = request.headers.get('Authorization').split(" ")[1]  # Assuming Bearer token
        # payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # user_id = payload.get('sub') 
        user_id = request.form.get('userId')
        meeting_path = request.form.get('video_path')
        if not user_id:
            return jsonify({'error': 'userId is required'}), 400

        if 'files' not in request.files and not meeting_path:
            return 'No file part', 400
        video_path = request.form.get('video_path')
        file_name=""
        if video_path:
            file_name = os.path.basename(video_path)

        # Case 2: If file(s) are uploaded
        if 'files' in request.files:
            uploaded_files = request.files.getlist('files')
            if uploaded_files:
                first_file = uploaded_files[0]
                file_name = first_file.filename
        
        if file_name == '' and not meeting_path:
            return 'No selected file', 400
        
        only_name = file_name.split('.')[0]

        unique_id=create_entry(user_id, only_name)

        if unique_id is False:
            return jsonify({'error': 'Failed to create entry in BRD'}), 500

        transcript,content = extraction_files(request,app,unique_id, user_id)


        result = intial_upload( unique_id,user_id)
        brd_qa(user_id, unique_id)
        return jsonify({'html': result, 'unique_id': unique_id}), 200
    except Exception as e:
        logging.error(f"Error during file upload: {e}")
        traceback.print_exc()
        return 'Error processing file', 500
    


@app.route('/brdfrdgeneration/chatbot', methods=['POST'])
def chatbot():
    try:
        # token = request.headers.get('Authorization').split(" ")[1]  # Assuming Bearer token
        # payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # user_id = payload.get('sub')

        user_id = request.json.get('userId')
        unique_id = request.json.get('uniqueId')

        file_name = request.json['file_name']
        ques = request.json['question']

        
        
        if ques.lower() in ["hi", "hibhavya"]:
            logging.info(f"Chatbot response generated for user {user_id}")
            return chatbot_initialization(user_id, unique_id)
        else:
            logging.info(f"Chatbot response generated for user {user_id}")
            return chatbot_conversation(user_id, unique_id, ques)
        
        
        logging.info(f"Chatbot response generated for user {user_id}")
        return jsonify({"response": chatbot_result, "history": history}), 200
    except Exception as e:
        logging.error(f"Error  in chabot api: {e}")
        traceback.print_exc()
        return 'Error deleting file', 500

@app.route('/brdfrdgeneration/final', methods=['POST'])
def final():
    try:
        # token = request.headers.get('Authorization').split(" ")[1]  # Assuming Bearer token
        # payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # user_id = payload.get('sub')

        user_id = request.json.get('userId')

        uniqueId = request.json['uniqueId']

        return generate_brd(user_id, uniqueId, content= "" )
    except Exception as e:
        logging.error(f"Error in final api file: {e}")
        error_output = io.StringIO()
        traceback.print_exc(file=error_output)
        error_output=str(error_output.getvalue())
        return f'Error in final file {e} \n {error_output}', 500


@app.route('/brdfrdgeneration/listfiles', methods=['GET'])
def list_files():
    try:
        # token = request.headers.get('Authorization').split(" ")[1]  # Assuming Bearer token
        # payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # user_id = payload.get('sub')

        user_id = request.args.get('userId')
        if not user_id:
            return jsonify({'error': 'userId is required'}), 400

        files = get_entry(user_id)
        if files is None:
            return jsonify({'error': 'No files found for this user'}), 404

        return jsonify(files), 200
    except Exception as e:
        logging.error(f"Error listing files: {e}")
        traceback.print_exc()
        return 'Error listing files', 500


@app.route('/brdfrdgeneration/uploadinbetween', methods=['POST'])
def upload_between_file():
    try:
        # token = request.headers.get('Authorization').split(" ")[1]  # Assuming Bearer token
        # payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # user_id = payload.get('sub') 
        user_id = request.form.get('userId')
        unique_id = request.form.get('uniqueId')
        meeting_path = request.form.get('video_path')
        if not user_id:
            return jsonify({'error': 'userId is required'}), 400

        if 'files' not in request.files and not meeting_path:
            return 'No file part', 400
        video_path = request.form.get('video_path')
        file_name=""
        if video_path:
            file_name = os.path.basename(video_path)

        # Case 2: If file(s) are uploaded
        if 'files' in request.files:
            uploaded_files = request.files.getlist('files')
            if uploaded_files:
                first_file = uploaded_files[0]
                file_name = first_file.filename
        
        if file_name == '' and not meeting_path:
            return 'No selected file', 400

        if unique_id is False:
            return jsonify({'error': 'Failed to create entry in BRD'}), 500

        transcript,content = extraction_files(request,app,unique_id, user_id)
        list_content = [content, transcript]
        final_content = "\n".join(filter(None, list_content))

        result = generate_brd(user_id, unique_id, final_content)
        
        return jsonify({'html': result, 'unique_id': unique_id}), 200
    except Exception as e:
        logging.error(f"Error during file upload: {e}")
        traceback.print_exc()
        return 'Error processing file', 500
     
@app.route('/brdfrdgeneration/downloadbrd', methods=['POST'])
def downloadbrd():
    try:
        user_id = request.form.get('userId')
        unique_id = request.form.get('uniqueId')
        file_name = request.form.get('filename')
        html_content = request.form.get('htmlcontent')

        # Input validation
        if not user_id:
            return jsonify({'error': 'userId is required'}), 400
        if not unique_id:
            return jsonify({'error': 'uniqueId is required'}), 400
        if not file_name:
            return jsonify({'error': 'filename is required'}), 400
        if not html_content:
            return jsonify({'error': 'htmlContent is required'}), 400

        # Generate the BRD file
        path = download_brd(user_id, unique_id, file_name, html_content)
        file_path = Path(path)

        if not file_path.exists():
            return jsonify({'error': 'Generated file not found'}), 404

        # Generator function to stream file and delete it after streaming
        def generate():
            with open(file_path, 'rb') as f:
                yield from f
            try:
                os.remove(file_path)
                app.logger.info(f"Deleted file: {file_path}")
            except Exception as e:
                app.logger.error(f"Error deleting file {file_path}: {e}")

        headers = {
            'Content-Disposition': f'attachment; filename="{file_path.name}"',
            'Content-Type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        }

        return Response(stream_with_context(generate()), headers=headers)

    except Exception as e:
        app.logger.error(f"Unhandled error in downloadbrd: {e}")
        return jsonify({'error': str(e)}), 500
    
@app.route('/brdfrdgeneration/uploadvialink', methods=['POST'])
def downloadlinks():
    try:
        user_id = request.form.get('userId')
        unique_id = uuid.uuid4()
        meet_url = request.form.get('meeting_url')

        # Input validation
        if not user_id:
            return jsonify({'error': 'userId is required'}), 400
        if not meet_url:
            return jsonify({'error': 'meeting_url is required'}), 400

        # Extract linked user ID from the URL
        link_user_id = extract_user_id(meet_url)
        token_number = link_user_id.split('_')[0]

        #Extract linked meeting number from the URL
        meet_name = extract_filename(meet_url)
        # Attempt to get access token
        token = get_user_token(token_number)

        if not token:
            return jsonify({
                'message': f"Unable to access the file. Please ask the linked user ID '{token_number}' to log in to the BRD Generation portal (https://brdgen-dev.m-devsecops.com) and try again."
            }), 403

        # Proceed with download
        gcs_path = download_video(user_id, unique_id, token, meet_url, meet_name)

        return jsonify({
            'message': f"I hereby acknowledge and confirm my intent to access, read, and process the file(s) available through the provided OneDrive link. This action is undertaken with the understanding that the content retrieved is intended solely for authorized use within the scope of the BRD/FRD generation process associated with ID .",
            'gcs_path': gcs_path,
            'file_name': meet_name
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

@app.route('/brdfrdgeneration/delete', methods=['POST'])
def deletesession():
    try:
        user_id = request.form.get('userId')
        unique_id = request.form.get('uniqueId')

        # Input validation
        if not user_id:
            return jsonify({'error': 'userId is required'}), 400
        if not unique_id:
            return jsonify({'error': 'uniqueId is required'}), 400

        # Delete from Firestore
        entry_deleted = delete_entry(user_id, unique_id)
        if not entry_deleted:
            return jsonify({'error': 'Entry not found or already deleted'}), 404

        # Delete from storage
        status_code, msg = session_delete(user_id, unique_id)
        if status_code != 200:
            return jsonify({'error': 'Session deletion failed', 'details': msg}), status_code

        return jsonify({'message': 'Session deleted successfully'}), 200

    except Exception as e:
        app.logger.error(f"Unhandled error in delete session: {e}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=False, host="0.0.0.0", port=port_no)