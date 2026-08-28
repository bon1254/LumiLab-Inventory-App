import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
import time
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

st.set_page_config(page_title="📱 手機專用・品項管理", page_icon="📱", layout="wide")

# ==========================================
# 授權與連線設定
# ==========================================
scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource
def get_credentials():
    return Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes
    )

try:
    creds = get_credentials()
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(st.secrets["spreadsheet_id"])
    drive_service = build('drive', 'v3', credentials=creds)
except Exception as e:
    st.error("⚠️ 連線失敗，請檢查 Secrets 設定。")
    st.stop()

# ==========================================
# 核心功能：照片浮水印 & 自動建立分類資料夾
# ==========================================
def add_watermark(image_bytes):
    img = Image.open(io.BytesIO(image_bytes))
    img.thumbnail((1280, 1280)) 
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
    except:
        font = ImageFont.load_default()

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        bbox = draw.textbbox((0, 0), current_time, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
    except:
        text_w, text_h = 200, 20
        
    width, height = img.size
    x, y = width - text_w - 20, height - text_h - 20
    draw.rectangle((x - 10, y - 10, x + text_w + 10, y + text_h + 10), fill="black")
    draw.text((x, y), current_time, font=font, fill="white")

    output = io.BytesIO()
    img.save(output, format="JPEG", quality=85)
    return output.getvalue()

def get_or_create_subfolder(parent_id, folder_name):
    query = f"'{parent_id}' in parents and name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    response = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    files = response.get('files', [])
    if files:
        return files[0].get('id')
    else:
        folder_metadata = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [parent_id]}
        folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
        return folder.get('id')

def upload_image_to_drive(file_bytes, filename, category_name):
    processed_bytes = add_watermark(file_bytes)
    main_folder_id = st.secrets["drive_folder_id"]
    subfolder_id = get_or_create_subfolder(main_folder_id, category_name)
    file_metadata = {'name': filename, 'parents': [subfolder_id]}
    media = MediaIoBaseUpload(io.BytesIO(processed_bytes), mimetype='image/jpeg', resumable=True)
    file = drive_service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
    drive_service.permissions().create(fileId=file.get('id'), body={'type': 'anyone', 'role': 'reader'}).execute()
    return file.get('webViewLink')

# ==========================================
# ⚙️ 左側邊欄：系統管理
# ==========================================
worksheets = sh.worksheets()
sheet_names = [ws.title for ws in worksheets]

with st.sidebar:
    st.header("⚙️ 系統管理")
    with st.expander("➕ 分頁與欄位管理"):
        new_sheet = st.text_input("新增分頁名稱:")
        if st.button("建立新分頁"):
            if new_sheet and new_sheet not in sheet_names:
                new_ws = sh.add_worksheet(title=new_sheet, rows=100, cols=20)
                new_ws.update([["品項名稱", "數量", "型號", "狀態", "照片連結"]])
                st.rerun()
                
        st.divider()
        col_sheet = st.selectbox("選擇要擴充欄位的分頁:", sheet_names)
        new_col = st.text_input("新增欄位名稱:")
        if st.button("加入欄位"):
            if new_col:
                ws = sh.worksheet(col_sheet)
                header = ws.row_values(1)
                if new_col not in header:
                    ws.update_cell(1, len(header) + 1, new_col)
                    st.rerun()

# ==========================================
# 📱 主畫面：手機表單輸入版
# ==========================================
st.title("📱 品項新增與管理")

ITEM_OPTIONS = ["雷射筆", "光學鏡片", "透鏡", "濾光片", "感測器", "電源線", "馬達", "螺絲", "其他"]
STATUS_OPTIONS = ["✅ 在庫", "⚠️ 使用中", "🛠️ 送修", "❌ 報廢"]

tabs = st.tabs(sheet_names + ["🌐 總表"])

for i, ws in enumerate(worksheets):
    with tabs[i]:
        header = ws.row_values(1)
        if not header:
            header = ["品項名稱", "數量", "型號", "狀態", "照片連結"]
            ws.update([header])
            
        # --- 區塊 1：超大表單輸入區 ---
        st.subheader("📝 新增品項 (填寫表單)")
        
        with st.form(key=f"form_{ws.id}", clear_on_submit=True):
            input_data = {}
            
            # 動態產生輸入框
            for col in header:
                if col == "照片連結":
                    continue # 照片我們另外放相機按鈕
                elif col == "品項名稱":
                    input_data[col] = st.selectbox(f"📦 {col}", options=ITEM_OPTIONS)
                elif col == "狀態":
                    input_data[col] = st.selectbox(f"🚦 {col}", options=STATUS_OPTIONS)
                elif col == "數量":
                    input_data[col] = st.text_input(f"🔢 {col} (請輸入數字)")
                else:
                    input_data[col] = st.text_input(f"✍️ {col}")
                    
            st.write("---")
            photo = st.camera_input("📷 拍下照片 (選填)")
            
            # 滿版大按鈕
            submit = st.form_submit_button("🚀 一鍵儲存並上傳", use_container_width=True)
            
            if submit:
                with st.spinner("雲端處理中，請稍候..."):
                    img_url = ""
                    item_name = input_data.get("品項名稱", "未命名")
                    
                    # 處理照片上傳
                    if photo:
                        filename = f"{item_name}_{int(time.time())}.jpg"
                        img_url = upload_image_to_drive(photo.getvalue(), filename, category_name=item_name)
                    
                    # 整理要寫入的資料整列
                    row_to_add = []
                    for col in header:
                        if col == "照片連結":
                            row_to_add.append(img_url)
                        else:
                            row_to_add.append(str(input_data.get(col, "")))
                            
                    # 直接新增一列到 Google 試算表最下方
                    ws.append_row(row_to_add)
                    st.success("✅ 資料已成功新增！")
                    time.sleep(1.5)
                    st.rerun()
        
        st.divider()

        # --- 區塊 2：資料預覽與微調區 ---
        st.subheader("📊 目前庫存預覽")
        data = ws.get_all_records()
        df = pd.DataFrame(data) if data else pd.DataFrame(columns=header)
        
        col_config = {}
        if "品項名稱" in df.columns:
            col_config["品項名稱"] = st.column_config.SelectboxColumn("品項名稱", options=ITEM_OPTIONS)
        if "狀態" in df.columns:
            col_config["狀態"] = st.column_config.SelectboxColumn("狀態", options=STATUS_OPTIONS)
        if "照片連結" in df.columns:
            col_config["照片連結"] = st.column_config.ImageColumn("照片預覽")

        st.caption("💡 提示：此區僅供快速瀏覽與微調；若要刪除資料，請勾選最左側方塊後按 Delete。")
        
        edited_df = st.data_editor(
            df, num_rows="dynamic", use_container_width=True,
            column_config=col_config, key=f"editor_{ws.id}"
        )

        if st.button("💾 儲存下方表格修改", key=f"save_edit_{ws.id}"):
            ws.clear()
            edited_df = edited_df.fillna("") 
            ws.update([edited_df.columns.values.tolist()] + edited_df.astype(str).values.tolist())
            st.success("✅ 表格修改已儲存！")
            time.sleep(1)
            st.rerun()

with tabs[-1]:
    st.subheader("🌐 所有分頁資料彙整")
    st.info("總表模式，請至上方各分頁進行表單新增。")