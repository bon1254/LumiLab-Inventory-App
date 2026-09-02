import streamlit as st
import pandas as pd
import gspread
from backend import init_services, get_system_settings

# 拔掉 page_icon，並把標題的圖示拿掉
st.set_page_config(page_title="庫存總表", layout="wide")

st.title("實驗室庫存總表")
st.caption("請點擊左側【>】展開選單，切換至『AddInventory (新增品項)』或『SystemSetting (系統設定)』")

try:
    sh, _ = init_services()
    _, _, _, _, _, _, _, display_worksheets = get_system_settings(sh)
except Exception as e:
    st.error("無法連線至雲端系統，請檢查設定。")
    st.stop()

st.subheader("所有分頁資料彙整")
all_dfs = []
for ws in display_worksheets:
    data = ws.get_all_records()
    if data:
        temp_df = pd.DataFrame(data)
        temp_df.insert(0, "所屬分頁", ws.title)
        all_dfs.append(temp_df)

if all_dfs:
    full_df = pd.concat(all_dfs, ignore_index=True)
    col_config = {"照片連結": st.column_config.ImageColumn("照片預覽")} if "照片連結" in full_df.columns else {}
    st.dataframe(full_df, use_container_width=True, column_config=col_config)
else:
    st.info("目前尚無任何資料。請展開左側選單至新增頁面建立資料。")


# ==========================================
# 管理員工具 (任意分頁刪除)
# ==========================================
st.divider() 
st.subheader("管理員工具：刪除分頁")

# 抓取目前所有的分頁名稱
sheet_names = [ws.title for ws in display_worksheets]

if sheet_names:
    # 建立下拉選單讓使用者選擇
    sheet_to_delete = st.selectbox("請選擇要刪除的分頁：", sheet_names)
    
    # 動態顯示按鈕文字，避免誤刪
    if st.button(f"確認刪除【{sheet_to_delete}】分頁", type="primary"):
        try:
            # 鎖定被選中的工作表並刪除
            ws_target = sh.worksheet(sheet_to_delete)
            sh.del_worksheet(ws_target)
            
            st.success(f"【{sheet_to_delete}】分頁已經被徹底刪除！")
            st.cache_resource.clear() 
            st.rerun() # 重新整理網頁
            
        except gspread.exceptions.WorksheetNotFound:
            st.warning(f"找不到「{sheet_to_delete}」分頁，可能已經被刪除了！")
        except Exception as e:
            st.error(f"發生錯誤：{e}")
else:
    st.info("目前沒有任何可以刪除的分頁。")