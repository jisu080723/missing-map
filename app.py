import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
from datetime import datetime
from geopy.geocoders import Nominatim
import requests
import json

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
    try:
        # 데이터 유실 방지를 위해 헤더 없이 순수 데이터만 가져옵니다.
        df = pd.read_csv(csv_url, header=None)
        if len(df) > 1:
            # 첫 번째 줄이 만약 제목줄(텍스트)이면 제외하고 데이터만 슬라이싱
            if "위도" in str(df.iloc[0]) or "이름" in str(df.iloc[0]) or "lat" in str(df.iloc[0]).lower():
                df = df.iloc[1:]
            
            # 구글 시트 열 순서에 맞춰 강제로 칼럼 매칭 (0번째=등록시간, 1번째=이름...)
            df.columns = ["등록시간", "이름", "나이", "위치", "위도", "경도", "특징"]
            
            # 위도와 경도를 강제 숫자로 변환하고 에러는 버림
            df["위도"] = pd.to_numeric(df["위도"], errors='coerce')
            df["경도"] = pd.to_numeric(df["경도"], errors='coerce')
            df = df.dropna(subset=["위도", "경도"])
            return df
        return pd.DataFrame(columns=["등록시간", "이름", "나이", "위치", "위도", "경도", "특징"])
    except:
        return pd.DataFrame(columns=["등록시간", "이름", "나이", "위치", "위도", "경도", "특징"])

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
                        "위도": float(loc.latitude), "경도": float(loc.longitude), "특징": desc
                    }
                    headers = {"Content-Type": "application/json"}
                    res = requests.post(api_url, data=json.dumps(new_row), headers=headers)
                    
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
        st.dataframe(missing_db)
