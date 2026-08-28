import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="📦 品項管理系統", page_icon="📦", layout="wide")

scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource
def get_gspread_client():
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes
    )
    return gspread.authorize(credentials)

try:
    gc = get_gspread_client()
    sh = gc.open_by_key(st.secrets["spreadsheet_id"])
except Exception as e:
    st.error("⚠️ 尚未連線到 Google 試算表，請檢查 Secrets 設定。")
    st.stop()

st.title("📦 品項管理系統 (雲端同步版)")

worksheets = sh.worksheets()
sheet_names = [ws.title for ws in worksheets]

tabs = st.tabs(sheet_names + ["🌐 全部一覽 (總表)"])

for i, ws in enumerate(worksheets):
    with tabs[i]:
        data = ws.get_all_records()
        df = pd.DataFrame(data)

        if df.empty:
            df = pd.DataFrame(columns=["品項名稱", "數量", "型號", "備註說明", "狀態"])

        st.caption("💡 提示：按兩下儲存格可直接修改；按下方 '+' 號可新增一列。")

        edited_df = st.data_editor(
            df,
            num_rows="dynamic",
            use_container_width=True,
            key=f"editor_{ws.id}"
        )

        if st.button("💾 儲存修改至雲端", key=f"save_{ws.id}"):
            ws.clear()
            ws.update([edited_df.columns.values.tolist()] + edited_df.astype(str).values.tolist())
            st.success("✅ 修改成功！資料已同步至 Google 試算表")
            st.rerun()

with tabs[-1]:
    st.subheader("🌐 所有分頁資料彙整")
    all_dfs = []
    for ws in worksheets:
        data = ws.get_all_records()
        if data:
            temp_df = pd.DataFrame(data)
            temp_df.insert(0, "所屬分頁", ws.title)
            all_dfs.append(temp_df)

    if all_dfs:
        full_df = pd.concat(all_dfs, ignore_index=True)
        st.dataframe(full_df, use_container_width=True)
    else:
        st.info("目前尚無任何資料。")