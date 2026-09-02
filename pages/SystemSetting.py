import streamlit as st
import time
from backend import init_services, get_system_settings, save_system_settings

st.set_page_config(page_title="系統設定", layout="wide")
st.title("系統設定與選項管理")

db, _ = init_services()
settings = get_system_settings(db)

st.subheader("選單選項管理 (新增/修改/刪除)")
st.caption("輸入各項類別清單，用逗號分隔，設定完成後點選儲存。")

col_a, col_b = st.columns(2)
with col_a:
    items_str = st.text_area("品項名稱選項 (用逗號隔開)", value=", ".join(settings.get("ITEM_OPTIONS", [])))
    brands_str = st.text_area("品牌選項 (用逗號隔開)", value=", ".join(settings.get("BRAND_OPTIONS", [])))
    areas_str = st.text_area("存放區域選項 (用逗號隔開)", value=", ".join(settings.get("AREA_OPTIONS", [])))

with col_b:
    locs_str = st.text_area("存放位置選項 (用逗號隔開)", value=", ".join(settings.get("LOC_OPTIONS", [])))
    status_str = st.text_area("設備狀態選項 (用逗號隔開)", value=", ".join(settings.get("STATUS_OPTIONS", [])))

if st.button("儲存選單設定"):
    new_settings = {
        "ITEM_OPTIONS": [x.strip() for x in items_str.split(",") if x.strip()],
        "BRAND_OPTIONS": [x.strip() for x in brands_str.split(",") if x.strip()],
        "AREA_OPTIONS": [x.strip() for x in areas_str.split(",") if x.strip()],
        "LOC_OPTIONS": [x.strip() for x in locs_str.split(",") if x.strip()],
        "STATUS_OPTIONS": [x.strip() for x in status_str.split(",") if x.strip()],
    }
    save_system_settings(db, new_settings)
    st.success("選單設定已更新！")
    time.sleep(1)
    st.rerun()

st.divider()
st.subheader("分頁管理")

col1, col2 = st.columns(2)
categories = settings.get("CATEGORIES", [])

with col1:
    st.markdown("#### 新增分頁")
    new_cat = st.text_input("輸入新分頁名稱:")
    if st.button("建立分頁"):
        if new_cat and new_cat not in categories:
            categories.append(new_cat)
            save_system_settings(db, {"CATEGORIES": categories})
            st.success(f"已建立分頁：{new_cat}")
            time.sleep(1)
            st.rerun()

with col2:
    st.markdown("#### 刪除分頁")
    cat_to_delete = st.selectbox("選擇要刪除的分頁:", categories) if categories else None
    if st.button("刪除分頁", type="primary"):
        if cat_to_delete:
            categories.remove(cat_to_delete)
            save_system_settings(db, {"CATEGORIES": categories})
            st.success(f"已刪除分頁：{cat_to_delete}")
            time.sleep(1)
            st.rerun()