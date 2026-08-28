import streamlit as st
import pandas as pd
import time
from backend import init_services, get_system_settings

st.set_page_config(page_title="系統設定", page_icon="⚙️", layout="wide")
st.title("⚙️ 系統設定與選項管理")

sh, _ = init_services()
setting_ws, set_df, _, _, _, display_worksheets = get_system_settings(sh)
display_sheet_names = [ws.title for ws in display_worksheets]

st.subheader("🛠️ 選單選項管理 (新增/修改/刪除)")
st.caption("直接在下方表格修改、刪除(勾選按Delete)或新增列。完成後請按儲存。")
edited_set_df = st.data_editor(set_df, num_rows="dynamic", use_container_width=True)

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
st.subheader("➕ 分頁與欄位擴充")
col1, col2 = st.columns(2)

with col1:
    st.markdown("#### 📄 新增分頁")
    new_sheet = st.text_input("輸入新分頁名稱:")
    if st.button("建立分頁"):
        if new_sheet and new_sheet not in display_sheet_names and new_sheet != "⚙️系統設定":
            new_ws = sh.add_worksheet(title=new_sheet, rows=100, cols=20)
            new_ws.update([["品項名稱", "品牌", "數量", "型號", "狀態", "備註說明", "照片連結"]])
            st.success(f"已建立分頁：{new_sheet}")
            time.sleep(1)
            st.rerun()

with col2:
    st.markdown("#### ✨ 新增欄位")
    col_sheet = st.selectbox("選擇要擴充的分頁:", display_sheet_names) if display_sheet_names else st.empty()
    new_col = st.text_input("輸入新欄位名稱:")
    if st.button("加入欄位"):
        if new_col and display_sheet_names:
            ws = sh.worksheet(col_sheet)
            header = ws.row_values(1)
            if new_col not in header:
                ws.update_cell(1, len(header) + 1, new_col)
                st.success(f"已加入欄位：{new_col}")
                time.sleep(1)
                st.rerun()