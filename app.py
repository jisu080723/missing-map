import streamlit as st
import pandas as pd
from datetime import datetime
from geopy.geocoders import Nominatim
import requests
import json
import time

# 1. 페이지 기본 설정
st.set_page_config(page_title="실종자 관제 시스템", layout="wide")
st.title("🚓 실종자 보호자 직접 등록 및 실시간 관제 플랫폼")
st.caption("보호자가 입력한 정보는 구글 시트에 안전하게 영구 저장됩니다.")

geolocator = Nominatim(user_agent="missing_jisu_final_2026", timeout=10)

# 2. 스트림릿 순정 구글 시트 커넥션 엔진 가동
try:
    # 이 한 줄이 기존의 복잡한 주소 변환 및 차단 문제를 100% 해결합니다.
    conn = st.connection("gsheets", type="experimental_index")
    api_url = st.secrets["connections"]["gsheets"]["api_url"]
except Exception:
    st.error("❌ 스트림릿 대시보드의 Secrets 설정을 다시 확인해 주세요.")
    st.stop()

# 3. 안전한 데이터 로드 함수
@st.cache_data(ttl=1)
def load_google_sheet_data():
    try:
        # 스트림릿 내장 기능으로 구글 시트 데이터를 안전하게 읽어옵니다.
        df = conn.read(ttl="1m")
        if df is not None and not df.empty:
            df.columns = [str(col).strip() for col in df.columns]
            lat_column = [c for c in df.columns if "위도" in c or "lat" in c.lower()]
            lng_column = [c for c in df.columns if "경도" in c or "lng" in c.lower()]
            
            if lat_column and lng_column:
                # 순정 지도용 필수 칼럼명 지정
                df["latitude"] = pd.to_numeric(df[lat_column[0]], errors='coerce')
                df["longitude"] = pd.to_numeric(df[lng_column[0]], errors='coerce')
                return df.dropna(subset=["latitude", "longitude"])
        return pd.DataFrame(columns=["latitude", "longitude"])
    except Exception:
        return pd.DataFrame(columns=["latitude", "longitude"])

missing_database = load_google_sheet_data()

# 4. 사이드바 입력 양식
st.sidebar.header("📝 실종자 신규 등록")
with st.sidebar.form(key="registration_form", clear_on_submit=True):
    name = st.text_input("1. 실종자 성함")
    age = st.text_input("2. 나이")
    location_name = st.text_input("3. 마지막 발견 위치", placeholder="예: 서울역")
    description = st.text_area("4. 주요 특징 및 인상착의")
    submit_button = st.form_submit_button(label="🚨 시스템에 즉시 등록")

# 5. 데이터 등록 및 구글 웹앱 전송 로직
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
                        st.error("❌ 구글 웹앱 전송 실패 (API URL 주소를 확인해 주세요)")
                else:
                    st.error("❌ 입력하신 위치를 지도에서 찾을 수 없습니다.")
            except Exception:
                st.error("❌ 서버 지연이 발생했습니다. 잠시 후 다시 눌러주세요.")
    else:
        st.error("❌ 성함과 위치는 필수 입력
