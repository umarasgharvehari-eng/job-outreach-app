from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from app.gmail_client import SCOPES
from app.config import TOKEN_PATH

def get_sheets_service():
    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    return build("sheets", "v4", credentials=creds)
