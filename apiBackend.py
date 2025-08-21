from flask import Flask, jsonify
from google.oauth2 import service_account
from googleapiclient.discovery import build
import datetime

app = Flask(__name__)

# Cấu hình Google Drive
SCOPES = ['https://www.googleapis.com/auth/drive']
FOLDER_ID = "____your_folder_id____"
CREDENTIALS_FILE = "____your_path____credentials.json"

def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE, scopes=SCOPES
    )
    return build('drive', 'v3', credentials=creds)

@app.route('/api/images/<class_id>')
def get_images(class_id):
    service = get_drive_service()
    now = datetime.datetime.now()
    date_str = now.strftime("%Y%m%d")
    
    # Query ảnh trong 24h
    query = f"""
        name contains '{class_id}_{date_str}' 
        and mimeType='image/jpeg' 
        and '{FOLDER_ID}' in parents
    """
    
    results = service.files().list(
        q=query,
        fields="files(id, name, createdTime)",  # Chỉ trả về fileId
        orderBy="createdTime desc"
    ).execute()
    
    return jsonify(results.get('files', []))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)