import streamlit as st
import folium
import pandas as pd
from datetime import datetime
from geopy.geocoders import Nominatim
import requests, json, time
import streamlit.components.v1 as cp

st.set_page_config(page_title="실종자 관제", layout="wide")
st.title("🚓 실종자 보호자 직접 등록 및 실시간 관제 플랫폼")

geolocator = Nominatim(user_agent="missing_jisu_final_2026", timeout=10)

try:
    su = st.secrets["connections"]["gsheets"]["spreadsheet"]
    au = st.secrets["connections"]["gsheets"]["api_url"]
except:
    st.error("❌ Secrets 설정을 확인해 주세요.")
    st.stop()

cu = f'{su.split("/edit")[0]}/gviz/tq?tqx=out:csv' if "/edit" in su else f'{su}/gviz/tq?tqx=out:csv'

@st.cache_data(ttl=1)
def load_data():
    try:
        df = pd.read_csv(cu)
        if not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
            lat_c = [c for c in df.columns if "위도" in c or "lat" in c.lower()]
            lng_c = [c for c in df.columns if "경도" in c or "lng" in c.lower()]
            if lat_c and lng_c:
                df["Y"] = pd.to_numeric(df[lat_c[0]], errors='coerce')
                df["X"] = pd.to_numeric(df[lng_c[0]], errors='coerce')
                return df.dropna(subset=["Y", "X"])
        return pd.DataFrame()
    except:
        return pd.DataFrame()

db = load_data()

with st.sidebar.form(key="reg_form", clear_on_submit=True):
    st.header("📝 신규 등록")
    name = st.text_input("1. 성함")
    age = st.text_input("2. 나이")
    loc_n = st.text_input("3. 위치", placeholder="예: 서울역")
    desc = st.text_area("4. 특징")
    submit = st.form_submit_button(label="🚨 즉시 등록")

if submit and name and loc_n:
    with st.spinner("저장 중..."):
        try:
            time.sleep(1)
            l = geolocator.geocode(loc_n)
            if l:
                row = {"등록시간": datetime.now().strftime("%Y-%m-%d %H:%M"), "이름": name, "나이": age, "위치": loc_n, "위도": float(l.latitude), "경도": float(l.longitude), "특징": desc}
                if requests.post(au, data=json.dumps(row), headers={"Content-Type": "application/json"}).status_code == 200:
                    st.success("🎯 등록 성공!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("❌ 구글 저장 실패")
            else:
                st.error("❌ 위치 주소 오류")
        except:
            st.error("❌ 주소 서버 지연. 잠시 후 다시 시도")

c1, c2 = st.columns([1, 1])

with c1:
    st.subheader("📋 실종자 누적 리스트")
    if not db.empty:
        st.dataframe(db, use_container_width=True)
    else:
        st.info("데이터 없음")

with c2:
    st.subheader("📍 실시간 수색 관제 지도 (반경 500m 원)")
    if db.empty or "Y" not in db.columns:
        m = folium.Map(location=[36.5, 127.5], zoom_start=7)
    else:
        m = folium.Map(
