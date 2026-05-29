import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
from datetime import datetime

# 1. 페이지 기본 설정
st.set_page_config(page_title="실종자 직접 등록 및 관제 시스템", layout="wide")
st.title("开设 실종자 보호자 직접 등록 및 실시간 관제 플랫폼")
st.caption("보호자가 직접 실종 정보를 입력하면 실시간으로 지도와 리스트에 등록되어 공유됩니다.")

# 2. 데이터 누적 저장소 생성 (빈 상태로 시작)
if "missing_db" not in st.session_state:
    st.session_state.missing_db = pd.DataFrame(columns=["등록시간", "이름", "나이", "마지막 발견 위치", "위도", "경도", "특징"])

# 3. 사이드바 - 보호자 직접 입력 양식
st.sidebar.header("📝 실종자 신규 등록")
with st.sidebar.form(key="register_form", clear_on_submit=True):
    name = st.text_input("1. 실종자 성함")
    age = st.text_input("2. 나이")
    location_name = st.text_input("3. 마지막 발견 위치 설명")
    
    st.markdown("🌐 **4. 지도 좌표 입력 (구글 지도 등에서 확인)**")
    lat = st.number_input("위도 (Latitude)", value=37.5665, format="%.6f")
    lng = st.number_input("경도 (Longitude)", value=126.9780, format="%.6f")
    
    features = st.text_area("5. 주요 특징 (인상착의 등)")
    
    submit_button = st.form_submit_button(label="🚨 시스템에 즉시 등록")

# 4. 등록 버튼 클릭 시 데이터 추가 로직
if submit_button:
    if name and location_name:
        new_data = {
            "등록시간": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "이름": name,
            "나이": age,
            "마지막 발견 위치": location_name,
            "위도": lat,
            "경도": lng,
            "특징": features
        }
        st.session_state.missing_db = pd.concat([st.session_state.missing_db, pd.DataFrame([new_data])], ignore_index=True)
        st.success(f"🎯 {name} 님의 정보가 관제 시스템에 성공적으로 등록되었습니다!")
    else:
        st.error("❌ 이름과 마지막 발견 위치는 필수 입력 사항입니다.")

# 5. 메인 화면 구성
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📋 현재 등록된 실종자 누적 리스트")
    if st.session_state.missing_db.empty:
        st.info("현재 등록된 데이터가 없습니다. 왼쪽 입력창에서 첫 번째 실종자를 등록해 주세요.")
    else:
        st.dataframe(st.session_state.missing_db, use_container_width=True)

with col2:
    st.subheader("📍 실시간 수색 관제 지도 (반경 500m 원 표시)")
    
    # 데이터가 없을 때는 대한민국 중심(서울시청)을 보여주고, 데이터가 있으면 마지막 등록 위치 중심
    if st.session_state.missing_db.empty:
        m = folium.Map(location=[37.5665, 126.9780], zoom_start=7)
    else:
        last_lat = st.session_state.missing_db.iloc[-1]["위度"] if "위度" in st.session_state.missing_db.columns else st.session_state.missing_db.iloc[-1]["위도"]
        last_lng = st.session_state.missing_db.iloc[-1]["경도"]
        m = folium.Map(location=[last_lat, last_lng], zoom_start=13)
        
        # 입력된 데이터만 지도에 마커 표시
        for idx, row in st.session_state.missing_db.iterrows():
            folium.Marker(
                [row["위도"], row["경도"]],
                popup=f"<b>{row['이름']}</b>({row['나이']}세)<br>{row['마지막 발견 위치']}",
                icon=folium.Icon(color="red", icon="info-sign")
            ).add_to(m)
            
            folium.Circle(
                location=[row["위도"], row["경도"]],
                radius=500,
                color="red",
                fill=True,
                fill_opacity=0.15
            ).add_to(m)
            
    st_folium(m, width="100%", height=500)
