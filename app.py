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
    try:
        processed_bytes = add_watermark(file_bytes)
        main_folder_id = st.secrets["drive_folder_id"]
        subfolder_id = get_or_create_subfolder(main_folder_id, category_name)
        file_metadata = {'name': filename, 'parents': [subfolder_id]}
        media = MediaIoBaseUpload(io.BytesIO(processed_bytes), mimetype='image/jpeg', resumable=False)

        file = drive_service.files().create(
            body=file_metadata, 
            media_body=media, 
            fields='id, webViewLink'
        ).execute()

        drive_service.permissions().create(
            fileId=file.get('id'), 
            body={'type': 'anyone', 'role': 'reader'}
        ).execute()

        return file.get('webViewLink')
    except Exception as e:
        st.error(f"❌ 上傳失敗，詳細原因：{e}")
        return ""

# ==========================================
# ⚙️ 系統設定：讀取並升級 (加入品牌)
# ==========================================
worksheets = sh.worksheets()
SETTING_SHEET_NAME = "⚙️系統設定"

if SETTING_SHEET_NAME not in [ws.title for ws in worksheets]:
    setting_ws = sh.add_worksheet(title=SETTING_SHEET_NAME, rows=200, cols=5)
    setting_ws.update([["下拉選單_品項名稱", "下拉選單_品牌"], ["雷射筆", "自訂品牌A"]])
else:
    setting_ws = sh.worksheet(SETTING_SHEET_NAME)

# 將設定轉為 DataFrame，並自動補齊缺漏的欄位
set_data = setting_ws.get_all_records()
set_df = pd.DataFrame(set_data) if set_data else pd.DataFrame(columns=["下拉選單_品項名稱", "下拉選單_品牌"])

if "下拉選單_品牌" not in set_df.columns:
    set_df["下拉選單_品牌"] = ""

# 提取非空白的選項清單
ITEM_OPTIONS = [str(x) for x in set_df["下拉選單_品項名稱"].dropna().tolist() if str(x).strip() != ""]
BRAND_OPTIONS = [str(x) for x in set_df["下拉選單_品牌"].dropna().tolist() if str(x).strip() != ""]
STATUS_OPTIONS = ["✅ 在庫", "⚠️ 使用中", "🛠️ 送修", "❌ 報廢"]

display_worksheets = [ws for ws in worksheets if ws.title != SETTING_SHEET_NAME]
display_sheet_names = [ws.title for ws in display_worksheets]

# ==========================================
# ⚙️ 左側邊欄：系統管理
# ==========================================
with st.sidebar:
    st.header("⚙️ 系統管理")
    
    # 升級：使用表格直接管理 品項 與 品牌
    with st.expander("🛠️ 選單選項管理 (新增/修改/刪除)"):
        st.caption("💡 直接在下方表格修改、刪除(勾選按Delete)或新增列。完成後請按儲存。")
        edited_set_df = st.data_editor(
            set_df, 
            num_rows="dynamic", 
            use_container_width=True,
            key="setting_editor"
        )
        
        if st.button("💾 儲存選單設定"):
            setting_ws.clear()
            edited_set_df.replace("", pd.NA, inplace=True)
            edited_set_df.dropna(how="all", inplace=True)
            edited_set_df.fillna("", inplace=True)
            setting_ws.update([edited_set_df.columns.values.tolist()] + edited_set_df.astype(str).values.tolist())
            st.success("✅ 選單設定已更新！")
            time.sleep(1)
            st.rerun()

    st.divider()
    with st.expander("➕ 分頁與欄位管理"):
        new_sheet = st.text_input("新增分頁名稱:")
        if st.button("建立新分頁"):
            if new_sheet and new_sheet not in display_sheet_names and new_sheet != SETTING_SHEET_NAME:
                new_ws = sh.add_worksheet(title=new_sheet, rows=100, cols=20)
                new_ws.update([["品項名稱", "品牌", "數量", "型號", "狀態", "備註說明", "照片連結"]])
                st.rerun()

        st.divider()
        col_sheet = st.selectbox("選擇要擴充欄位的分頁:", display_sheet_names)
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

tabs = st.tabs(display_sheet_names + ["🌐 總表"])

