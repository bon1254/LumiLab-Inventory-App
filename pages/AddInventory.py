import streamlit as st
import pandas as pd
import time
from backend import init_services, get_system_settings, upload_image_to_drive

st.set_page_config(page_title="新增品項", page_icon="📝", layout="wide")
st.title("📝 庫存登打與管理")

sh, _ = init_services()
setting_ws, set_df, ITEM_OPTIONS, BRAND_OPTIONS, AREA_OPTIONS, LOC_OPTIONS, STATUS_OPTIONS, display_worksheets = get_system_settings(sh)

if not display_worksheets:
    st.warning("⚠️ 目前沒有任何可用分頁，請先至系統設定建立新分頁！")
    st.stop()

tabs = st.tabs([ws.title for ws in display_worksheets])

for i, ws in enumerate(display_worksheets):
    with tabs[i]:
        header = ws.row_values(1)
        if not header:
            header = ["品項名稱", "品牌", "存放區域", "存放所在位置", "數量", "型號", "設備狀態", "備註說明", "照片連結"]
            ws.update([header])

        st.subheader("📝 新增品項 (填寫表單)")
        with st.form(key=f"form_{ws.id}", clear_on_submit=True):
            input_data = {}
            manual_data = {}
            
            for col in header:
                if col == "照片連結": continue
                elif col == "品項名稱":
                    input_data[col] = st.selectbox(f"📦 {col}", options=ITEM_OPTIONS + ["✏️ 手動輸入新選項..."])
                    manual_data[col] = st.text_input(f"✍️ 新{col}:", key=f"mi_{ws.id}")
                elif col == "品牌" or col == "品牌名稱":
                    input_data[col] = st.selectbox(f"🏷️ {col}", options=BRAND_OPTIONS + ["✏️ 手動輸入新選項..."])
                    manual_data[col] = st.text_input(f"✍️ 新{col}:", key=f"mb_{ws.id}")
                elif col == "存放區域":
                    input_data[col] = st.selectbox(f"🗃️ {col}", options=AREA_OPTIONS + ["✏️ 手動輸入新選項..."])
                    manual_data[col] = st.text_input(f"✍️ 新{col}:", key=f"ma_{ws.id}")
                elif col == "存放所在位置":
                    input_data[col] = st.selectbox(f"📍 {col}", options=LOC_OPTIONS + ["✏️ 手動輸入新選項..."])
                    manual_data[col] = st.text_input(f"✍️ 新{col}:", key=f"ml_{ws.id}")
                elif "狀態" in col:
                    input_data[col] = st.selectbox(f"🚦 {col}", options=STATUS_OPTIONS + ["✏️ 手動輸入新選項..."])
                    manual_data[col] = st.text_input(f"✍️ 新{col}:", key=f"ms_{ws.id}")
                elif col == "數量":
                    input_data[col] = st.number_input(f"🔢 {col}", min_value=0, value=1, step=1)
                elif "備註" in col:
                    q_opt = st.radio(f"⚡ {col}", ["無", "全新正常", "需維修", "零件短缺", "✏️ 手動打字..."], horizontal=True)
                    input_data[col] = st.text_input(f"✍️ 輸入{col}") if q_opt == "✏️ 手動打字..." else q_opt
                else:
                    input_data[col] = st.text_input(f"✍️ {col}")

            st.write("---")
            photo = st.camera_input("📷 拍下照片 (選填)")
            submit = st.form_submit_button("🚀 一鍵儲存並上傳", use_container_width=True)

            if submit:
                with st.spinner("雲端處理中..."):
                    def get_final(col_name):
                        return manual_data.get(col_name, "").strip() if input_data.get(col_name) == "✏️ 手動輸入新選項..." else input_data.get(col_name, "")
                    
                    final_item = get_final("品項名稱") or "未命名品項"
                    final_brand = get_final("品牌") or get_final("品牌名稱")
                    final_area = get_final("存放區域")
                    final_loc = get_final("存放所在位置")
                    
                    status_key = "設備狀態" if "設備狀態" in input_data else ("狀態" if "狀態" in input_data else "")
                    final_status = get_final(status_key) if status_key else ""

                    # 寫入新選項到設定表
                    needs_update = False
                    if final_item and final_item not in ITEM_OPTIONS: ITEM_OPTIONS.append(final_item); needs_update = True
                    if final_brand and final_brand not in BRAND_OPTIONS: BRAND_OPTIONS.append(final_brand); needs_update = True
                    if final_area and final_area not in AREA_OPTIONS: AREA_OPTIONS.append(final_area); needs_update = True
                    if final_loc and final_loc not in LOC_OPTIONS: LOC_OPTIONS.append(final_loc); needs_update = True
                    if final_status and final_status not in STATUS_OPTIONS: STATUS_OPTIONS.append(final_status); needs_update = True
                        
                    if needs_update:
                        mlen = max(len(ITEM_OPTIONS), len(BRAND_OPTIONS), len(AREA_OPTIONS), len(LOC_OPTIONS), len(STATUS_OPTIONS))
                        def pad(lst): return lst + [""]*(mlen-len(lst))
                        new_df = pd.DataFrame({
                            "下拉選單_品項名稱": pad(ITEM_OPTIONS), "下拉選單_品牌": pad(BRAND_OPTIONS),
                            "下拉選單_存放區域": pad(AREA_OPTIONS), "下拉選單_存放所在位置": pad(LOC_OPTIONS),
                            "下拉選單_設備狀態": pad(STATUS_OPTIONS)
                        })
                        setting_ws.clear()
                        setting_ws.update([new_df.columns.values.tolist()] + new_df.astype(str).values.tolist())

                    # 照片上傳
                    img_url = upload_image_to_drive(photo.getvalue(), f"{final_item}_{int(time.time())}.jpg", final_item) if photo else ""

                    # 寫入資料
                    row_to_add = []
                    for col in header:
                        if col == "照片連結": row_to_add.append(img_url)
                        elif col == "品項名稱": row_to_add.append(final_item)
                        elif col in ["品牌", "品牌名稱"]: row_to_add.append(final_brand)
                        elif col == "存放區域": row_to_add.append(final_area)
                        elif col == "存放所在位置": row_to_add.append(final_loc)
                        elif col in ["狀態", "設備狀態"]: row_to_add.append(final_status)
                        else: row_to_add.append(str(input_data.get(col, "")))

                    ws.append_row(row_to_add)
                    st.success("✅ 新增成功！")
                    time.sleep(1)
                    st.rerun()

        st.divider()
        st.subheader("📊 庫存預覽與編輯")
        data = ws.get_all_records()
        df = pd.DataFrame(data) if data else pd.DataFrame(columns=header)

        col_config = {}
        if "品項名稱" in df.columns: col_config["品項名稱"] = st.column_config.SelectboxColumn(options=ITEM_OPTIONS)
        if "品牌" in df.columns: col_config["品牌"] = st.column_config.SelectboxColumn(options=BRAND_OPTIONS)
        if "存放區域" in df.columns: col_config["存放區域"] = st.column_config.SelectboxColumn(options=AREA_OPTIONS)
        if "存放所在位置" in df.columns: col_config["存放所在位置"] = st.column_config.SelectboxColumn(options=LOC_OPTIONS)
        if "設備狀態" in df.columns: col_config["設備狀態"] = st.column_config.SelectboxColumn(options=STATUS_OPTIONS)
        if "狀態" in df.columns: col_config["狀態"] = st.column_config.SelectboxColumn(options=STATUS_OPTIONS)
        if "照片連結" in df.columns: col_config["照片連結"] = st.column_config.ImageColumn("照片預覽")

        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, column_config=col_config, key=f"ed_{ws.id}")
        if st.button("💾 儲存表格修改", key=f"sv_{ws.id}"):
            ws.clear()
            edited_df = edited_df.fillna("") 
            ws.update([edited_df.columns.values.tolist()] + edited_df.astype(str).values.tolist())
            st.success("✅ 儲存成功！")
            time.sleep(1)
            st.rerun()