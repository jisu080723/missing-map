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

# 주소 변환기 세팅 및 타임아웃 넉넉하게 지정
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
    cols = ["등록시간", "이름", "나이", "위치", "위도", "경도", "특징"]
    try:
        df = pd.read_csv(csv_url, header=None)
        if len(df) > 1:
            if "위도" in str(df.iloc[0]) or "이름" in str(df.iloc[0]) or "lat" in str(df.iloc[0]).lower():
                df = df.iloc[1:]
            if df.shape[1] < 7:
                for i in range(7 - df.shape[1]):
                    df[df.shape[1]] = ""
            df = df.iloc[:, :7]
            df.columns = cols
            
            df["위도"] = pd.to_numeric(df["위도"], errors='coerce')
            df["경도"] = pd.to_numeric(df["경도"], errors='coerce')
            df = df.dropna(subset=["위도", "경도"])
            return df
        return pd.DataFrame(columns=cols)
    except:
        return pd.DataFrame(columns=cols)

missing_db = load_data()

st.sidebar.header("📝 실종자 신규 등록")
with st.sidebar.form(key="reg_form", clear_on_submit=True):
    name = st.text_input("1. 실종자 성함")
    age = st.text_input("2. 나이")
    loc_name = st.text_input("3. 마지막 발견 위치 (정확한 주소나 명칭)", placeholder="예: 서울 종로구 세종대로 209")
    desc = st.text_area("4. 주요 특징 및 인상착의")
    submit = st.form_submit_button(label="🚨 시스템에 즉시 등록")

if submit:
    if name and loc_name:
        with st.spinner("🌍 위치 좌표 검색 및 구글 시트 저장 중..."):
            try:
                # 인터넷 주소 변환 서버 과부하를 막기 위해 1초 대기 후 요청
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
                        st.success(f"🎯 {name} 님 구글 시트에 평생 저장 완료!")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("❌ 구글 시트 웹앱 연결 실패 (2단계 설정을 확인해 주세요)")
                else:
                    st.error("❌ 입력하신 주소를 지도에서 찾을 수 없습니다. 정확한 구/동/건물명으로 적어보세요.")
            except Exception as e:
                # 에러 원인을 화면에 명확하게 띄워주기
                st.error(f"❌ 주소 검색 서버 접속 지연. 2~3초 뒤 다시 [즉시 등록] 버튼을 눌러주세요.")
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
    
    if missing_db.empty:
        m = folium.Map(location=[36.5, 127.5], zoom_start=7)
    else:
        lat = float(missing_db.iloc[-1]["위도"])
        lng = float(missing_db.iloc[-1]["경도"])
        m = folium.Map(location=[lat, lng], zoom_start=14)
        
        for idx, row in missing_db.iterrows():
            try:
                folium.Marker(
                    [float(row["위도"]), float(row["경도"])],
                    popup=f"<b>{row['이름']}</b>({row['나이']}세)<br>{row['위치']}",
                    icon=folium.Icon(color="red", icon="info-sign")
                ).add_to(m)
                
                folium.Circle(
                    location=[float(row["위도"]), float(row["경도"])],
                    radius=500, color="red", fill=True, fill_opacity=0.15
                ).add_to(m)
            except:
                continue
            
    try:
        map_html = m._repr_html_()
        components.html(map_html, height=500, scrolling=False)
    except:
        st.error("지도를 그리는 화면에 문제가 발생했습니다.")