for i, ws in enumerate(display_worksheets):
    with tabs[i]:
        header = ws.row_values(1)
        
        # 自動修復/新增表頭
        if not header:
            header = ["品項名稱", "品牌", "數量", "型號", "狀態", "備註說明", "照片連結"]
            ws.update([header])
        elif "品牌" not in header:
            header.append("品牌")
            ws.update_cell(1, len(header), "品牌")

        # --- 區塊 1：超大表單輸入區 ---
        st.subheader("📝 新增品項 (填寫表單)")

        with st.form(key=f"form_{ws.id}", clear_on_submit=True):
            input_data = {}
            manual_data = {} # 存放手動打字的資料

            for col in header:
                if col == "照片連結":
                    continue
                elif col == "品項名稱":
                    input_data[col] = st.selectbox(f"📦 選擇 {col}", options=ITEM_OPTIONS + ["✏️ 手動輸入新選項..."])
                    manual_data[col] = st.text_input(f"✍️ 若上方選【手動輸入】，請在此輸入新{col}:", key=f"man_item_{ws.id}")
                elif col == "品牌":
                    input_data[col] = st.selectbox(f"🏷️ 選擇 {col}", options=BRAND_OPTIONS + ["✏️ 手動輸入新選項..."])
                    manual_data[col] = st.text_input(f"✍️ 若上方選【手動輸入】，請在此輸入新{col}:", key=f"man_brand_{ws.id}")
                elif col == "狀態":
                    input_data[col] = st.selectbox(f"🚦 {col}", options=STATUS_OPTIONS)
                elif col == "數量":
                    input_data[col] = st.number_input(f"🔢 {col}", min_value=0, value=1, step=1)
                elif "備註" in col:
                    quick_opt = st.radio(
                        f"⚡ 快速填寫 {col}", 
                        ["無", "全新正常", "需維修", "零件短缺", "✏️ 手動打字..."], 
                        horizontal=True
                    )
                    if quick_opt == "✏️ 手動打字...":
                        input_data[col] = st.text_input(f"✍️ 手動輸入{col}")
                    else:
                        input_data[col] = quick_opt
                else:
                    input_data[col] = st.text_input(f"✍️ {col}")

            st.write("---")
            photo = st.camera_input("📷 拍下照片 (選填)")
            submit = st.form_submit_button("🚀 一鍵儲存並上傳", use_container_width=True)

            if submit:
                with st.spinner("雲端處理中，請稍候..."):
                    # 處理「手動輸入」的邏輯
                    final_item = manual_data["品項名稱"].strip() if input_data["品項名稱"] == "✏️ 手動輸入新選項..." else input_data["品項名稱"]
                    final_brand = manual_data["品牌"].strip() if input_data["品牌"] == "✏️ 手動輸入新選項..." else input_data["品牌"]
                    
                    if not final_item: final_item = "未命名品項"
                    
                    # 若為全新選項，自動加進系統設定清單
                    needs_update = False
                    if final_item not in ITEM_OPTIONS:
                        ITEM_OPTIONS.append(final_item)
                        needs_update = True
                    if final_brand and final_brand not in BRAND_OPTIONS:
                        BRAND_OPTIONS.append(final_brand)
                        needs_update = True
                        
                    if needs_update:
                        max_len = max(len(ITEM_OPTIONS), len(BRAND_OPTIONS))
                        new_set_df = pd.DataFrame({
                            "下拉選單_品項名稱": ITEM_OPTIONS + [""] * (max_len - len(ITEM_OPTIONS)),
                            "下拉選單_品牌": BRAND_OPTIONS + [""] * (max_len - len(BRAND_OPTIONS))
                        })
                        setting_ws.clear()
                        setting_ws.update([new_set_df.columns.values.tolist()] + new_set_df.astype(str).values.tolist())

                    # 處理照片上傳
                    img_url = ""
                    if photo:
                        filename = f"{final_item}_{int(time.time())}.jpg"
                        img_url = upload_image_to_drive(photo.getvalue(), filename, category_name=final_item)

                    # 整理要寫入的資料
                    row_to_add = []
                    for col in header:
                        if col == "照片連結":
                            row_to_add.append(img_url)
                        elif col == "品項名稱":
                            row_to_add.append(final_item)
                        elif col == "品牌":
                            row_to_add.append(final_brand)
                        else:
                            row_to_add.append(str(input_data.get(col, "")))

                    ws.append_row(row_to_add)
                    st.success("✅ 資料已成功新增！新選項已自動儲存。")
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
        if "品牌" in df.columns:
            col_config["品牌"] = st.column_config.SelectboxColumn("品牌", options=BRAND_OPTIONS)
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