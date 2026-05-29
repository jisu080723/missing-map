import streamlit as st
import folium
import pandas as pd
from datetime import datetime
from geopy.geocoders import Nominatim
import requests
import json
import time
import streamlit.components.v1 as components

# 페이지 기본 설정
st.set_page_config(page_title="실종자 관제 시스템", layout="wide")
st.title(" Police 실종자 보호자 직접 등록 및 실시간 관제 플랫폼")
st.caption("보호자가 입력한 정보는 구글 시트에 안전하게 영구 저장됩니다.")

geolocator = Nominatim(user_agent="missing_jisu_final_2026", timeout=10)

# Secrets 값 직접 읽기
try:
    spreadsheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    api_url = st.secrets["connections"]["gsheets"]["api_url"]
except Exception:
    st.error("❌ 스트림릿 대시보드의 Secrets 설정을 다시 확인해 주세요.")
    st.stop()

# 주소 정제
base_url = spreadsheet_url.split("/edit")[0] if "/edit" in spreadsheet_url else spreadsheet_url
csv_url = f"{base_url}/gviz/tq?tqx=out:csv"

@st.cache_data(ttl=1)
def load_google_sheet_data():
    try:
        df = pd.read_csv(csv_url)
        if not df.empty:
            df.columns = [str(col).strip() for col in df.columns]
            lat_column = [c for c in df.columns if "위도" in c or "lat" in c.lower()]
            lng_column = [c for c in df.columns if "경도" in c or "lng" in c.lower()]
            
            if lat_column and lng_column:
                df["Y_COORDINATE"] = pd.to_numeric(df[lat_column[0]], errors='coerce')
                df["X_COORDINATE"] = pd.to_numeric(df[lng_column[0]], errors='coerce')
                return df.dropna(subset=["Y_COORDINATE", "X_COORDINATE"])
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

missing_database = load_google_sheet_data()

st.sidebar.header("📝 실종자 신규 등록")
with st.sidebar.form(key="registration_form", clear_on_submit=True):
    name = st.text_input("1. 실종자 성함")
    age = st.text_input("2. 나이")
    location_name = st.text_input("3. 마지막 발견 위치", placeholder="예: 서울역")
    description = st.text_area("4. 주요 특징 및 인상착의")
    submit_button = st.form_submit_button(label="🚨 시스템에 즉시 등록")

if submit_button:
    if name and location_name:
        with st.spinner("🌍 위치 좌표를 찾고 구글 시트에 저장하는 중..."):
            try:
                time.sleep(1)
                geocoded_location = geolocator.geocode(location_name)
                
                if geocoded_location:
                    reg_time = datetime.now().strftime("%Y-%m-%d %H:%M")
                    data_payload = {
                        "등록시간": reg_time, "이름": name, "나이": age, "위치": location_name,
                        "위도": float(geocoded_location.latitude), "경도": float(geocoded_location.longitude), "특징": description
                    }
                    headers = {"Content-Type": "application/json"}
                    response = requests.post(api_url, data=json.dumps(data_payload), headers=headers)
                    
                    if response.status_code == 200:
                        st.success(f"🎯 {name} 님 등록 및 구글 저장 완료!")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("❌ 구글 웹앱 전송 실패 (배포 권한 설정을 확인해 주세요)")
                else:
                    st.error("❌ 입력하신 위치를 지도에서 찾을 수 없습니다.")
            except Exception:
                st.error("❌ 서버 지연이 발생했습니다. 잠시 후 다시 눌러주세요.")
    else:
        st.error("❌ 성함과 위치는 필수 입력 항목입니다.")

column_left, column_right = st.columns([1, 1])

with column_left:
    st.subheader("📋 현재 등록된 실종자 누적 리스트")
    if not missing_database.empty:
        st.dataframe(missing_database, use_container_width=True)
    else:
        st.info("현재 저장된 실종자 데이터가 없습니다.")

with column_right:
    st.subheader("📍 실시간 수색 관제 지도 (반경 500m 원)")
    if missing_database.empty or "Y_COORDINATE" not in missing_database.columns:
        map_object = folium.Map(location=[36.5, 127.5], zoom_start=7)
    else:
        latest_latitude = float(missing_database.iloc[-1]["Y_COORDINATE"])
        latest_longitude = float(missing_database.iloc[-1]["X_COORDINATE"])
        map_object = folium.Map(location=[latest_latitude, latest_longitude], zoom_start=14)
        
        for index, row in missing_database.iterrows():
            try:
                person_name = row["이름"] if "이름" in row else "실종자"
                person_location = row["위치"] if "위치" in row else ""
                folium.Marker(
                    [float(row["Y_COORDINATE"]), float(row["X_COORDINATE"])],
                    popup=f"<b>{person_name}</b><br>{person_location}",
                    icon=folium.Icon(color="red", icon="info-sign")
                ).add_to(map_object)
                folium.Circle(
                    location=[float(row["Y_COORDINATE"]), float(row["X_COORDINATE"])],
                    radius=500, color="red", fill=True, fill_opacity=0.15
                ).add_to(map_object)
            except Exception:
                continue

    try:
        html_map_data = map_object._repr_html_()
        components.html(html_map_data, height=500, scrolling=False)
    except Exception:
        st.error("❌ 지도를 화면에 표시하지 못했습니다.")
