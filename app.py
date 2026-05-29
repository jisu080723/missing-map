import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
from datetime import datetime
from geopy.geocoders import Nominatim
from st_gsheets import GSheetsConnection

# 1. 페이지 기본 설정
st.set_page_config(page_title="실종자 영구 등록 및 관제 시스템", layout="wide")
st.title("🚓 실종자 보호자 직접 등록 및 실시간 관제 플랫폼")
st.caption("보호자가 입력한 정보는 구글 시트(DB)에 영구 저장되며, 새로고침해도 사라지지 않습니다.")

# 도구 로딩 (주소 변환기 및 구글 시트 연결)
geolocator = Nominatim(user_agent="missing_person_map_jisu_2026")
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. 구글 시트에서 기존에 저장된 데이터 평생 읽어오기
@st.cache_data(ttl=5)  # 5초마다 구글 시트의 최신 데이터를 확인합니다.
def load_permanent_data():
    try:
        # 구글 시트 데이터를 읽어옵니다.
        df = conn.read(ttl="5s")
        return df
    except Exception:
        # 만약 구글 시트가 아예 비어있거나 처음 만들었을 때를 위한 기본 틀(뼈대)
        return pd.DataFrame(columns=["등록시간", "이름", "나이", "입력한 위치", "위도", "경도", "특징"])

missing_db = load_permanent_data()

# 3. 사이드바 - 보호자 직접 입력 양식
st.sidebar.header("📝 실종자 신규 등록")
with st.sidebar.form(key="register_form", clear_on_submit=True):
    name = st.text_input("1. 실종자 성함")
    age = st.text_input("2. 나이")
    location_name = st.text_input("3. 마지막 발견 위치 (주소 또는 건물명)", placeholder="예: 서울역, 제주도청")
    features = st.text_area("4. 주요 특징 (인상착의 등)")
    
    submit_button = st.form_submit_button(label="🚨 시스템에 즉시 등록")

# 4. 등록 버튼 클릭 시 구글 시트에 영구 저장하기
if submit_button:
    if name and location_name:
        with st.spinner("🌍 위치 좌표를 찾고 구글 금고에 영구 저장하는 중..."):
            try:
                # 사용자가 입력한 문장으로 위도/경도 자동 검색
                location = geolocator.geocode(location_name)
                
                if location:
                    new_data = pd.DataFrame([{
                        "등록시간": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "이름": name,
                        "나이": age,
                        "입력한 위치": location_name,
                        "위도": location.latitude,
                        "경도": location.longitude,
                        "특징": features
                    }])
                    
                    # 기존 데이터에 새 데이터 합치기
                    updated_df = pd.concat([missing_db, new_data], ignore_index=True)
                    
                    # ⭐ 구글 시트에 업데이트(덮어쓰기) 명령!
                    conn.update(data=updated_df)
                    
                    st.success(f"🎯 {name} 님의 정보가 구글 시트에 평생 저장되었습니다!")
                    st.cache_data.clear() # 캐시를 지워서 화면에 즉시 반영
                    st.rerun()
                else:
                    st.error(f"❌ '{location_name}' 위치를 찾을 수 없습니다. 정확한 명칭으로 입력해 주세요.")
            except Exception as e:
                st.error("저장 중 오류가 발생했습니다. 구글 시트 연결 설정을 확인해 주세요.")
    else:
        st.error("❌ 이름과 마지막 발견 위치는 필수 입력 사항입니다.")

# 5. 메인 화면 구성
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📋 현재 등록된 실종자 누적 리스트")
    if missing_db.empty or len(missing_db) == 0:
        st.info("현재 저장된 데이터가 없습니다. 왼쪽 입력창에서 첫 번째 실종자를 등록해 주세요.")
    else:
        st.dataframe(missing_db[["등록시간", "이름", "나이", "입력한 위치", "특징"]], use_container_width=True)

with col2:
    st.subheader("📍 실시간 수색 관제 지도 (반경 500m 원 표시)")
    
    if missing_db.empty or len(missing_db) == 0:
        m = folium.Map(location=[36.5, 127.5], zoom_start=7)
    else:
        last_lat = float(missing_db.iloc[-1]["위도"])
        last_lng = float(missing_db.iloc[-1]["경도"])
        m = folium.Map(location=[last_lat, last_lng], zoom_start=14)
        
        # 구글 시트에 저장된 모든 사람을 지도에 핀으로 복원
        for idx, row in missing_db.iterrows():
            try:
                folium.Marker(
                    [float(row["위도"]), float(row["경도"])],
                    popup=f"<b>{row['이름']}</b>({row['나이']}세)<br>{row['입력한 위치']}",
                    icon=folium.Icon(color="red", icon="info-sign")
                ).add_to(m)
                
                folium.Circle(
                    location=[float(row["위도"]), float(row["경도"])],
                    radius=500,
                    color="red",
                    fill=True,
                    fill_opacity=0.15
                ).add_to(m)
            except:
                continue
            
    st_folium(m, width="100%", height=500)
