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

# 전체 원본 데이터 로드
raw_database = load_google_sheet_data()

# 지도와 리스트에 표시할 데이터 (수색중인 데이터만 필터링)
if not raw_database.empty and "상태" in raw_database.columns:
    missing_database = raw_database[raw_database["상태"] == "수색중"]
else:
    missing_database = raw_database

# ----------------- 좌측 사이드바: 1. 신규 등록 폼 -----------------
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
                        "action": "insert",  # 신규 등록 액션 명령어
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

st.sidebar.markdown("---")

# ----------------- [새로 추가된 기능] 좌측 사이드바: 2. 관리자 제어 패널 -----------------
st.sidebar.header("⚙️ 관리자 전용 관제 패널")
if not missing_database.empty:
    # 현재 수색 중인 실종자 이름 목록 생성
    active_list = missing_database["이름"].tolist()
    selected_name = st.sidebar.selectbox("상태를 변경할 실종자 선택", active_list)
    
    # 선택된 실종자의 기존 수색 현황 가져오기
    selected_row = missing_database[missing_database["이름"] == selected_name].iloc[0]
    existing_status = selected_row["수색현황"] if "수색현황" in selected_row else ""
    
    new_status_text = st.sidebar.text_input("📍 실시간 수색 현황 업데이트", value=existing_status)
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        update_status_btn = st.button("📝 현황 업데이트")
    with col2:
        complete_btn = st.button("✅ 수색 완료 처리")
        
    # 현황 텍스트만 업데이트 할 때
    if update_status_btn:
        with st.spinner("구글 시트에 실시간 현황 동기화 중..."):
            update_payload = {"action": "update", "이름": selected_name, "수색현황": new_status_text, "상태": "수색중"}
            res = requests.post(api_url, data=json.dumps(update_payload), headers={"Content-Type": "application/json"})
            if res.status_code == 200:
                st.toast(f"📢 {selected_name} 님의 수색 현황이 업데이트되었습니다!")
                st.cache_data.clear()
                st.rerun()
                
    # 수색 완료 버튼을 눌렀을 때 (자동으로 리스트/지도에서 지우기)
    if complete_btn:
        with st.spinner("구글 시트에 완료 상태 체크 및 자동 반영 중..."):
            complete_payload = {"action": "update", "이름": selected_name, "수색현황": "수색 완료 및 안전 귀가", "상태": "발견완료"}
            res = requests.post(api_url, data=json.dumps(complete_payload), headers={"Content-Type": "application/json"})
            if res.status_code == 200:
                st.success(f"🎉 {selected_name} 님 무사 귀가! 복귀 처리 완료.")
                st.cache_data.clear()
                st.rerun()
else:
    st.sidebar.info("현재 수색 중인 실종자가 없어 관제 패널이 비활성화되었습니다.")


# ----------------- 우측 메인 화면: 리스트 및 지도 표시 -----------------
column_left, column_right = st.columns([1, 1])

with column_left:
    st.subheader("📋 현재 등록된 실종자 누적 리스트")
    if not missing_database.empty:
        st.dataframe(missing_database, use_container_width=True)
    else:
        st.info("현재 수색 중인 실종자 데이터가 없습니다.")

with column_right:
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
                current_status = row["수색현황"] if "수색현황" in row else "정보 업데이트 중"
                person_desc = row["특징"] if "특징" in row else "미기재"
                
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
