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
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
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

    # 幫你把截圖裡的品項全部塞進來了！
    default_items = [
        "雷射筆", "光學鏡片", "透鏡", "濾光片", "感測器", "電源線", "馬達", "螺絲", "其他",
        "擴大機", "HiFi Steaeo Karaoke擴大機", "喇叭", "數位回音立體聲擴大機", 
        "Professional Karaoke 擴大機", "Stereo Karaoke擴大機", "單片式畫框喇叭",
        "訊號延伸器", "變壓器", "85吋電視", "55吋電視", 
        "43型4K低藍光HDR智慧聯網顯示器", "40型低藍光LED顯示器", "32吋 HD 液晶顯示器"
    ]
    default_brands = ["無品牌或未知", "Acer 宏碁", "ASUS 華碩", "Digital Projection 數字投影科技", "Dotation 達道", "Genuine 捷元", "i-COOLTW", "JY 聚奕工業", "LITEON 光寶科技", "Logitech 羅技", "MSI 微星", "TPLink 普聯技術", "Zyxel 兆勤科技", "DIVA 惠威", "JCT", "JWE", "LINDY 林帝", "DAYEN 大影", "MACHI 金典範", "B&W 寶華韋健", "TiKAudio 翊景", "EPSON 愛普森", "ATEN 宏正自動科技", "Litemax 晶達光電", "SAMPO 聲寶", "CHIMEI 奇美", "Haier 海爾", "UniSync 優尼森克", "WAVEST 威士波", "POLYWELL 寶利威爾", "Kolin 歌林", "Mayka 明家瑋崙", "WEITIEN 威電", "JODEWAY 久威电子", "IKEA 宜家家居", "BARCORNA", "LEKO 格雷"]
    default_areas = ["無存放區域", "1號航空箱", "2號航空箱", "3號航空箱", "4號航空箱", "5號航空箱", "吊架航空箱", "機房"]
    default_locs = ["Elaine保管中", "光敘所倉庫", "翡冷翠倉庫", "高雄駁二P3_世界界古文明展場", "台北科教館_比薩大學動物展"]
    default_statuses = ["✅ 在庫", "故障中等維修", "維修中", "無法使用", "使用中", "無使用", "非案子外借中", "已賣出", "翡冷翠保管"]

    if SETTING_SHEET_NAME not in [ws.title for ws in worksheets]:
        mlen = max(len(default_items), len(default_brands), len(default_areas), len(default_locs), len(default_statuses))
        def pad(lst): return lst + [""] * (mlen - len(lst))
        
        setting_ws = sh.add_worksheet(title=SETTING_SHEET_NAME, rows=mlen + 20, cols=5)
        new_set_df = pd.DataFrame({
            "下拉選單_品項名稱": pad(default_items),
            "下拉選單_品牌": pad(default_brands),
            "下拉選單_存放區域": pad(default_areas),
            "下拉選單_存放所在位置": pad(default_locs),
            "下拉選單_設備狀態": pad(default_statuses)
        })
        setting_ws.update([new_set_df.columns.values.tolist()] + new_set_df.astype(str).values.tolist())
    else:
        setting_ws = sh.worksheet(SETTING_SHEET_NAME)
        
    set_data = setting_ws.get_all_records()
    set_df = pd.DataFrame(set_data) if set_data else pd.DataFrame()

    def get_opt(col_name):
        return [str(x) for x in set_df[col_name].dropna().tolist() if str(x).strip() != ""] if col_name in set_df.columns else []

    ITEM_OPTIONS = get_opt("下拉選單_品項名稱")
    BRAND_OPTIONS = get_opt("下拉選單_品牌")
    AREA_OPTIONS = get_opt("下拉選單_存放區域")
    LOC_OPTIONS = get_opt("下拉選單_存放所在位置")
    STATUS_OPTIONS = get_opt("下拉選單_設備狀態")
    
    display_worksheets = [ws for ws in worksheets if ws.title != SETTING_SHEET_NAME]
    
    return setting_ws, set_df, ITEM_OPTIONS, BRAND_OPTIONS, AREA_OPTIONS, LOC_OPTIONS, STATUS_OPTIONS, display_worksheets