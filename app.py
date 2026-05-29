import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
from datetime import datetime
from geopy.geocoders import Nominatim

st.set_page_config(page_title="실종자 영구 등록 및 관제 시스템", layout="wide")
st.title("🚓 실종자 보호자 직접 등록 및 실시간 관제 플랫폼")
st.caption("보호자가 입력한 정보는 구글 시트에 저장되며, 새로고침해도 사라지지 않습니다.")

geolocator = Nominatim(user_agent="missing_person_map_jisu_2026")

try:
    sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
except:
    st.error("❌ 스트림릿 Secrets에 구글 시트 주소가 설정되지 않았습니다.")
    st.stop()

base_url = sheet_url.split("/edit")[0] if "/edit" in sheet_url else sheet_url
csv_export_url = f"{base_url}/gviz/tq?tqx=out:csv"

@st.cache_data(ttl=5)
def load_permanent_data():
    try:
        df = pd.read_csv(csv_export_url)
        return df if not df.empty else pd.DataFrame(columns=["등록시간", "이름", "나이", "위치", "위도", "경도", "특징"])
    except:
        return pd.DataFrame(columns=["등록시간", "이름", "나이", "위치", "위도", "경도", "특징"])

missing_db = load_permanent_data()

st.sidebar.header("📝 실종자 신규 등록")
with st.sidebar.form(key="register_form", clear_on_submit=True):
    name = st.text_input("1. 실종자 성함")
    age = st.text_input("2. 나이")
    location_name = st.text_input("3. 마지막 발견 위치 (주소 또는 건물명)", placeholder="예: 서울역, 제주도청")
    features = st.text_area("4. 주요 특징 (인상착의 등)")
    submit_button = st.form_submit_button(label="🚨 시스템에 즉시 등록")

if submit_button:
    if name and location_name:
        with st.spinner("🌍 위치 좌표를 찾는 중..."):
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
                    st.success(f"🎯 {name} 님의 정보가 등록되었습니다!")
                    st.rerun()
                else:
                    st.error(f"❌ '{location_name}' 위치를 찾을 수 없습니다.")
            except:
                st.error("시스템 처리 중 오류가 발생했습니다.")
    else:
        st.error("❌ 이름과 위치는 필수 입력 사항입니다.")

display_db = st.session_state.temp_db if "temp_db" in st.session_state else missing_db

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📋 등록된 실종자 리스트")
    if display_db.empty:
        st.info("현재 저장된 데이터가 없습니다.")
    else:
        st.dataframe(display_db[["등록시간", "이름", "나이", "위치", "특징"]], use_container_width=True)

with col2:
    st.subheader("📍 실시간 수색 관제 지도 (반경 5
