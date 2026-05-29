import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
from datetime import datetime
from geopy.geocoders import Nominatim
import requests
import json

st.set_page_config(page_title="실종자 관제", layout="wide")
st.title("开设 실종자 보호자 직접 등록 및 실시간 관제 플랫폼")

geolocator = Nominatim(user_agent="missing_jisu_2026")

try:
    sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    api_url = st.secrets["connections"]["gsheets"]["api_url"]
except:
    st.error("❌ 스트림릿 Secrets 설정을 확인해 주세요.")
    st.stop()

base_url = sheet_url.split("/edit")[0] if "/edit" in sheet_url else sheet_url
csv_url = f"{base_url}/gviz/tq?tqx=out:csv"

@st.cache_data(ttl=2)
def load_data():
    cols = ["등록시간", "이름", "나이", "위치", "위도", "경도", "특징"]
    try:
        df = pd.read_csv(csv_url)
        if not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
            return df
        return pd.DataFrame(columns=cols)
    except:
        return pd.DataFrame(columns=cols)

missing_db = load_data()

st.sidebar.header("📝 실종자 신규 등록")
with st.sidebar.form(key="reg_form", clear_on_submit=True):
    name = st.text_input("1. 실종자 성함")
    age = st.text_input("2. 나이")
    loc_name = st.text_input("3. 마지막 발견 위치", placeholder="예: 서울역")
    desc = st.text_area("4. 주요 특징 및 인상착의")
    submit = st.form_submit_button(label="🚨 시스템에 즉시 등록")

if submit:
    if name and loc_name:
        with st.spinner("🌍 구글 금고에 영구 저장하는 중..."):
            try:
                loc = geolocator.geocode(loc_name)
                if loc:
                    new_row = {
                        "등록시간": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "이름": name, "나이": age, "위치": loc_name,
                        "위도": loc.latitude, "경도": loc.longitude, "특징": desc
                    }
                    # 구글 시트에 직접 쓰기 API 요청
                    headers = {"Content-Type": "application/json"}
                    res = requests.post(api_url, data=json.dumps(new_row), headers=headers)
                    
                    if res.status_code == 200:
                        st.success(f"🎯 {name} 님 구글 시트에 평생 저장 완료!")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("❌ 구글 시트 저장 실패 (API 오류)")
                else:
                    st.error("❌ 위치를 찾을 수 없습니다.")
            except:
                st.error("❌ 시스템 처리 중 오류 발생")
    else:
        st.error("❌ 필수 항목을 채워주세요.")

c1, c2 = st.columns([1, 1])

with c1:
    st.subheader("📋 현재 등록된 실종자 누적 리스트")
    if missing_db.empty:
        st.info("현재 저장된 데이터가 없습니다.")
    else:
        st.dataframe(missing_db[["등록시간", "이름", "나이", "위치", "특징"]], use_container_width=True)

with c2:
    st.subheader("📍 실시간 수색 관제 지도 (반경 500m 원)")
    if missing_db.empty:
        m = folium.Map(location=[36.5, 127.5], zoom_start=7)
    else:
        lat = float(missing_db.iloc[-1]["위도"])
        lng = float(missing_db.iloc[-1]["경도"])
        m = folium.Map(location=[lat, lng], zoom_start=14)
        
        for idx, row in missing_db.iterrows():
            try:
                folium.Marker(
                    [float(row["위도"]), float(row["경도"])],
                    popup=f"<b>{row['이름']}</b>",
                    icon=folium.Icon(color="red", icon="info-sign")
                ).add_to(m)
                
                folium.Circle(
                    location=[float(row["위도"]), float(row["경도"])],
                    radius=500, color="red", fill=True, fill_opacity=0.15
                ).add_to(m)
            except:
                continue
            
    st_folium(m, width="100%", height=500)
