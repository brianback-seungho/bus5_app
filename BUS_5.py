import streamlit as st
import requests
import holidays
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from streamlit_js_eval import get_geolocation
import pandas as pd
import numpy as np

# ---------------------------------------------------------
# [1] 설정 및 정밀 좌표 (지도 기반 재조정)
# ---------------------------------------------------------
st.set_page_config(page_title="동구5번 교통 안내", page_icon="🚌", layout="wide")

# 지도 위치를 반영하여 반야월역 좌표를 1번 출구 근처로 미세 조정
STATION_DATA = [
    {"name": "반야월", "lat": 35.871500, "lon": 128.706500}, # 1번 출구 인근
    {"name": "각산", "lat": 35.868984, "lon": 128.718047},
    {"name": "신기", "lat": 35.870025, "lon": 128.694625},
    {"name": "율하", "lat": 35.867142, "lon": 128.682855}
]

def get_now_korea():
    return datetime.utcnow() + timedelta(hours=9)

def haversine_distance(lat1, lon1, lat2, lon2):
    r = 6371 
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi, dlambda = np.radians(lat2-lat1), np.radians(lon2-lon1)
    a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlambda/2)**2
    return 2 * r * np.arcsin(np.sqrt(a))

def get_dtro_api_data(station_nm, direction):
    now = get_now_korea()
    is_holiday = now in holidays.KR()
    weekday = now.weekday()
    s_type = "HOLIDAY" if (is_holiday or weekday == 6) else ("SATURDAY" if weekday == 5 else "WEEKDAY")
    
    session = requests.Session()
    headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.dtro.or.kr/'}
    url = "https://www.dtro.or.kr/open_content_new/ko/OpenApi/stationTime.php"
    
    try:
        first = session.get(url, headers=headers, verify=False, timeout=5)
        sig = re.search(r"sabSignature=([^']+)'", first.text)
        if sig:
            session.cookies.set('sabFingerPrint', '1920,1080,www.dtro.or.kr', domain='www.dtro.or.kr')
            session.cookies.set('sabSignature', sig.group(1), domain='www.dtro.or.kr')

        params = {'STT_NM': station_nm, 'LINE_NO': '1', 'SCHEDULE_METH': direction, 'SCHEDULE_TYPE': s_type}
        res = session.get(url, params=params, headers=headers, verify=False, timeout=10)
        res.encoding = 'utf-8'
        
        if "apiDataList" in res.text:
            root = ET.fromstring(res.text)
            schedule_str = root.findtext('.//SCHEDULE')
            if schedule_str and schedule_str != "-":
                all_times = re.findall(r'(\d{1,2}:\d{2})', schedule_str)
                now_str = now.strftime("%H:%M")
                return sorted(list(set([t for t in all_times if t >= now_str])))[:5]
        return []
    except: return []

# ---------------------------------------------------------
# [2] 메인 UI
# ---------------------------------------------------------
st.title("🚌 동구5번 스마트 안내판")
st.info(f"📅 현재 시각: **{get_now_korea().strftime('%H:%M:%S')}**")

location = get_geolocation()

if location:
    u_lat, u_lon = location['coords']['latitude'], location['coords']['longitude']
    
    # 거리 계산
    dists = []
    for s in STATION_DATA:
        d = haversine_distance(u_lat, u_lon, s['lat'], s['lon'])
        dists.append({"name": s['name'], "m": int(d * 1000)})
    
    df_sorted = pd.DataFrame(dists).sort_values(by="m")
    nearest_station = df_sorted.iloc[0]['name']
    
    # 결과 출력
    st.success(f"📍 현재 **{nearest_station}역**이 가장 가깝습니다. (거리: {df_sorted.iloc[0]['m']}m)")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader(f"🚅 {nearest_station}역 상행")
        times = get_dtro_api_data(nearest_station, "UP")
        if times:
            for t in times: st.write(f"⏱️ **{t}**")
        else: st.write("운행 정보 없음")
        
    with col2:
        st.subheader(f"🚅 {nearest_station}역 하행")
        times = get_dtro_api_data(nearest_station, "DOWN")
        if times:
            for t in times: st.write(f"⏱️ **{t}**")
        else: st.write("운행 정보 없음")

    # 진단용 정보 (오류 발생 시 확인용)
    with st.expander("🔍 GPS 정밀 진단 데이터"):
        st.write(f"내 위도: `{u_lat}`, 경도: `{u_lon}`")
        st.table(df_sorted)
else:
    st.warning("🛰️ GPS 수신 대기 중... 반야월파크뷰 위치를 확인하고 있습니다.")

st.divider()
if st.button('🔄 새로고침'): st.rerun()
