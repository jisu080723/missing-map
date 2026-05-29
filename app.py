import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
from datetime import datetime
from geopy.geocoders import Nominatim

# 1. 페이지 제목 및 레이아웃 설정
st.set_page_config(page_title="실종자 관제 시스템", layout="wide")
st.title("🚓 실종자 보호자 직접 등록 및 실시간 관제 플랫폼")

# 주소 변환기 로딩
geolocator = Nominatim(user_agent="missing_person_map_jisu_2026")

# 구글 시트 연결 정보 확인
try:
    sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
except:
    st.error("❌ 스트림릿 설정(Secrets)에 구글 시트 주소가 없습니다.")
    st.stop()

# CSV 데이터 추출 주소 생성
base_url = sheet_url.split("/edit")[0] if "/edit" in sheet_url else sheet_url
csv_url = f"{base_url}/gviz/tq?tqx=out:csv"

# 2. 구글 시트 데이터 불러오기 함수
@st.cache_data(ttl=5)
def load_data():
    cols = ["등록시간", "이름", "나이", "위치", "위도", "경도", "특징"]
    try:
        df = pd.read_csv(csv_url)
        return df if not df.empty else pd.DataFrame(columns=cols)
    except:
        return pd.DataFrame(columns=cols)

missing_db = load_data()

# 3. 사이드바 입력 양식 (완벽 한글화)
st.sidebar.header("📝 실종자 신규 등록")
with st.sidebar.form(key="reg_form", clear_on_submit=True):
    name = st.text_input("1. 실종자 성함")
    age = st.text_input("2. 나이")
    loc_name = st.text_input("3. 마지막 발견 위치", placeholder="예: 서울역, 제주도청")
    desc = st.text_area("4. 주요 특징 및 인상착의")
    submit = st.form_submit_button(label="🚨 시스템에 즉시 등록")

# 4. 등록 버튼 작동 로직
if submit:
    if name and loc_name:
        with st.spinner("🌍 위치 좌표를 찾는 중..."):
            try:
                loc = geolocator.geocode(loc_name)
                if loc:
                    new_row = {
                        "등록시간": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "이름": name,
                        "나이": age,
                        "위치": loc_name,
                        "위도": loc.latitude,
                        "경도": loc.longitude,
                        "특징": desc
                    }
                    if "temp_db" not in st.session_state:
                        st.session_state.temp_db = missing_db.copy()
                    st.session_state.temp_db = pd.concat([st.session_state.temp_db, pd.DataFrame([new_row])], ignore_index=True)
                    st.success(f"🎯 {name} 님의 정보가 성공적으로 등록되었습니다!")
                    st.rerun()
                else:
                    st.error("❌ 입력하신 위치를 지도에서 찾을 수 없습니다.")
            except:
                st.error("❌ 시스템 처리 중 오류가 발생했습니다.")
    else:
        st.error("❌ 이름과 위치는 필수 입력 사항입니다.")

# 화면에 표출할 데이터 선택
display_db = st.session_state.temp
