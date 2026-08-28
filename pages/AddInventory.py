import streamlit as st
import time
from backend import init_services, get_system_settings, upload_image_to_drive

# 1. 設定手機版專用版面 (Centered 比較適合手機集中視覺)
st.set_page_config(page_title="庫存管理", page_icon="📱", layout="centered")
st.title("📱 庫存管理與總覽")

sh, _ = init_services()
setting_ws, set_df, ITEM_OPTIONS, BRAND_OPTIONS, AREA_OPTIONS, LOC_OPTIONS, STATUS_OPTIONS, display_worksheets = get_system_settings(sh)

if not display_worksheets:
    st.warning("⚠️ 目前沒有分頁，請先至系統設定建立！")
    st.stop()

# ==========================================
# 彈出視窗區 (Streamlit 最新黑科技：對話框)
# ==========================================

# 產生表單的共用函數 (讓新增跟編輯共用，減少程式碼)
def render_form(header, default_data=None):
    if default_data is None: default_data = {}
    input_data = {}
    
    # 為了手機順手，我們用最乾淨的下拉選單，拿掉複雜的手動輸入區塊
    for col in header:
        if col == "照片連結": continue
        
        val = default_data.get(col, "")
        
        if col == "品項名稱":
            idx = ITEM_OPTIONS.index(val) if val in ITEM_OPTIONS else 0
            input_data[col] = st.selectbox(f"📦 {col}", options=ITEM_OPTIONS, index=idx)
        elif col in ["品牌", "品牌名稱"]:
            idx = BRAND_OPTIONS.index(val) if val in BRAND_OPTIONS else 0
            input_data[col] = st.selectbox(f"🏷️ {col}", options=BRAND_OPTIONS, index=idx)
        elif col == "存放區域":
            idx = AREA_OPTIONS.index(val) if val in AREA_OPTIONS else 0
            input_data[col] = st.selectbox(f"🗃️ {col}", options=AREA_OPTIONS, index=idx)
        elif col == "存放所在位置":
            idx = LOC_OPTIONS.index(val) if val in LOC_OPTIONS else 0
            input_data[col] = st.selectbox(f"📍 {col}", options=LOC_OPTIONS, index=idx)
        elif col in ["狀態", "設備狀態"]:
            idx = STATUS_OPTIONS.index(val) if val in STATUS_OPTIONS else 0
            input_data[col] = st.selectbox(f"🚦 {col}", options=STATUS_OPTIONS, index=idx)
        elif col == "數量":
            try: num_val = int(val) if val else 1
            except: num_val = 1
            input_data[col] = st.number_input(f"🔢 {col}", min_value=0, value=num_val, step=1)
        else:
            input_data[col] = st.text_input(f"✍️ {col}", value=val)
            
    photo = st.camera_input("📷 拍下照片 (若不換照片請忽略)")
    return input_data, photo

@st.dialog("➕ 新增庫存品項")
def add_item_dialog(ws_title, header):
    ws = sh.worksheet(ws_title)
    input_data, photo = render_form(header)
    
    if st.button("🚀 一鍵新增", use_container_width=True, type="primary"):
        with st.spinner("上傳中..."):
            img_url = upload_image_to_drive(photo.getvalue(), f"photo_{int(time.time())}.jpg", "Inventory") if photo else ""
            row_to_add = [img_url if col == "照片連結" else str(input_data.get(col, "")) for col in header]
            ws.append_row(row_to_add)
            st.success("✅ 新增成功！")
            time.sleep(1)
            st.rerun()

@st.dialog("✏️ 編輯品項詳細資料")
def edit_item_dialog(ws_title, header, row_idx, row_data):
    ws = sh.worksheet(ws_title)
    input_data, photo = render_form(header, row_data)
    
    if st.button("💾 儲存修改", use_container_width=True, type="primary"):
        with st.spinner("更新中..."):
            # 如果有拍新照片就上傳，沒有就用舊的
            img_url = upload_image_to_drive(photo.getvalue(), f"photo_{int(time.time())}.jpg", "Inventory") if photo else row_data.get("照片連結", "")
            row_to_update = [img_url if col == "照片連結" else str(input_data.get(col, "")) for col in header]
            
            # 更新 Google Sheets 指定的列
            ws.update(values=[row_to_update], range_name=f"A{row_idx}")
            st.success("✅ 更新成功！")
            time.sleep(1)
            st.rerun()

@st.dialog("⚠️ 刪除確認")
def delete_item_dialog(ws_title, row_idx, item_name):
    st.warning(f"🚨 你確定要刪除「**{item_name}**」嗎？刪除後無法復原喔！")
    if st.button("🗑️ 確定刪除", use_container_width=True, type="primary"):
        sh.worksheet(ws_title).delete_rows(row_idx)
        st.success("✅ 資料已刪除！")
        time.sleep(1)
        st.rerun()


# ==========================================
# 主畫面：大總覽與分類頁籤
# ==========================================

tabs = st.tabs([ws.title for ws in display_worksheets])

for i, ws in enumerate(display_worksheets):
    with tabs[i]:
        header = ws.row_values(1)
        if not header:
            header = ["品項名稱", "品牌", "存放區域", "存放所在位置", "數量", "型號", "設備狀態", "備註說明", "照片連結"]
            ws.update([header])

        # 超大的新增按鈕
        st.write("")
        if st.button(f"➕ 新增一筆【{ws.title}】資料", use_container_width=True, type="primary", key=f"add_btn_{ws.id}"):
            add_item_dialog(ws.title, header)
        st.write("")

        # 讀取全部資料，變成手機卡片
        all_vals = ws.get_all_values()
        if len(all_vals) > 1:
            data_rows = all_vals[1:]
            for r_i, row in enumerate(data_rows):
                row_idx = r_i + 2  # Google sheet 是從 1 開始，而且有 1 行標題
                row_dict = {h: (row[idx] if idx < len(row) else "") for idx, h in enumerate(header)}
                
                name = row_dict.get("品項名稱", "未命名")
                brand = row_dict.get("品牌", row_dict.get("品牌名稱", ""))
                status = row_dict.get("設備狀態", row_dict.get("狀態", ""))
                
                # 手機版神級 UI：折疊卡片 (Expander)
                with st.expander(f"📦 {name} | {brand}  (🚦{status})"):
                    # 詳細資料區塊
                    st.markdown(f"**📍 位置：** {row_dict.get('存放區域', '')} - {row_dict.get('存放所在位置', '')}")
                    st.markdown(f"**🔢 數量：** {row_dict.get('數量', '')} ｜ **🏷️ 型號：** {row_dict.get('型號', '')}")
                    st.markdown(f"**⚡ 備註：** {row_dict.get('備註說明', '')}")
                    
                    img = row_dict.get("照片連結", "")
                    if img and "http" in img:
                        st.image(img, use_container_width=True)
                    
                    st.divider()
                    
                    # 修改與刪除的專屬按鈕
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✏️ 編輯內容", key=f"edit_{ws.id}_{row_idx}", use_container_width=True):
                            edit_item_dialog(ws.title, header, row_idx, row_dict)
                    with col2:
                        if st.button("🗑️ 刪除這筆", key=f"del_{ws.id}_{row_idx}", use_container_width=True):
                            delete_item_dialog(ws.title, row_idx, name)
        else:
            st.info("📂 目前還沒有任何資料，點擊上方按鈕新增吧！")