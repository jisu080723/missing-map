import streamlit as st
import folium
import pandas as pd
from datetime import datetime
from geopy.geocoders import Nominatim
import requests
import json
import streamlit.components.v1 as components
import time

st.set_page_config(page_title="실종자 관제", layout="wide")
st.title("🚓 실종자 보호자 직접 등록 및 실시간 관제 플랫폼")
st.caption("보호자가 입력한 정보는 구글 시트에 저장되며, 새로고침해도 사라지지 않습니다.")

geolocator = Nominatim(user_agent="missing_jisu_final_2026", timeout=10)

try:
    sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    api_url = st.secrets["connections"]["gsheets"]["api_url"]
except:
    st.error("❌ 스트림릿 Secrets 설정을 확인해 주세요.")
    st.stop()

base_url = sheet_url.split("/edit")[0] if "/edit" in sheet_url else sheet_url
csv_url = f"{base_url}/gviz/tq?tqx=out:csv"

@st.cache_data(ttl=1)
def load_data():
    try:
        # 구글 시트의 첫 줄을 제목(Header)으로 정상적으로 읽어옵니다.
        df = pd.read_csv(csv_url)
        if not df.empty:
            # 공백 및 글자 정리
            df.columns = [str(c).strip() for c in df.columns]
            
            # 💡 [핵심 패치] 순서와 상관없이 구글 시트에서 '위도'와 '경도'라는 글자가 적힌 열을 스스로 찾습니다.
            lat_col = [c for c in df.columns if "위도" in c or "lat" in c.lower()]
            lng_col = [c for c in df.columns if "경도" in c or "lng" in c.lower()]
            
            if lat_col and lng_col:
                # 찾은 칼럼의 데이터를 숫자로 강제 변환
                df["표시위도"] = pd.to_numeric(df[lat_col[0]], errors='coerce')
                df["표시경도"] = pd.to_numeric(df[lng_col[0]], errors='coerce')
                # 위도 경도가 정상적인 것만 남기기
                df = df.dropna(subset=["표시위도", "표시경도"])
            else:
                # 글자를 못 찾으면 강제로 위치(열 순서) 기준으로 매칭 시도
                if df.shape[1] >= 6:
                    df["표시위도"] = pd.to_numeric(df.iloc[:, 4], errors='coerce')
                    df["표시경도"] = pd.to_numeric(df.iloc[:, 5], errors='coerce')
                    df = df.dropna(subset=["표시위도", "표시경도"])
            return df
        return pd.DataFrame()
    except:
        return pd.DataFrame()

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
        with st.spinner("🌍 위치 좌표 검색 및 구글 시트 저장 중..."):
            try:
                time.sleep(1)
                loc = geolocator.geocode(loc_name)
                
                if loc:
                    new_row = {
                        "등록시간": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "이름": name, "나이": age, "위치": loc_name,
                        "위도": float(loc.latitude), "경도": float(loc.longitude), "특징": desc
                    }
                    headers = {"Content-Type": "application/json"}
                    res = requests.post(api_url, data=json.dumps(new_row), headers=headers)
                    
                    if res.status_code == 200:
                        st.success(f"🎯 {name} 님 등록 및 구글 저장 완료!")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("❌ 구글 시트 통신 실패 (API 오류)")
                else:
                    st.error("❌ 입력하신 위치를 찾을 수 없습니다. 더 명확한 주소로 적어주세요.")
            except Exception as e:
                st.error("❌ 주소 서버 지연. 잠시 후 다시 눌러주세요.")
    else:
        st.error("❌ 필수 항목을 채워주세요.")

c1, c2 = st.columns([1, 1])

with c1:
    st.subheader("📋 현재 등록된 실종자 누적 리스트")
    if missing_db.empty:
        st.info("현재 저장된 데이터가 없습니다.")
    else:
        st.dataframe(missing_db, use_container_width=True)

with c2:
    st.subheader("📍 실시간 수색 관제 지도 (반경 500m 원)")
    
    # 데이터가 없거나 위도경도가 깨졌으면 대한민국 중심 지도 표출
    if missing_db.empty or "표시위도" not in missing_db.columns or missing_db["표시위도"].empty:
        m = folium.Map(location=[36.5, 127.5], zoom_start=7)
    else:
        try:
            # 가장 마지막에 등록된 데이터의 좌표로 이동
            lat = float(missing_db.iloc[-1]["표시위도"])
            lng = float(missing_db.iloc[-1]["표시경도"])
            m = folium.Map(location=[lat, lng], zoom_start=14)
            
            for idx, row in missing_db.iterrows():
                try:
                    name_val = row["이름"] if "이름" in row else "실종자"
                    loc_val = row["위치"] if "위치" in row else ""
                    
                    folium.Marker(
                        [float(row["표시위도"]), float(row["표시경도"])],
                        popup=f"<b>{name_val}</b><br>{loc_val}",
                        icon=folium.Icon(color="red", icon="info-sign")
                    ).add_to(m)
                    
                    folium.Circle(
                        location=[float(row["표시위도"]), float(row["표시경도"])],
                        radius=500, color="red", fill=True, fill_opacity=0.15
                    ).add_to(m
