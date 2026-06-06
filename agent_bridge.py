import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

# ─── 1. 設定雲端伺服器內部的檔案存放資料夾 ───
# 在雲端 Linux 系統上，我們直接在程式碼同級目錄建立一個 data 資料夾來放 AI 生成的網頁
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "data")
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# ─── 資料結構定義 ───
class FilePayload(BaseModel):
    filename: str
    content: str

# ─── 工具 1：寫入雲端檔案 ───
@app.post("/file/save")
def save_to_drive(payload: FilePayload):
    try:
        # 安全檢查：防止 AI 傳入 ../../ 這種惡意路徑去破壞雲端系統
        safe_filename = os.path.basename(payload.filename)
        file_path = os.path.join(UPLOAD_DIR, safe_filename)
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(payload.content)
            
        return {"status": "success", "message": f"檔案已成功儲存至雲端伺服器：{safe_filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ─── 工具 2：讀取雲端檔案 ───
@app.get("/file/read")
def read_from_drive(filename: str):
    try:
        safe_filename = os.path.basename(filename)
        file_path = os.path.join(UPLOAD_DIR, safe_filename)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="在雲端找不到該檔案")
            
        with open(file_path, "r", encoding="utf-8") as f:
            return {"filename": safe_filename, "content": f.read()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 啟動指令（Render 自動執行）：uvicorn agent_bridge:app --host 0.0.0.0 --port 8000