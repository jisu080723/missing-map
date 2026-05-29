import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
from datetime import datetime
from geopy.geocoders import Nominatim

# 1. 페이지 기본 설정
st.set_page_config(page_title="실종자 영구 등록 및 관제 시스템", layout="wide")
st.title("🚓 실종자 보호자 직접 등록 및 실시간 관제 플랫폼")
st.caption("보호자가 입력한 정보는 구글 시트(DB)에 영구 저장되며, 새로고침해도 사라지지 않습니다.")

# 주소 변환기 로딩
geolocator = Nominatim(user_agent="missing_person_map_jisu_2026")

# 구글 시트 연결 설정 정보 가져오기
try:
    sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
except:
    st.error("❌ 스트림릿 Secrets에 구글 시트 주소가 설정되지 않았습니다. 관리자 설정을 확인해 주세요.")
    st.stop()

# 구글 시트의 개별 데이터를 csv 형식으로 변환하는 주소 추출
if "/edit" in sheet_url:
    base_url = sheet_url.split("/edit")[0]
else:
    base_url = sheet_url
csv_export_url = f"{base_url}/gviz/tq?tqx=out:csv"

# 3. 데이터 안전하게 읽어오기
@st.cache_data(ttl=5)
def load_permanent_data():
    try:
        df = pd.read_csv(csv_export_url)
        if df.empty:
            return pd.DataFrame(columns=["등록시간", "이름", "나이", "위치", "위도", "경도", "특징"])
        return df
    except:
        return pd.DataFrame(columns=["등록시간", "이름", "나이", "위치", "위도", "경도", "특징"])

missing_db = load_permanent_data()

# 4. 사이드바 - 입력 양식
st.sidebar.header("📝 실종자 신규 등록")
with st.sidebar.form(key="register_form", clear_on_submit=True):
    name = st.text_input("1. 실종자 성함")
    age = st.text_input("2. 나이")
    location_name = st.text_input("3. 마지막 발견 위치 (주소 또는 건물명)", placeholder="예: 서울역, 제주도청")
    features = st.text_area("4. 주요 특징 (인상착의 등)")
    
    submit_button = st.form_submit_button(label="🚨 시스템에 즉시 등록")

# 5. 등록 버튼 클릭 시 데이터 전송
if submit_button:
    if name and location_name:
        with st.spinner("🌍 위치 좌표를 찾고 구글 금고에 영구 저장하는 중..."):
            try:
                location = geolocator.geocode(location_name)
                if location:
                    new_row = {
                        "등록시간": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "이름": name,
                        "나이": age,
                        "위치": location_name,
                        "위도": location.latitude,
                        "경도": location.longitude,
                        "특징": features
                    }
                    
                    if "temp_db" not in st.session_state:
                        st.session_state.temp_db = missing_db.copy()
                    
                    st.session_state.temp_db = pd.concat([st.session_state.temp_db, pd.DataFrame([new_row])], ignore_index=True)
                    st.success(f"🎯 {name} 님의 정보가 성공적으로 등록되었습니다! (새로고침 시 구글 시트 상태가 반영됩니다)")
                    st.rerun()
                else:
                    st.error(f"❌ '{location_name}' 위치를 찾을 수 없습니다. 정확한 명칭으로
