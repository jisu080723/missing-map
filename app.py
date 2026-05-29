import streamlit as st
import folium
import pandas as pd
from datetime import datetime
from geopy.geocoders import Nominatim
import requests
import json
import time
import streamlit.components.v1 as components

# 1. 페이지 기본 설정 및 제목 (오타 교정 완료)
st.set_page_config(page_title="실종자 관제 시스템", layout="wide")
st.title("🚓 실종자 보호자 직접 등록 및 실시간 관제 플랫폼")
st.caption("보호자가 입력한 정보는 구글 시트에 안전하게 영구 저장됩니다.")

# 2. 주소 변환기 설정 (타임아웃 넉넉히 10초)
geolocator = Nominatim(user_agent="missing_jisu_final_2026", timeout=10)

# 3. 스트림릿 Secrets 연동 체크
try:
    spreadsheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    api_url = st.secrets["connections"]["gsheets"]["api_url"]
except Exception:
    st.error("❌ 스트림릿 대시보드의 Secrets 설정을 다시 확인해 주세요.")
    st.stop()

# 4. 구글 시트 CSV 다운로드 주소 변환
if "/edit" in spreadsheet_url:
    base_url = spreadsheet_url.split("/edit")[0]
else:
    base_url = spreadsheet_url
csv_url = f"{base_url}/gviz/tq?tqx=out:csv"

# 5. 구글 시트 데이터 불러오기 함수
@st.cache_data(ttl=1)
def load_google_sheet_data():
    try:
        df = pd.read_csv(csv_url)
        if not df.empty:
            # 칼럼 이름 앞뒤 공백 제거 및 정리
            df.columns = [str(col).strip() for col in df.columns]
            
            # 구글 시트에서 '위도'와 '경도' 칼럼 추적
            lat_column = [c for c in df.columns if "위도" in c or "lat" in c.lower()]
            lng_column = [c for c in df.columns if "경도" in c or "lng" in c.lower()]
            
            if lat_column and lng_column:
                df["Y_COORDINATE"] = pd.to_numeric(df[lat_column[0]], errors='coerce')
                df["X_COORDINATE"] = pd.to_numeric(df[lng_column[0]], errors='coerce')
                return df.dropna(subset=["Y_COORDINATE", "X_COORDINATE"])
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

# 데이터베이스 로드
missing_database = load_google_sheet_data()

# 6. 왼쪽 사이드바 신규 등록 양식 (원래대로 큼직하게 복원)
st.sidebar.header("📝 실종자 신규 등록")
with st.sidebar.form(key="registration_form", clear_on_submit=True):
    name = st.text_input("1. 실종자 성함")
    age = st.text_input("2. 나이")
    location_name = st.text_input("3. 마지막 발견 위치", placeholder="예: 서울역")
    description = st.text_area("4. 주요 특징 및 인상착의")
    submit_button = st.form_submit_button(label="🚨 시스템에 즉시 등록")

# 7. [등록] 버튼을 누를 때 작동하는 로직
if submit_button:
    if name and location_name:
        with st.spinner("🌍 위치를 찾고 구글 금고에 저장하는 중..."):
            try:
                time.sleep(1)  # 서버 과부하 방지 대기
                geocoded_location = geolocator.geocode(location_name)
                
                if geocoded_location:
                    # 보낼 데이터 포맷 생성
                    new_missing_person = {
                        "등록시간": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "이름": name,
                        "나이": age,
                        "위치": location_name,
                        "위도": float(geocoded_location.latitude),
                        "경도":
