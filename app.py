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

st.set_page_config(page_title="📦 品項管理系統", page_icon="📦", layout="wide")

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
    st.error("⚠️ 連線失敗，請檢查 Secrets 裡的 ID 或金鑰是否正確。")
    st.stop()

# ==========================================
# 核心功能：照片浮水印 & 自動建立分類資料夾
# ==========================================
def add_watermark(image_bytes):
    # 開啟圖片並稍微壓縮以節省空間
    img = Image.open(io.BytesIO(image_bytes))
    img.thumbnail((1280, 1280)) 
    
    draw = ImageDraw.Draw(img)
    # 嘗試載入較大字體，若無則使用預設字體
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
    except:
        font = ImageFont.load_default()

    # 取得現在時間 (字串)
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 計算文字大小與位置 (右下角)
    try:
        bbox = draw.textbbox((0, 0), current_time, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
    except:
        text_w, text_h = 200, 20
        
    width, height = img.size
    x, y = width - text_w - 20, height - text_h - 20

    # 畫一個黑色半透明底色，讓白色時間文字更清楚
    draw.rectangle((x - 10, y - 10, x + text_w + 10, y + text_h + 10), fill="black")
    draw.text((x, y), current_time, font=font, fill="white")

    output = io.BytesIO()
    img.save(output, format="JPEG", quality=85)
    return output.getvalue()

def get_or_create_subfolder(parent_id, folder_name):
    """尋找分類資料夾，如果沒有就自動建立一個"""
    query = f"'{parent_id}' in parents and name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    response = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    files = response.get('files', [])
    
    if files:
        return files[0].get('id')
    else:
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_id]
        }
        folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
        return folder.get('id')

def upload_image_to_drive(file_bytes, filename, category_name):
    # 1. 先處理照片(浮水印+壓縮)
    processed_bytes = add_watermark(file_bytes)
    
    # 2. 找到或建立該品項的專屬資料夾
    main_folder_id = st.secrets["drive_folder_id"]
    subfolder_id = get_or_create_subfolder(main_folder_id, category_name)
    
    # 3. 執行上傳
    file_metadata = {'name': filename, 'parents': [subfolder_id]}
    media = MediaIoBaseUpload(io.BytesIO(processed_bytes), mimetype='image/jpeg', resumable=True)
    file = drive_service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
    
    # 4. 開放權限
    drive_service.permissions().create(fileId=file.get('id'), body={'type': 'anyone', 'role': 'reader'}).execute()
    return file.get('webViewLink')

# ==========================================
# ⚙️ 左側邊欄：系統管理
# ==========================================
worksheets = sh.worksheets()
sheet_names = [ws.title for ws in worksheets]

with st.sidebar:
    st.header("⚙️ 系統管理面板")
    
    with st.expander("➕ 分頁管理"):
        new_sheet = st.text_input("新增分頁名稱:")
        if st.button("建立"):
            if new_sheet and new_sheet not in sheet_names:
                new_ws = sh.add_worksheet(title=new_sheet, rows=100, cols=20)
                new_ws.update([["品項名稱", "數量", "型號", "狀態", "照片連結"]])
                st.rerun()
                
        st.divider()
        target_sheet = st.selectbox("選擇要改名的分頁:", sheet_names)
        rename_sheet = st.text_input("輸入新名稱:")
        if st.button("改名"):
            if rename_sheet:
                sh.worksheet(target_sheet).update_title(rename_sheet)
                st.rerun()
                
    with st.expander("✨ 擴充欄位"):
        col_sheet = st.selectbox("選擇分頁:", sheet_names, key="col_sheet")
        new_col = st.text_input("新增欄位名稱:")
        if st.button("加入"):
            if new_col:
                ws = sh.worksheet(col_sheet)
                header = ws.row_values(1)
                if new_col not in header:
                    ws.update_cell(1, len(header) + 1, new_col)
                    st.rerun()

# ==========================================
# 📦 主畫面：品項管理與拍照
# ==========================================
st.title("📦 品項管理系統 (雲端同步版)")

ITEM_OPTIONS = ["雷射筆", "光學鏡片", "透鏡", "濾光片", "感測器", "電源線", "馬達", "螺絲", "其他"]
STATUS_OPTIONS = ["✅ 在庫", "⚠️ 使用中", "🛠️ 送修", "❌ 報廢"]

tabs = st.tabs(sheet_names + ["🌐 總表"])

for i, ws in enumerate(worksheets):
    with tabs[i]:
        data = ws.get_all_records()
        header = ws.row_values(1)
        
        if not header:
            header = ["品項名稱", "數量", "型號", "狀態", "照片連結"]
            ws.update([header])
            
        df = pd.DataFrame(data) if data else pd.DataFrame(columns=header)
        
        col_config = {}
        if "品項名稱" in df.columns:
            col_config["品項名稱"] = st.column_config.SelectboxColumn("品項名稱", options=ITEM_OPTIONS)
        if "狀態" in df.columns:
            col_config["狀態"] = st.column_config.SelectboxColumn("狀態", options=STATUS_OPTIONS)
        if "照片連結" in df.columns:
            col_config["照片連結"] = st.column_config.ImageColumn("照片預覽")

        st.caption("💡 提示：按下方 '+' 新增列；若要上傳照片，請先新增品項並【儲存修改】，再使用下方的拍照區。")

        edited_df = st.data_editor(
            df, num_rows="dynamic", use_container_width=True,
            column_config=col_config, key=f"editor_{ws.id}"
        )

        if st.button("💾 儲存表格修改", key=f"save_{ws.id}"):
            ws.clear()
            edited_df = edited_df.fillna("") 
            ws.update([edited_df.columns.values.tolist()] + edited_df.astype(str).values.tolist())
            st.success("✅ 儲存成功！")
            time.sleep(1)
            st.rerun()

        st.divider()
        
        # --- 📸 拍照專區 ---
        st.subheader("📸 專屬拍照 / 上傳區")
        if "品項名稱" in df.columns and not df.empty:
            item_list = df["品項名稱"].tolist()
            selected_item_idx = st.selectbox(
                "請選擇要上傳照片的品項:", 
                range(len(item_list)), 
                format_func=lambda x: f"第 {x+1} 列 - {item_list[x] if item_list[x] else '未命名品項'}",
                key=f"item_sel_{ws.id}"
            )
            
            photo = st.camera_input("📷 開啟相機拍照", key=f"cam_{ws.id}")
            
            if photo:
                if st.button("🚀 確認上傳照片並更新表格", key=f"btn_{ws.id}"):
                    with st.spinner("影像處理中，並上傳至 Google 雲端..."):
                        
                        item_name = str(item_list[selected_item_idx]).strip() or "未命名"
                        filename = f"{item_name}_{int(time.time())}.jpg"
                        
                        # 呼叫終極上傳函數
                        img_url = upload_image_to_drive(photo.getvalue(), filename, category_name=item_name)
                        
                        if "照片連結" not in header:
                            ws.update_cell(1, len(header) + 1, "照片連結")
                            col_idx = len(header) + 1
                        else:
                            col_idx = header.index("照片連結") + 1
                            
                        ws.update_cell(selected_item_idx + 2, col_idx, img_url)
                        
                        st.success(f"✅ 上傳完畢！照片已儲存於【{item_name}】資料夾！")
                        time.sleep(2)
                        st.rerun()
        else:
            st.info("請先在上方表格新增至少一個品項並儲存，才能使用拍照功能喔！")

with tabs[-1]:
    st.subheader("🌐 所有分頁資料彙整")
    st.info("請至各分頁查看詳細資料。")