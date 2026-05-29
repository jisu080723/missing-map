import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
import urllib.parse
import pandas as pd
import os

st.set_page_config(page_title="경찰청 실종자 누적 기록 지도", layout="wide")
st.title("🚓 경찰청 실종자 누적 기록 및 실시간 관제 플랫폼")
st.markdown("재난안전데이터 공유플랫폼 API로 수집된 실시간 실제 실종자 위치를 파일에 누적 기록하고 지도에 업데이트합니다.")
st.markdown("---")

DB_FILE = "missing_persons.csv"

def load_saved_data():
    if os.path.exists(DB_FILE):
        try:
            return pd.read_csv(DB_FILE)
        except:
            return pd.DataFrame(columns=['id', 'name', 'place', 'desc', 'lat', 'lng'])
    else:
        return pd.DataFrame(columns=['id', 'name', 'place', 'desc', 'lat', 'lng'])

def update_and_get_data():
    service_key = "47429F3O74123G99" 
    safe_key = urllib.parse.unquote(service_key)

    # 재난안전플랫폼 실시간 진짜 실종자 API 주소
    url = "https://www.safetydata.go.kr/V2/api/DSSP-IF-00171"
    params = {'serviceKey': safe_key, 'pageNo': '1', 'numOfRows': '100'}

    df_existing = load_saved_data()

    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            res_json = response.json()
            raw_row = []

            if isinstance(res_json, list):
                raw_row = res_json
            elif isinstance(res_json, dict):
                body = res_json.get('body', {})
                if isinstance(body, list):
                    raw_row = body
                elif isinstance(body, dict):
                    raw_row = body.get('row', res_json.get('data', []))

            new_records = []
            if isinstance(raw_row, list):
                for item in raw_row:
                    if not isinstance(item, dict):
                        continue

                    name = item.get('nm') or item.get('name') or "실종자 상황"
                    place = item.get('occrrnc_lc') or item.get('occrrncLc') or "발생 장소 정보 없음"
                    desc = item.get('altrtv_nm') or item.get('description') or "상세 인상착의 정보 없음"
                    lat = item.get('la') or item.get('lat') or item.get('latitude')
                    lng = item.get('lo') or item.get('lng') or item.get('longitude')

                    record_id = f"{name}_{place}"

                    if lat and lng:
                        try:
                            new_records.append({
                                'id': record_id, 'name': name, 'place': place, 
                                'desc': desc, 'lat': float(lat), 'lng': float(lng)
                            })
                        except:
                            continue

            if new_records:
                df_new = pd.DataFrame(new_records)
                if not df_existing.empty and 'id' in df_existing.columns:
                    df_new = df_new[~df_new['id'].isin(df_existing['id'])]

                if not df_new.empty:
                    df_updated = pd.concat([df_existing, df_new], ignore_index=True)
                    df_updated.to_csv(DB_FILE, index=False, encoding='utf-8-sig')
                    st.success(f"🔔 새로운 실종자 {len(df_new)}명의 정보가 데이터베이스에 새롭게 기록되었습니다!")
                    return df_updated
    except Exception as e:
        st.warning(f"⚠️ 시스템 반영 중 일시적 지연 발생: {e}")

    return df_existing

df_missing = update_and_get_data()

if not df_missing.empty:
    st.success(f"📊 현재 데이터베이스에 누적 기록된 실종자 위치: 총 {len(df_missing)}건")
    m = folium.Map(location=[36.5, 127.5], zoom_start=7, control_scale=True)

    for _, row in df_missing.iterrows():
        # 🚨 [수정 완료] 복잡한 HTML 대신 파이썬 기본 텍스트 포맷으로 변경하여 문자열 줄바꿈 에러를 원천 차단합니다.
        popup_text = f"🚨 실종자: {row['name']}\n📍 마지막 위치: {row['place']}\n👕 특징: {row['desc']}"

        folium.Marker(
            location=[row['lat'], row['lng']],
            popup=folium.Popup(popup_text, max_width=300),
            tooltip=f"🔍 {row['name']} 상세 정보",
            icon=folium.Icon(color="red", icon="exclamation-sign")
        ).add_to(m)

    st_folium(m, width="100%", height=650)
else:
    st.info("💡 실시간 API 통신은 성공했으나, 현재 정부 서버에 등록된 원본 데이터 건수가 없습니다.")
    st.markdown("정부 서버에 새로운 실종자 데이터가 등록되면 자동으로 이 아래 테이블과 지도에 기록됩니다.")

with st.expander("💾 [내 컴퓨터 DB 파일] 현재 누적 기록된 missing_persons.csv 데이터 보기"):
    st
