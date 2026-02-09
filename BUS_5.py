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
# [1] 설정 및 데이터
# ---------------------------------------------------------
st.set_page_config(page_title="동구5번 교통 안내", page_icon="🚌", layout="wide")

# 대구 1호선 전체 역 리스트 (노선 순서)
LINE_1_STATIONS = [
    "설화명곡", "화원", "대곡", "진천", "월배", "상인", "월촌", "송현", "서부정류장", "대명", 
    "안지랑", "현충로", "영대병원", "교대", "명덕", "반월당", "중앙로", "대구역", 
    "칠성시장", "신천", "동대구", "동구청", "아양교", "동촌", "해안", "방촌", 
    "용계", "율하", "신기", "반야월", "각산", "안심"
]

# 주요 거점 좌표 (거리 계산용)
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
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.dtro.or.kr/'
    }
    url = "https://www.dtro.or.kr/open_content_new/ko/OpenApi/stationTime.php"
    
    try:
        # 1. 시그니처 자동 추출
        first_res = session.get(url, headers=headers, verify=False, timeout=5)
        sig_match = re.search(r"sabSignature=([^']+)'", first_res.text)
        if sig_match:
            session.cookies.set('sabFingerPrint', '1920,1080,www.dtro.or.kr', domain='www.dtro.or.kr')
            session.cookies.set('sabSignature', sig_match.group(1), domain='www.dtro.or.kr')

        # 2. 역 이름 매칭 (반드시 '역'을 붙여서 시도)
        clean_nm = station_nm.replace("역", "")
        test_names = [clean_nm + "역", clean_nm]
        
        final_times = []
        for name in test_names:
            params = {
                'STT_NM': name,
                'LINE_NO': '1',
                'SCHEDULE_METH': direction,
                'SCHEDULE_TYPE': s_type
            }
            res = session.get(url, params=params, headers=headers, verify=False, timeout=10)
            res.encoding = 'utf-8'
            
            if "apiDataList" in res.text:
                root = ET.fromstring(res.text)
                schedule_str = root.findtext('.//SCHEDULE')
                if schedule_str and schedule_str != "-":
                    all_times = re.findall(r'(\d{1,2}:\d{2})', schedule_str)
                    now_str = now.strftime("%H:%M")
                    # 중복 제거 및 현재 시간 이후 5개 추출
                    final_times = sorted(list(set([t for t in all_times if t >= now_str])))[:5]
                    if final_times: break # 데이터를 찾았으면 중단
        return final_times
    except Exception as e:
        return []

# ---------------------------------------------------------
# [2] UI 구성
# ---------------------------------------------------------
st.title("🚌 동구5번 스마트 안내판")

# 상단 선택 메뉴
selected_mode = st.selectbox(
    "📍 정보를 확인할 역을 선택하세요:",
    ["자동 (GPS 추천)"] + LINE_1_STATIONS
)

# GPS 수신
location = get_geolocation()
target_station = ""

if selected_mode == "자동 (GPS 추천)":
    if location:
        u_lat, u_lon = location['coords']['latitude'], location['coords']['longitude']
        dists = [{"name": n, "m": int(haversine_distance(u_lat, u_lon, c['lat'], c['lon'])*1000)} for n, c in STATION_COORDS.items()]
        nearest = sorted(dists, key=lambda x: x['m'])[0]
        target_station = nearest['name']
        st.success(f"🛰️ GPS 기반 **{target_station}역** 추천 (거리: {nearest['m']}m)")
    else:
        st.warning("🛰️ GPS 수신 대기 중... 수동으로 역을 선택할 수 있습니다.")
        target_station = "반야월" # 기본값
else:
    target_station = selected_mode
    st.info(f"📍 직접 선택: **{target_station}역**")

# ---------------------------------------------------------
# [3] 시간표 출력 (성공했던 기존 방식 레이아웃)
# ---------------------------------------------------------
if target_station:
    st.subheader(f"🚅 {target_station}역 실시간 시간표")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🔼 상행 (설화명곡)")
        up_times = get_dtro_api_data(target_station, "UP")
        if up_times:
            for t in up_times: st.write(f"⏱️ **{t}**")
        else: st.error("운행 정보 없음")

    with col2:
        st.markdown("### 🔽 하행 (안심)")
        down_times = get_dtro_api_data(target_station, "DOWN")
        if down_times:
            for t in down_times: st.write(f"⏱️ **{t}**")
        else: st.error("운행 정보 없음")

st.divider()
if st.button('🔄 정보 새로고침'):
    st.rerun()
