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
# [1] 설정 및 노선 순서 데이터
# ---------------------------------------------------------
st.set_page_config(page_title="동구5번 교통 안내", page_icon="🚌", layout="wide")

# 대구 1호선 노선 순서대로 정렬 (역 선택 메뉴용)
LINE_1_STATIONS = [
    "설화명곡", "화원", "대곡", "진천", "월배", "상인", "월촌", "송현", "성당못", "대명", 
    "안지랑", "현충로", "영대병원", "교대", "명덕", "반월당", "중앙로", "대구역", 
    "칠성시장", "신천", "동대구", "동구청", "아양교", "동촌", "해안", "방촌", 
    "용계", "율하", "신기", "반야월", "각산", "안심"
]

# 주요 역 정밀 좌표 (거리 계산용)
STATION_COORDS = {
    "율하": {"lat": 35.867142, "lon": 128.682855},
    "신기": {"lat": 35.870025, "lon": 128.694625},
    "반야월": {"lat": 35.871842, "lon": 128.706725},
    "각산": {"lat": 35.868984, "lon": 128.718047},
    "안심": {"lat": 35.875322, "lon": 128.727402},
    "동대구": {"lat": 35.877400, "lon": 128.628500},
}

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

        # '역' 글자 처리 포함하여 요청
        target_nm = station_nm if station_nm.endswith("역") else station_nm + "역"
        params = {'STT_NM': target_nm, 'LINE_NO': '1', 'SCHEDULE_METH': direction, 'SCHEDULE_TYPE': s_type}
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
# [2] UI 레이아웃
# ---------------------------------------------------------
st.title("🚌 동구5번 스마트 안내판")

# 상단: 역 선택 메뉴 (기본값은 자동)
selected_mode = st.selectbox(
    "📍 정보를 확인하고 싶은 역을 선택하세요:",
    ["자동 (GPS 추천)"] + LINE_1_STATIONS
)

st.divider()

# 위치 정보 가져오기
location = get_geolocation()
target_station = ""

if selected_mode == "자동 (GPS 추천)":
    if location:
        u_lat, u_lon = location['coords']['latitude'], location['coords']['longitude']
        
        # 주요 역 중 가장 가까운 곳 찾기
        dists = []
        for name, coord in STATION_COORDS.items():
            d = haversine_distance(u_lat, u_lon, coord['lat'], coord['lon'])
            dists.append({"name": name, "m": int(d * 1000)})
        
        nearest = sorted(dists, key=lambda x: x['m'])[0]
        target_station = nearest['name']
        st.success(f"🛰️ GPS 추천: 현재 **{target_station}역**({nearest['m']}m) 근처입니다.")
    else:
        st.warning("🛰️ GPS 신호를 기다리는 중입니다... (신호가 약하면 아래 메뉴에서 역을 직접 선택하세요)")
        target_station = "반야월" # 기본값
else:
    target_station = selected_mode
    st.info(f"📍 사용자가 직접 **{target_station}역**을 선택했습니다.")

# ---------------------------------------------------------
# [3] 시간표 표시부
# ---------------------------------------------------------
if target_station:
    st.subheader(f"🚅 {target_station}역 실시간 도착 정보")
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("🔼 **상행 (설화명곡 방면)**")
        times_up = get_dtro_api_data(target_station, "UP")
        if times_up:
            for t in times_up: st.write(f"⏱️ **{t}**")
        else: st.write("운행 정보 없음")

    with col2:
        st.write("🔽 **하행 (안심 방면)**")
        times_down = get_dtro_api_data(target_station, "DOWN")
        if times_down:
            for t in times_down: st.write(f"⏱️ **{t}**")
        else: st.write("운행 정보 없음")

st.divider()
if st.button('🔄 새로고침'):
    st.rerun()

# 하단 정보
if location and selected_mode == "자동 (GPS 추천)":
    with st.expander("🔍 내 GPS 좌표 및 거리 상세"):
        st.write(f"좌표: `{u_lat}, {u_lon}`")
        st.write("※ 실내에서는 GPS 오차(최대 1km 이상)가 발생할 수 있습니다.")
