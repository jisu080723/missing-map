import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
from datetime import datetime
from geopy.geocoders import Nominatim

st.set_page_config(page_title="🚨", layout="wide")
st.title("🚓 Missing Person Management System")

geolocator = Nominatim(user_agent="missing_person_map_jisu_2026")

try:
    sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
except:
    st.error("No Sheet URL in Secrets")
    st.stop()

base_url = sheet_url.split("/edit")[0] if "/edit" in sheet_url else sheet_url
csv_url = f"{base_url}/gviz/tq?tqx=out:csv"

@st.cache_data(ttl=5)
def load_data():
    cols = ["등록시간", "이름", "나이", "위치", "위도", "경도", "특징"]
    try:
        df = pd.read_csv(csv_url)
        return df if not df.empty else pd.DataFrame(columns=cols)
    except:
        return pd.DataFrame(columns=cols)

missing_db = load_data()

st.sidebar.header("📝 Register")
with st.sidebar.form(key="reg_form", clear_on_submit=True):
    name = st.text_input("1. Name")
    age = st.text_input("2. Age")
    loc_name = st.text_input("3. Location", placeholder="e.g. Seoul Station")
    desc = st.text_area("4. Features")
    submit = st.form_submit_button(label="🚨 Register Now")

if submit:
    if name and loc_name:
        with st.spinner("Searching..."):
            try:
                loc = geolocator.geocode(loc_name)
                if loc:
                    new_row = {
                        "등록시간": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "이름": name,
                        "나이": age,
                        "위치": loc_name,
                        "위도": loc.latitude,
                        "경도": loc.longitude,
                        "특징": desc
                    }
                    if "temp_db" not in st.session_state:
                        st.session_state.temp_db = missing_db.copy()
                    st.session_state.temp_db = pd.concat([st.session_state.temp_db, pd.DataFrame([new_row])], ignore_index=True)
                    st.success("Success!")
                    st.rerun()
                else:
                    st.error("Location not found.")
            except:
                st.error("Error occurred.")
    else:
        st.error("Fill the form.")

display_db = st.session_state.temp_db if "temp_db" in st.session_state else missing_db

c1, c2 = st.columns([1, 1])

with c1:
    st.subheader("📋 실종자 누적 리스트")
    if display_db.empty:
        st.info("No Data")
    else:
        st.dataframe(display_db[["등록시간", "이름", "나이", "위치", "특징"]], use_container_width=True)
