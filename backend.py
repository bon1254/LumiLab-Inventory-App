import streamlit as st
from google.cloud import firestore, storage
from google.oauth2.service_account import Credentials
import time

@st.cache_resource
def init_services():
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"])
    db = firestore.Client(credentials=creds, project=creds.project_id)
    storage_client = storage.Client(credentials=creds, project=creds.project_id)
    return db, storage_client

def get_system_settings(db):
    doc_ref = db.collection("system").document("settings")
    doc = doc_ref.get()
    
    default_settings = {
        "ITEM_OPTIONS": ["雷射筆", "投影機", "延伸器"],
        "BRAND_OPTIONS": ["無品牌或未知", "Epson", "BenQ"],
        "AREA_OPTIONS": ["A區", "B區", "C區"],
        "LOC_OPTIONS": ["架子1", "架子2", "抽屜"],
        "STATUS_OPTIONS": ["在庫", "借出", "維修中"],
        "CATEGORIES": ["訊號延伸器", "投影機"]
    }
    
    if doc.exists:
        data = doc.to_dict()
        for key in default_settings:
            if key not in data:
                data[key] = default_settings[key]
        return data
    else:
        doc_ref.set(default_settings)
        return default_settings

def save_system_settings(db, new_data):
    doc_ref = db.collection("system").document("settings")
    doc_ref.set(new_data, merge=True)

def upload_image_to_storage(file_bytes, filename, category_name):
    try:
        _, storage_client = init_services()
        bucket_name = st.secrets["gcp_service_account"].get("bucket_name", "your-bucket-name")
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(f"{category_name}/{filename}")
        blob.upload_from_string(file_bytes, content_type="image/jpeg")
        return blob.public_url
    except Exception as e:
        st.error(f"照片上傳失敗：{e}")
        return ""