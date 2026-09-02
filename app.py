import streamlit as st
import pandas as pd
from backend import init_services, get_system_settings

# 👇 強制清除快取，確保讀取最新權限
st.cache_resource.clear() 

st.set_page_config(page_title="庫存管理", layout="centered")
st.title("實驗室庫存總表")
st.caption("請點擊左側【>】展開選單，切換至『AddInventory (新增品項)』或『SystemSetting (系統設定)』")

# 1. 嘗試連線到 Firestore
try:
    db, _ = init_services()
    settings = get_system_settings(db)
    categories = settings.get("CATEGORIES", [])
except Exception as e:
    # 💡 故意把真實的錯誤訊息 (e) 印出來，如果還有報錯，我們才能看清楚是誰在搞鬼
    st.error(f"連線失敗，錯誤詳細原因：{e}")
    st.stop()

st.subheader("所有分類資料彙整")

# 2. 從 Firestore 讀取所有分類的資料
if categories:
    all_items = []
    for cat in categories:
        # 讀取每個分類下的 items 集合
        docs = db.collection("inventory").document(cat).collection("items").stream()
        for doc in docs:
            item_data = doc.to_dict()
            item_data["所屬分類"] = cat
            all_items.append(item_data)
    
    # 3. 轉換成 DataFrame 並顯示
    if all_items:
        full_df = pd.DataFrame(all_items)
        
        # 把「所屬分類」排在表格的第一欄
        cols = ["所屬分類"] + [c for c in full_df.columns if c != "所屬分類" and c != "created_at"]
        full_df = full_df[cols]
        
        col_config = {"照片連結": st.column_config.ImageColumn("照片預覽")} if "照片連結" in full_df.columns else {}
        st.dataframe(full_df, use_container_width=True, column_config=col_config)
    else:
        st.info("目前尚無任何資料。請展開左側選單至新增頁面建立資料。")
else:
    st.warning("目前沒有分類，請先至系統設定建立！")