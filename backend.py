import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

@st.cache_resource(ttl=600)
def init_services():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(st.secrets["spreadsheet_id"])
    drive_service = build('drive', 'v3', credentials=creds)
    return sh, drive_service

def add_watermark(image_bytes):
    img = Image.open(io.BytesIO(image_bytes))
    img.thumbnail((1280, 1280)) 
    draw = ImageDraw.Draw(img)
    try: font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
    except: font = ImageFont.load_default()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        bbox = draw.textbbox((0, 0), current_time, font=font)
        text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    except:
        text_w, text_h = 200, 20
    width, height = img.size
    x, y = width - text_w - 20, height - text_h - 20
    draw.rectangle((x - 10, y - 10, x + text_w + 10, y + text_h + 10), fill="black")
    draw.text((x, y), current_time, font=font, fill="white")
    output = io.BytesIO()
    img.save(output, format="JPEG", quality=85)
    return output.getvalue()

def get_or_create_subfolder(drive_service, parent_id, folder_name):
    query = f"'{parent_id}' in parents and name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    response = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    files = response.get('files', [])
    if files: return files[0].get('id')
    folder = drive_service.files().create(body={'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [parent_id]}, fields='id').execute()
    return folder.get('id')

def upload_image_to_drive(file_bytes, filename, category_name):
    try:
        sh, drive_service = init_services()
        processed_bytes = add_watermark(file_bytes)
        main_folder_id = st.secrets["drive_folder_id"]
        subfolder_id = get_or_create_subfolder(drive_service, main_folder_id, category_name)
        media = MediaIoBaseUpload(io.BytesIO(processed_bytes), mimetype='image/jpeg', resumable=False)
        file = drive_service.files().create(body={'name': filename, 'parents': [subfolder_id]}, media_body=media, fields='id, webViewLink').execute()
        drive_service.permissions().create(fileId=file.get('id'), body={'type': 'anyone', 'role': 'reader'}).execute()
        return file.get('webViewLink')
    except Exception as e:
        st.error(f"❌ 照片上傳失敗：{e}")
        return ""

def get_system_settings(sh):
    SETTING_SHEET_NAME = "⚙️系統設定"
    worksheets = sh.worksheets()
    if SETTING_SHEET_NAME not in [ws.title for ws in worksheets]:
        setting_ws = sh.add_worksheet(title=SETTING_SHEET_NAME, rows=200, cols=5)
        setting_ws.update([["下拉選單_品項名稱", "下拉選單_品牌"], ["雷射筆", "未分類品牌"]])
    else:
        setting_ws = sh.worksheet(SETTING_SHEET_NAME)
        
    set_data = setting_ws.get_all_records()
    set_df = pd.DataFrame(set_data) if set_data else pd.DataFrame(columns=["下拉選單_品項名稱", "下拉選單_品牌"])
    if "下拉選單_品牌" not in set_df.columns: set_df["下拉選單_品牌"] = ""
        
    ITEM_OPTIONS = [str(x) for x in set_df["下拉選單_品項名稱"].dropna().tolist() if str(x).strip() != ""]
    BRAND_OPTIONS = [str(x) for x in set_df["下拉選單_品牌"].dropna().tolist() if str(x).strip() != ""]
    STATUS_OPTIONS = ["✅ 在庫", "⚠️ 使用中", "🛠️ 送修", "❌ 報廢"]
    display_worksheets = [ws for ws in worksheets if ws.title != SETTING_SHEET_NAME]
    
    return setting_ws, set_df, ITEM_OPTIONS, BRAND_OPTIONS, STATUS_OPTIONS, display_worksheets