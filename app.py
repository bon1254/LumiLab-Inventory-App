import streamlit as st
import pandas as pd
from backend import init_services, get_system_settings

st.set_page_config(page_title="📦 庫存總表", page_icon="🏠", layout="wide")
st.title("🏠 實驗室庫存總表")
st.caption("👈 請點擊左側【>】展開選單，切換至『AddInventory (新增品項)』或『SystemSetting (系統設定)』")

try:
    sh, _ = init_services()
    _, _, _, _, _, _, _, display_worksheets = get_system_settings(sh)
except Exception as e:
    st.error("⚠️ 無法連線至雲端系統，請檢查設定。")
    st.stop()

st.subheader("🌐 所有分頁資料彙整")
all_dfs = []
for ws in display_worksheets:
    data = ws.get_all_records()
    if data:
        temp_df = pd.DataFrame(data)
        temp_df.insert(0, "📁 所屬分頁", ws.title)
        all_dfs.append(temp_df)

if all_dfs:
    full_df = pd.concat(all_dfs, ignore_index=True)
    col_config = {"照片連結": st.column_config.ImageColumn("照片預覽")} if "照片連結" in full_df.columns else {}
    st.dataframe(full_df, use_container_width=True, column_config=col_config)
else:
    st.info("目前尚無任何資料。請展開左側選單至新增頁面建立資料。")