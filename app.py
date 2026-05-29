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
    st.error("❌ 스트림릿 대시보드의 Secrets 설정을 다시 확인해 주세요.")
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
    loc_n = st.text_input("3. 위치 (예: 서울역)", placeholder="정확한 명칭 입력")
    desc = st.text_area("4. 특징")
    submit = st.form_submit_button(label="🚨 즉시 등록")

if submit and name and loc_n:
    with st.spinner("구글 시트에 영구 저장 중..."):
        try:
            time.sleep(1)
            l = geolocator.geocode(loc_n)
            if l:
                row = {"등록시간": datetime.now().strftime("%Y-%m-%d %H:%M"), "이름": name, "나이": age, "위치": loc_n, "위도": float(l.latitude), "경도": float(l.longitude), "특징": desc}
                res = requests.post(au, data=json.dumps(row), headers={"Content-Type": "application/json"})
                if res.status_code == 200:
                    st.success("🎯 성공적으로 저장되었습니다!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("❌ 구글 앱스 스크립트(웹앱 주소) 연결에 실패했습니다.")
            else:
                st.error("❌ 입력한 위치를 지도에서 찾을 수 없습니다
