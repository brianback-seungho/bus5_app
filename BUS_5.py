import streamlit as st
import requests
import holidays
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from streamlit_js_eval import get_geolocation
import pandas as pd
import numpy as np
import time

# ---------------------------------------------------------
# [1] 설정 및 전 노선 데이터 (1호선 하양 연장선 포함)
# ---------------------------------------------------------
st.set_page_config(page_title="도시철도역 시간표", page_icon="🚇", layout="wide")

LINE_STATIONS = {
    "1호선": [
        "설화명곡", "화원", "대곡", "진천", "월배", "상인", "월촌", "송현", "서부정류장", "대명", 
        "안지랑", "현충로", "영대병원", "교대", "명덕", "반월당", "중앙로", "대구역", "칠성시장", 
        "신천", "동대구", "동구청", "아양교", "동촌", "해안", "방촌", "용계", "율하", "신기", 
        "반야월", "각산", "안심", "대구한의대병원", "부호", "하양"  # 하양 연장구간 추가
    ],
    "2호선": [
        "문양", "다사", "대실", "강창", "계명대", "성서산업단지", "이곡", "용산", "죽전", "감삼", 
        "두류", "내당", "반고개", "청라언덕", "반월당", "경대병원", "범어", "수성구청", "만촌", 
        "담티", "연호", "대공원", "고산", "신매", "사월", "정평", "임당", "영남대"
    ],
    "3호선": [
        "칠곡경대병원", "학정", "팔거", "동천", "칠곡운암", "구암", "태전", "매천시장", "매천", 
        "팔달", "공단", "만평", "팔달시장", "원대", "북구청", "달성공원", "서문시장", "청라언덕", 
        "남산", "명덕", "건들바위", "대봉교", "수성시장", "수성구민운동장", "어린이세상", "황금", 
        "수성못", "지산", "범물", "용지"
    ]
}

# GPS 거리 계산용 거점 (하양 방면 추가)
STATION_COORDS = {
    "반야월": {"lat": 35.871842, "lon": 128.706725, "line": "1"},
    "각산": {"lat": 35.868984, "lon": 128.718047, "line": "1"},
    "안심": {"lat": 35.875322, "lon": 128.727402, "line": "1"},
    "하양": {"lat": 35.911000, "lon": 128.818000, "line": "1"},
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
# [2] API 엔진 (재시도 및 보안 우회)
# ---------------------------------------------------------
def get_dtro_api_data(station_nm, line_no, direction):
    now = get_now_korea()
    is_holiday = now in holidays.KR()
    weekday = now.weekday()
    s_type = "HOLIDAY" if (is_holiday or weekday == 6) else ("SATURDAY" if weekday == 5 else "WEEKDAY")
    
    url = "https://www.dtro.or.kr/open_content_new/ko/OpenApi/stationTime.php"
    clean_nm = station_nm.replace("역", "")
    
    for attempt in range(3):
        try:
            session = requests.Session()
            headers = {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
                'Referer': 'https://www.dtro.or.kr/'
            }
            
            first = session.get(url, headers=headers, verify=False, timeout=5)
            sig = re.search(r"sabSignature=([^']+)'", first.text)
            
            if sig:
                session.cookies.set('sabFingerPrint', '1920,1080,www.dtro.or.kr', domain='www.dtro.or.kr')
                session.cookies.set('sabSignature', sig.group(1), domain='www.dtro.or.kr')

            test_nm = clean_nm + "역" if attempt % 2 == 0 else clean_nm
            params = {'STT_NM': test_nm, 'LINE_NO': line_no, 'SCHEDULE_METH': direction, 'SCHEDULE_TYPE': s_type}
            
            res = session.get(url, params=params, headers=headers, verify=False, timeout=8)
            res.encoding = 'utf-8'
            
            if "apiDataList" in res.text:
                root = ET.fromstring(res.text)
                schedule_str = root.findtext('.//SCHEDULE')
                if schedule_str and schedule_str != "-":
                    all_times = re.findall(r'(\d{1,2}:\d{2})', schedule_str)
                    now_str = now.strftime("%H:%M")
                    times = sorted(list(set([t for t in all_times if t >= now_str])))[:5]
                    if times: return times
            time.sleep(0.5)
        except:
            continue
    return []

# ---------------------------------------------------------
# [3] UI 및 GPS 로직
# ---------------------------------------------------------
st.title("🚇 도시철도역 시간표")
st.caption("대구 지하철 1·2·3호선 전 노선 안내 (1호선 하양 연장선 반영)")

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
        st.success(f"📍 GPS 추천: **{target_station}역**")
    else:
        target_station, target_line = "반야월", "1"
        st.warning("🛰️ GPS 수신 대기 중... (기본: 반야월역)")
else:
    target_station = st.selectbox("🚉 역 선택", LINE_STATIONS[line_choice])
    target_line = line_choice[0]

# ---------------------------------------------------------
# [4] 출력부
# ---------------------------------------------------------
if target_station:
    st.divider()
    st.subheader(f"🚅 {target_station}역 도착 정보")
    
    # 하행 종점 명칭 업데이트
    dest_labels = {
        "1": ("설화명곡 방면", "하양 방면"), # 안심에서 하양으로 변경
        "2": ("문양 방면", "영남대 방면"),
        "3": ("칠곡경대병원 방면", "용지 방면")
    }
    up_txt, down_txt = dest_labels[target_line]

    c1, c2 = st.columns(2)
    with c1:
        st.info(f"🔼 상행 ({up_txt})")
        up = get_dtro_api_data(target_station, target_line, "UP")
        if up: 
            for t in up: st.write(f"⏱️ **{t}**")
        else: st.error("❌ 데이터 없음")

    with c2:
        st.info(f"🔽 하행 ({down_txt})")
        down = get_dtro_api_data(target_station, target_line, "DOWN")
        if down: 
            for t in down: st.write(f"⏱️ **{t}**")
        else: st.error("❌ 데이터 없음")

st.divider()
if st.button('🔄 새로고침'): st.rerun()
