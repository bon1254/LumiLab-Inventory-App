import streamlit as st
import time
from backend import init_services, get_system_settings, upload_image_to_storage

st.set_page_config(page_title="庫存管理", layout="centered")
st.title("庫存管理與總覽")

db, _ = init_services()
settings = get_system_settings(db)
categories = settings.get("CATEGORIES", [])

if not categories:
    st.warning("目前沒有分頁，請先至系統設定建立！")
    st.stop()

def render_form(default_data=None):
    if default_data is None: default_data = {}
    input_data = {}
    
    item_opts = settings.get("ITEM_OPTIONS", [""])
    brand_opts = settings.get("BRAND_OPTIONS", [""])
    area_opts = settings.get("AREA_OPTIONS", [""])
    loc_opts = settings.get("LOC_OPTIONS", [""])
    status_opts = settings.get("STATUS_OPTIONS", [""])

    input_data["品項名稱"] = st.selectbox("品項名稱", options=item_opts, index=item_opts.index(default_data.get("品項名稱")) if default_data.get("品項名稱") in item_opts else 0)
    input_data["品牌"] = st.selectbox("品牌", options=brand_opts, index=brand_opts.index(default_data.get("品牌")) if default_data.get("品牌") in brand_opts else 0)
    input_data["存放區域"] = st.selectbox("存放區域", options=area_opts, index=area_opts.index(default_data.get("存放區域")) if default_data.get("存放區域") in area_opts else 0)
    input_data["存放所在位置"] = st.selectbox("存放所在位置", options=loc_opts, index=loc_opts.index(default_data.get("存放所在位置")) if default_data.get("存放所在位置") in loc_opts else 0)
    input_data["設備狀態"] = st.selectbox("設備狀態", options=status_opts, index=status_opts.index(default_data.get("設備狀態")) if default_data.get("設備狀態") in status_opts else 0)
    
    try: num_val = int(default_data.get("數量", 1))
    except: num_val = 1
    input_data["數量"] = st.number_input("數量", min_value=0, value=num_val, step=1)
    input_data["型號"] = st.text_input("型號", value=default_data.get("型號", ""))
    input_data["備註說明"] = st.text_input("備註說明", value=default_data.get("備註說明", ""))
    
    photo = st.camera_input("拍下照片 (若不換照片請忽略)")
    return input_data, photo

@st.dialog("新增庫存品項")
def add_item_dialog(cat_name):
    input_data, photo = render_form()
    if st.button("一鍵新增", use_container_width=True, type="primary"):
        with st.spinner("上傳中..."):
            img_url = upload_image_to_storage(photo.getvalue(), f"photo_{int(time.time())}.jpg", cat_name) if photo else ""
            input_data["照片連結"] = img_url
            input_data["created_at"] = time.time()
            db.collection("inventory").document(cat_name).collection("items").add(input_data)
            st.success("新增成功！")
            time.sleep(1)
            st.rerun()

@st.dialog("編輯品項詳細資料")
def edit_item_dialog(cat_name, doc_id, doc_data):
    input_data, photo = render_form(doc_data)
    if st.button("儲存修改", use_container_width=True, type="primary"):
        with st.spinner("更新中..."):
            if photo:
                img_url = upload_image_to_storage(photo.getvalue(), f"photo_{int(time.time())}.jpg", cat_name)
                input_data["照片連結"] = img_url
            else:
                input_data["照片連結"] = doc_data.get("照片連結", "")
            
            db.collection("inventory").document(cat_name).collection("items").document(doc_id).update(input_data)
            st.success("更新成功！")
            time.sleep(1)
            st.rerun()

@st.dialog("刪除確認")
def delete_item_dialog(cat_name, doc_id, item_name):
    st.warning(f"你確定要刪除「**{item_name}**」嗎？刪除後無法復原！")
    if st.button("確定刪除", use_container_width=True, type="primary"):
        db.collection("inventory").document(cat_name).collection("items").document(doc_id).delete()
        st.success("資料已刪除！")
        time.sleep(1)
        st.rerun()

# 頁面標籤渲染
tabs = st.tabs(categories)

for i, cat_name in enumerate(categories):
    with tabs[i]:
        st.write("")
        if st.button(f"新增一筆【{cat_name}】資料", use_container_width=True, type="primary", key=f"add_btn_{cat_name}"):
            add_item_dialog(cat_name)
        st.write("")

        docs = db.collection("inventory").document(cat_name).collection("items").stream()
        items = [(doc.id, doc.to_dict()) for doc in docs]
        
        if items:
            for doc_id, item in items:
                name = item.get("品項名稱", "未命名")
                brand = item.get("品牌", "")
                status = item.get("設備狀態", "")
                
                with st.expander(f"{name} | {brand} ({status})"):
                    st.markdown(f"**位置：** {item.get('存放區域', '')} - {item.get('存放所在位置', '')}")
                    st.markdown(f"**數量：** {item.get('數量', '')} ｜ **型號：** {item.get('型號', '')}")
                    st.markdown(f"**備註：** {item.get('備註說明', '')}")
                    
                    img = item.get("照片連結", "")
                    if img and "http" in img:
                        st.image(img, use_container_width=True)
                    
                    st.divider()
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("編輯內容", key=f"edit_{doc_id}", use_container_width=True):
                            edit_item_dialog(cat_name, doc_id, item)
                    with col2:
                        if st.button("刪除這筆", key=f"del_{doc_id}", use_container_width=True):
                            delete_item_dialog(cat_name, doc_id, name)
        else:
            st.info("目前還沒有任何資料，點擊上方按鈕新增吧！")