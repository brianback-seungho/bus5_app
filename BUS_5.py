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
# 설정
MY_SERVICE_KEY = "6fc222f7a07ce61876bf07b46533721a192b38b26b2ff8aff34d8bdc837f5ba1" 
st.set_page_config(page_title="동구5번 교통 안내", page_icon="🚌", layout="wide")

# 지하철역 좌표 데이터 (1호선 주요 역)
STATION_COORDS = [
    {"name": "반야월", "lat": 35.8718, "lon": 128.7067},
    {"name": "동대구", "lat": 35.8774, "lon": 128.6285},
    {"name": "각산", "lat": 35.8690, "lon": 128.7180},
    {"name": "안심", "lat": 35.8753, "lon": 128.7274},
    {"name": "신기", "lat": 35.8700, "lon": 128.6946},
    {"name": "율하", "lat": 35.8671, "lon": 128.6828},
    {"name": "반월당", "lat": 35.8648, "lon": 128.5933}
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
        # 시그니처 획득
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
                return sorted(list(set([t for t in all_times if t >= now_str])))[:5], s_type
        return [], s_type
    except: return [], s_type

# --- UI 시작 ---
st.title("🚌 동구5번 스마트 안내판 (위치기반)")
now_k = get_now_korea()
st.info(f"📅 현재 시각: **{now_k.strftime('%H:%M:%S')}**")

# 2. GPS 수신
location = get_geolocation()

if location:
    u_lat, u_lon = location['coords']['latitude'], location['coords']['longitude']
    
    # 가장 가까운 역 계산
    dists = [{"name": s["name"], "dist": haversine_distance(u_lat, u_lon, s["lat"], s["lon"])} for s in STATION_COORDS]
    nearest = sorted(dists, key=lambda x: x['dist'])[0]
    target_station = nearest['name']
    
    st.success(f"📍 현재 위치에서 **{target_station}역**({round(nearest['dist'], 2)}km)이 가장 가깝습니다.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader(f"🚅 {target_station}역 상행")
        times, mode = get_dtro_api_data(target_station, "UP")
        if times:
            for t in times: st.write(f"⏱️ **{t}** 출발")
        else: st.write("운행 정보 없음")
        
    with col2:
        st.subheader(f"🚅 {target_station}역 하행")
        times, mode = get_dtro_api_data(target_station, "DOWN")
        if times:
            for t in times: st.write(f"⏱️ **{t}** 출발")
        else: st.write("운행 정보 없음")
else:
    st.warning("🛰️ GPS 수신 대기 중... 스마트폰의 위치 권한을 허용해 주세요.")
    st.info("💡 팁: 스트림릿 클라우드의 HTTPS 주소로 접속해야 위치 팝업이 뜹니다.")

st.divider()
if st.button('🔄 정보 새로고침'): st.rerun()
