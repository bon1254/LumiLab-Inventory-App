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

# ==========================================
# ⚙️ 左側邊欄：系統管理面板
# ==========================================
with st.sidebar:
    st.header("⚙️ 系統管理面板")
    
    # 取得目前所有分頁
    worksheets = sh.worksheets()
    sheet_names = [ws.title for ws in worksheets]
    
    # 1. 新增 / 重命名分頁
    with st.expander("➕ 新增 / 重命名分頁"):
        new_sheet = st.text_input("新增分頁名稱:")
        if st.button("建立分頁"):
            if new_sheet and new_sheet not in sheet_names:
                new_ws = sh.add_worksheet(title=new_sheet, rows=100, cols=20)
                new_ws.update([["品項名稱", "數量", "型號", "備註說明", "狀態"]])
                st.success(f"已建立 [{new_sheet}]！")
                st.rerun()
                
        st.divider()
        target_sheet = st.selectbox("選擇要改名的分頁:", sheet_names)
        rename_sheet = st.text_input("輸入新名稱:")
        if st.button("確認改名"):
            if rename_sheet and rename_sheet not in sheet_names:
                sh.worksheet(target_sheet).update_title(rename_sheet)
                st.success("改名成功！")
                st.rerun()
                
    # 2. 新增欄位
    with st.expander("✨ 擴充表格欄位"):
        col_sheet = st.selectbox("選擇要擴充的分頁:", sheet_names, key="col_sheet")
        new_col = st.text_input("新增欄位名稱:")
        if st.button("加入欄位"):
            if new_col:
                ws = sh.worksheet(col_sheet)
                header = ws.row_values(1)
                if new_col not in header:
                    ws.update_cell(1, len(header) + 1, new_col)
                    st.success(f"已在 [{col_sheet}] 加入 [{new_col}] 欄位！")
                    st.rerun()

# ==========================================
# 📦 主畫面：品項管理與編輯
# ==========================================
st.title("📦 品項管理系統 (雲端同步版)")

# 自訂下拉選單的選項 (可自由修改括號內的文字)
ITEM_OPTIONS = ["雷射筆", "光學鏡片", "透鏡", "濾光片", "感測器", "電源線", "馬達", "螺絲", "其他"]
STATUS_OPTIONS = ["✅ 在庫", "⚠️ 使用中", "🛠️ 送修", "❌ 報廢"]

tabs = st.tabs(sheet_names + ["🌐 全部一覽 (總表)"])

# 3. 渲染各分頁表格
for i, ws in enumerate(worksheets):
    with tabs[i]:
        data = ws.get_all_records()
        header = ws.row_values(1)
        
        # 避免空白表報錯
        if not header:
            header = ["品項名稱", "數量", "型號", "備註說明", "狀態"]
            ws.update([header])
            
        df = pd.DataFrame(data) if data else pd.DataFrame(columns=header)
        
        # 設定下拉選單功能
        col_config = {}
        if "品項名稱" in df.columns:
            col_config["品項名稱"] = st.column_config.SelectboxColumn("品項名稱", options=ITEM_OPTIONS)
        if "狀態" in df.columns:
            col_config["狀態"] = st.column_config.SelectboxColumn("狀態", options=STATUS_OPTIONS)

        st.caption("💡 提示：【修改】雙擊文字直接改 / 【刪除】勾選最左側核取方塊後按 Delete / 【新增下拉選單】點擊欄位即可選擇。")

        # 顯示可編輯表格
        edited_df = st.data_editor(
            df,
            num_rows="dynamic",
            use_container_width=True,
            column_config=col_config,
            key=f"editor_{ws.id}"
        )

        if st.button("💾 儲存修改至雲端", key=f"save_{ws.id}"):
            ws.clear()
            # 自動將空值補為空字串，避免寫入出錯
            edited_df = edited_df.fillna("") 
            ws.update([edited_df.columns.values.tolist()] + edited_df.astype(str).values.tolist())
            st.success("✅ 修改成功！資料已同步至 Google 試算表")
            st.rerun()

# 4. 渲染總表
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
