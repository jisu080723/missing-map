import streamlit as st
import folium
import pandas as pd
from datetime import datetime
from geopy.geocoders import Nominatim
import requests
import json
import streamlit.components.v1 as components

st.set_page_config(page_title="실종자 관제", layout="wide")
st.title("🚓 실종자 보호자 직접 등록 및 실시간 관제 플랫폼")
st.caption("보호자가 입력한 정보는 구글 시트에 저장되며, 새로고침해도 사라지지 않습니다.")

geolocator = Nominatim(user_agent="missing_jisu_2026")

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
            
            # 문자열로 들어온 위도 경도를 안전하게 숫자로 정제
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
    loc_name = st.text_input("3. 마지막 발견 위치", placeholder="예: 서울역")
    desc = st.text_area("4. 주요 특징 및 인상착의")
    submit = st.form_submit_button(label="🚨 시스템에 즉시 등록")

if submit:
    if name and loc_name:
        with st.spinner("🌍 구글 금고에 영구 저장하는 중..."):
            try:
                loc = geolocator.geocode(loc_name)
                if loc:
                    new_row = {
                        "등록시간": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "이름": name, "나이": age, "위치": loc_name,
                        "위도": float(loc.latitude), "경度": float(loc.longitude), "특징": desc
                    }
                    # 변수명 통일을 위한 재조정
                    send_row = {
                        "등록시간": new_row["등록시간"], "이름": new_row["이름"], "나이": new_row["나이"],
                        "위치": new_row["위치"], "위도": new_row["위도"], "경도": new_row["경度"], "특징": new_row["특징"]
                    }
                    headers = {"Content-Type": "application/json"}
                    res = requests.post(api_url, data=json.dumps(send_row), headers=headers)
                    
                    if res.status_code == 200:
                        st.success(f"🎯 {name} 님 구글 시트에 평생 저장 완료!")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("❌ 구글 시트 저장 실패 (API 오류)")
                else:
                    st.error("❌ 위치를 찾을 수 없습니다.")
            except:
                st.error("❌ 시스템 처리 중 오류 발생")
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
    
    # 데이터가 아예 없으면 대한민국 전도 기본 표출
    if missing_db.empty:
        m = folium.Map(location=[36.5, 127.5], zoom_start=7)
    else:
        # 가장 마지막에 등록된 진짜 위치를 중심으로 설정
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
            
    # HTML 강제 출력 방식으로 지도 표출
    try:
        map_html = m._repr_html_()
        components.html(map_html, height=500, scrolling=False)
    except:
        st.error("지도를 그리는 중 오류가 발생했습니다.")
