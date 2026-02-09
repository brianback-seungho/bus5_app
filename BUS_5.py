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
# [1] 전 노선 데이터 정의 (1~3호선)
# ---------------------------------------------------------
st.set_page_config(page_title="동구5번 교통 안내", page_icon="🚌", layout="wide")

LINE_STATIONS = {
    "1호선": ["설화명곡", "화원", "대곡", "진천", "월배", "상인", "월촌", "송현", "서부정류장", "대명", "안지랑", "현충로", "영대병원", "교대", "명덕", "반월당", "중앙로", "대구역", "칠성시장", "신천", "동대구", "동구청", "아양교", "동촌", "해안", "방촌", "용계", "율하", "신기", "반야월", "각산", "안심"],
    "2호선": ["문양", "다사", "대실", "강창", "계명대", "성서산업단지", "이곡", "용산", "죽전", "감삼", "두류", "내당", "반고개", "청라언덕", "반월당", "경대병원", "범어", "수성구청", "만촌", "담티", "연호", "대공원", "고산", "신매", "사월", "정평", "임당", "영남대"],
    "3호선": ["칠곡경대병원", "학정", "팔거", "동천", "칠곡운암", "구암", "태전", "매천시장", "매천", "팔달", "공단", "만평", "팔달시장", "원대", "북구청", "달성공원", "서문시장", "청라언덕", "남산", "명덕", "건들바위", "대봉교", "수성시장", "수성구민운동장", "어린이세상", "황금", "수성못", "지산", "범물", "용지"]
}

STATION_COORDS = {
    "반야월": {"lat": 35.871842, "lon": 128.706725, "line": "1"},
    "각산": {"lat": 35.868984, "lon": 128.718047, "line": "1"},
    "신기": {"lat": 35.870025, "lon": 128.694625, "line": "1"},
    "율하": {"lat": 35.867142, "lon": 128.682855, "line": "1"},
    "동대구": {"lat": 35.877400, "lon": 128.628500, "line": "1"}
}

def get_now_korea():
    return datetime.utcnow() + timedelta(hours=9)

def haversine_distance(lat1, lon1, lat2, lon2):
    r = 6371 
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi, dlambda = np.radians(lat2-lat1), np.radians(lon2-lon1)
    a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlambda/2)**2
    return 2 * r * np.arcsin(np.sqrt(a))

# ---------------------------------------------------------
# [2] 핵심: 데이터 수신 안정화 로직 (가장 중요)
# ---------------------------------------------------------
def get_dtro_api_data(station_nm, line_no, direction):
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
        # 1. 보안 통과를 위한 시그니처 세션 획득
        first_res = session.get(url, headers=headers, verify=False, timeout=5)
        sig_match = re.search(r"sabSignature=([^']+)'", first_res.text)
        if sig_match:
            session.cookies.set('sabFingerPrint', '1920,1080,www.dtro.or.kr', domain='www.dtro.or.kr')
            session.cookies.set('sabSignature', sig_match.group(1), domain='www.dtro.or.kr')

        # 2. 역 이름 매칭 (데이터가 나올 때까지 3단 시도)
        clean_nm = station_nm.replace("역", "")
        test_names = [clean_nm + "역", clean_nm]
        
        for name in test_names:
            params = {
                'STT_NM': name, 
                'LINE_NO': line_no, 
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
                    times = sorted(list(set([t for t in all_times if t >= now_str])))[:5]
                    if times: return times
        return []
    except:
        return []

# ---------------------------------------------------------
# [3] UI 및 GPS 연동
# ---------------------------------------------------------
st.title("🚌 동구5번 스마트 안내판")

col_l, col_s = st.columns(2)
with col_l:
    line_choice = st.selectbox("🛤️ 호선 선택", ["자동 (GPS)", "1호선", "2호선", "3호선"])

location = get_geolocation()
target_station = ""
target_line = "1"

if line_choice == "자동 (GPS)":
    if location:
        u_lat, u_lon = location['coords']['latitude'], location['coords']['longitude']
        dists = [{"name": n, "m": int(haversine_distance(u_lat, u_lon, c['lat'], c['lon'])*1000), "line": c['line']} for n, c in STATION_COORDS.items()]
        nearest = sorted(dists, key=lambda x: x['m'])[0]
        target_station, target_line = nearest['name'], nearest['line']
        st.success(f"🛰️ GPS 추천: **{target_station}역**")
    else:
        target_station, target_line = "반야월", "1"
        st.warning("GPS 신호를 기다리는 중...")
else:
    with col_s:
        target_station = st.selectbox("🚉 역 선택", LINE_STATIONS[line_choice])
        target_line = line_choice[0]

# ---------------------------------------------------------
# [4] 결과 출력
# ---------------------------------------------------------
if target_station:
    st.subheader(f"🚅 {target_station}역 실시간 도착 정보")
    c1, c2 = st.columns(2)
    
    # 방향 안내 보정
    up_dest = "설화명곡/문양/칠곡경대" if target_line != "3" else "칠곡경대병원"
    down_dest = "안심/영남대/용지" if target_line != "3" else "용지"

    with c1:
        st.markdown(f"### 🔼 상행 ({up_dest})")
        times = get_dtro_api_data(target_station, target_line, "UP")
        if times:
            for t in times: st.write(f"⏱️ **{t}** 출발")
        else: st.error("⚠️ 운행 정보 없음 (API 응답 지연)")

    with c2:
        st.markdown(f"### 🔽 하행 ({down_dest})")
        times = get_dtro_api_data(target_station, target_line, "DOWN")
        if times:
            for t in times: st.write(f"⏱️ **{t}** 출발")
        else: st.error("⚠️ 운행 정보 없음 (API 응답 지연)")

st.divider()
if st.button('🔄 새로고침'): st.rerun()
