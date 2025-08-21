import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import datetime

class DriveUploader:
    def __init__(self, credentials_file="humandetectionrasp-ada94ad91646.json", folder_id="1moMSzkBTBcsbqeO-RplxiosGnkRf0Kv3"):
        """
        Initialize Google Drive uploader
        
        Args:
            credentials_file (str): Path to service account JSON file
            folder_id (str): Google Drive folder ID to upload images to
        """
        self.folder_id = folder_id
        
        # Set up credentials for Google Drive API
        try:
            self.creds = Credentials.from_service_account_file(
                credentials_file,
                scopes=['https://www.googleapis.com/auth/drive']
            )
            self.service = build('drive', 'v3', credentials=self.creds)
            print("Google Drive API initialized successfully")
        except Exception as e:
            print(f"Error initializing Google Drive API: {e}")
            self.service = None
    
    def upload_image(self, image_path, class_name="human", class_id="21040202"):
        """
        Upload image to Google Drive with proper naming convention
        
        Args:
            image_path (str): Path to the image file
            class_name (str): Class of detected object (e.g., "human")
            class_id (str): Class ID (e.g., student class ID "Lop21040202")
            
        Returns:
            dict: File metadata if successful, None if failed
        """
        if not self.service:
            print("Google Drive service not initialized")
            return None
            
        try:
            # Generate filename: human_Lop21040202_Date_Time
            now = datetime.datetime.now()
            date_str = now.strftime("%Y%m%d")
            time_str = now.strftime("%H%M%S")
            filename = f"{class_name}_{class_id}_{date_str}_{time_str}.jpg"
            
            # Create file metadata
            file_metadata = {
                'name': filename,
                'parents': [self.folder_id]
            }
            
            # Create media
            media = MediaFileUpload(image_path, mimetype='image/jpeg')
            
            # Upload file
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name,webViewLink'
            ).execute()
            
            print(f"File uploaded: {filename}")
            print(f"File ID: {file.get('id')}")
            print(f"View URL: {file.get('webViewLink')}")
            
            return file
            
        except Exception as e:
            print(f"Error uploading file to Google Drive: {e}")
            return None