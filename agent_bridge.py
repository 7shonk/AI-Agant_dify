import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload

app = FastAPI()

# ─── 1. Google Drive API 憑證與金鑰設定 ───
SCOPES = ['https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive']
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), "google_credentials.json")

# ─── 2. 填入你的 Google 雲端硬碟資料夾 ID ───
# 請打開網頁版雲端硬碟進入該資料夾，網址最後面那一長串亂碼（例如 1H7x...）就是了！
FOLDER_ID = "這裡請填入你雲端硬碟資料夾網址最後的那串亂碼"

def get_drive_service():
    if not os.path.exists(CREDENTIALS_FILE):
        raise RuntimeError("找不到 google_credentials.json 憑證檔案！")
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

class FilePayload(BaseModel):
    filename: str
    content: str

# ─── 工具 1：透過 API 寫入你真正的雲端硬碟 ───
@app.post("/file/save")
def save_to_drive(payload: FilePayload):
    try:
        service = get_drive_service()
        
        # 1. 先搜尋該資料夾內是否已經有同名的檔案
        query = f"'{FOLDER_ID}' in parents and name='{payload.filename}' and trashed=False"
        results = service.files().list(q=query, fields="files(id)").execute()
        files = results.get('files', [])
        
        # 準備要覆蓋或寫入的檔案內容
        media = MediaInMemoryUpload(payload.content.encode('utf-8'), mimetype='text/html', resumable=True)
        
        if files:
            # 檔案存在，執行「更新 (Update)」覆蓋內容
            file_id = files[0]['id']
            file = service.files().update(fileId=file_id, media_body=media, fields='id').execute()
            message = f"檔案已成功更新（覆蓋）至 Google 雲端硬碟！"
        else:
            # 檔案不存在，執行「新建 (Create)」
            file_metadata = {
                'name': payload.filename,
                'parents': [FOLDER_ID]
            }
            file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            message = f"新檔案已成功建立至 Google 雲端硬碟！"
            
        return {"status": "success", "message": message, "file_id": file.get('id')}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ─── 工具 2：透過 API 讀取你真正的雲端硬碟 ───
@app.get("/file/read")
def read_from_drive(filename: str):
    try:
        service = get_drive_service()
        
        # 搜尋檔案拿到 file_id
        query = f"'{FOLDER_ID}' in parents and name='{filename}' and trashed=False"
        results = service.files().list(q=query, fields="files(id)").execute()
        files = results.get('files', [])
        
        if not files:
            raise HTTPException(status_code=404, detail="在雲端硬碟中找不到該檔案")
            
        file_id = files[0]['id']
        
        # 下載檔案內容
        content_bytes = service.files().get_media(fileId=file_id).execute()
        content_str = content_bytes.decode('utf-8')
        
        return {"filename": filename, "content": content_str}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 雲端啟動指令：uvicorn agent_bridge:app --host 0.0.0.0 --port 8000
