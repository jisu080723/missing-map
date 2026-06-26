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
st.title(" 🚓 실종자 보호자 직접 등록 및 실시간 관제 플랫폼")
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

# [수정 반영 1] 구글 시트에 '상태' 열이 있다면, '수색중'인 데이터만 필터링하여 지도와 리스트에 표시합니다.
# 발견 완료 처리된 실종자는 화면에서 자동으로 제외됩니다.
if not missing_database.empty and "상태" in missing_database.columns:
    missing_database = missing_database[missing_database["상태"] == "수색중"]

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
                    # 신규 등록 시 '상태'의 기본값은 '수색중', '수색현황'의 기본값은 '정보 업데이트 중'으로 설정하여 전송합니다.
                    data_payload = {
                        "등록시간": reg_time, "이름": name, "나이": age, "위치": location_name,
                        "위도": float(geocoded_location.latitude), "경도": float(geocoded_location.longitude), 
                        "특징": description, "상태": "수색중", "수색현황": "정보 업데이트 중"
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
    # [수정 반영 2] 피드백에 따라 타이틀의 반경 표시를 500m에서 200m로 변경했습니다.
    st.subheader("📍 실시간 수색 관제 지도 (반경 200m 원)")
    if missing_database.empty or "Y_COORDINATE" not in missing_database.columns:
        map_object = folium.Map(location=[36.5, 127.5], zoom_start=7)
    else:
        latest_latitude = float(missing_database.iloc[-1]["Y_COORDINATE"])
        latest_longitude = float(missing_database.iloc[-1]["X_COORDINATE"])
        map_object = folium.Map(location=[latest_latitude, latest_longitude], zoom_start=15)
        
        for index, row in missing_database.iterrows():
            try:
                person_name = row["이름"] if "이름" in row else "실종자"
                person_location = row["위치"] if "위치" in row else ""
                
                # [수정 반영 3] 구글 시트에서 실시간 '수색현황'과 '특징' 데이터를 가져옵니다.
                current_status = row["수색현황"] if "수색현황" in row else "정보 업데이트 중"
                person_desc = row["특징"] if "특징" in row else "미기재"
                
                # 마커 클릭 시 나타날 팝업창 디자인 구성 (실시간 수색현황 및 인상착의 포함)
                popup_text = f"""
                <div style='font-size: 11pt; font-family: sans-serif; line-height: 1.5;'>
                    <b>성함:</b> {person_name}<br>
                    <b>위치:</b> {person_location}<br>
                    <b>특징:</b> {person_desc}<br>
                    <hr style='margin: 8px 0; border: 0; border-top: 1px solid #ccc;'>
                    <span style='color: red; font-weight: bold;'>🚨 수색 진행 현황:</span><br>
                    {current_status}
                </div>
                """
                
                folium.Marker(
                    [float(row["Y_COORDINATE"]), float(row["X_COORDINATE"])],
                    popup=folium.Popup(popup_text, max_width=300),
                    icon=folium.Icon(color="red", icon="info-sign")
                ).add_to(map_object)
                
                # [수정 반영 4] 수색 집중도를 높이기 위해 원 반경(radius)을 기존 500에서 200(미터)으로 축소 조정했습니다.
                folium.Circle(
                    location=[float(row["Y_COORDINATE"]), float(row["X_COORDINATE"])],
                    radius=200, color="red", fill=True, fill_opacity=0.15
                ).add_to(map_object)
            except Exception:
                continue

    try:
        html_map_data = map_object._repr_html_()
        components.html(html_map_data, height=500, scrolling=False)
    except Exception:
        st.error("❌ 지도를 화면에 표시하지 못했습니다.")
