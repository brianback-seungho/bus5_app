import streamlit as st
import requests
import holidays
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from streamlit_js_eval import get_geolocation, set_cookie, get_cookie
import pandas as pd
import numpy as np
import time
import json

# ---------------------------------------------------------
# [1] 설정 및 전 노선 데이터
# ---------------------------------------------------------
st.set_page_config(page_title="도시철도역 시간표", page_icon="🚇", layout="wide")

# 로컬 스토리지 대용으로 쿠키/JS 저장소 활용 (streamlit-js-eval 사용)
def save_favorites(fav_list):
    # 리스트를 JSON 문자열로 변환하여 저장
    set_cookie("my_fav_stations", json.dumps(fav_list), days_followed=365)

def load_favorites():
    raw_saved = get_cookie("my_fav_stations")
    if raw_saved:
        try:
            return json.loads(raw_saved)
        except:
            return []
    return []

# 초기 로드
if 'favorites' not in st.session_state:
    st.session_state.favorites = load_favorites()

LINE_STATIONS = {
    "1호선": ["설화명곡", "화원", "대곡", "진천", "월배", "상인", "월촌", "송현", "서부정류장", "대명", "안지랑", "현충로", "영대병원", "교대", "명덕", "반월당", "중앙로", "대구역", "칠성시장", "신천", "동대구", "동구청", "아양교", "동촌", "해안", "방촌", "용계", "율하", "신기", "반야월", "각산", "안심", "대구한의대병원", "부호", "하양"],
    "2호선": ["문양", "다사", "대실", "강창", "계명대", "성서산업단지", "이곡", "용산", "죽전", "감삼", "두류", "내당", "반고개", "청라언덕", "반월당", "경대병원", "범어", "수성구청", "만촌", "담티", "연호", "대공원", "고산", "신매", "사월", "정평", "임당", "영남대"],
    "3호선": ["칠곡경대병원", "학정", "팔거", "동천", "칠곡운암", "구암", "태전", "매천시장", "매천", "팔달", "공단", "만평", "팔달시장", "원대", "북구청", "달성공원", "서문시장", "청라언덕", "남산", "명덕", "건들바위", "대봉교", "수성시장", "수성구민운동장", "어린이세상", "황금", "수성못", "지산", "범물", "용지"]
}

TERMINUS_STATIONS = {
    "1호선": {"UP": "설화명곡", "DOWN": "하양"},
    "2호선": {"UP": "문양", "DOWN": "영남대"},
    "3호선": {"UP": "칠곡경대병원", "DOWN": "용지"}
}

STATION_COORDS = {
    "반야월": {"lat": 35.871842, "lon": 128.706725, "line": "1"},
    "각산": {"lat": 35.868984, "lon": 128.718047, "line": "1"},
    "동대구": {"lat": 35.877400, "lon": 128.628500, "line": "1"}
}

def get_now_korea():
    return datetime.utcnow() + timedelta(hours=9)

# ---------------------------------------------------------
# [2] API 엔진
# ---------------------------------------------------------
def get_dtro_api_data(station_nm, line_no, direction):
    line_key = f"{line_no}호선"
    if TERMINUS_STATIONS[line_key][direction] == station_nm:
        return "TERMINUS"

    url = "https://www.dtro.or.kr/open_content_new/ko/OpenApi/stationTime.php"
    clean_nm = station_nm.replace("역", "")
    now = get_now_korea()
    is_holiday = now in holidays.KR()
    weekday = now.weekday()
    s_type = "HOLIDAY" if (is_holiday or weekday == 6) else ("SATURDAY" if weekday == 5 else "WEEKDAY")
    
    try:
        session = requests.Session()
        headers = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6)', 'Referer': 'https://www.dtro.or.kr/'}
        first = session.get(url, headers=headers, verify=False, timeout=5)
        sig = re.search(r"sabSignature=([^']+)'", first.text)
        if sig:
            session.cookies.set('sabFingerPrint', '1920,1080', domain='www.dtro.or.kr')
            session.cookies.set('sabSignature', sig.group(1), domain='www.dtro.or.kr')

        params = {'STT_NM': clean_nm+"역", 'LINE_NO': line_no, 'SCHEDULE_METH': direction, 'SCHEDULE_TYPE': s_type}
        res = session.get(url, params=params, headers=headers, verify=False, timeout=8)
        res.encoding = 'utf-8'
        
        if "apiDataList" in res.text:
            root = ET.fromstring(res.text)
            schedule_str = root.findtext('.//SCHEDULE')
            if schedule_str and schedule_str != "-":
                all_times = re.findall(r'(\d{1,2}:\d{2})', schedule_str)
                now_str = now.strftime("%H:%M")
                return sorted(list(set([t for t in all_times if t >= now_str])))[:5]
    except: pass
    return []

# ---------------------------------------------------------
# [3] UI 및 즐겨찾기 로컬 저장 로직
# ---------------------------------------------------------
st.title("🚇 도시철도역 시간표")

# 상단 즐겨찾기 바 (로컬 데이터 연동)
if st.session_state.favorites:
    st.write("⭐ **마이 즐겨찾기** (브라우저에 저장됨)")
    cols = st.columns(4)
    for idx, fav in enumerate(st.session_state.favorites):
        if cols[idx].button(f"{fav['name']} ({fav['line']}호선)"):
            st.session_state.manual_station = fav['name']
            st.session_state.manual_line = f"{fav['line']}호선"

line_choice = st.radio("🛤️ 호선 선택", ["자동 (GPS)", "1호선", "2호선", "3호선"], horizontal=True)

target_station = ""
target_line = "1"

if line_choice == "자동 (GPS)":
    location = get_geolocation()
    if location:
        u_lat, u_lon = location['coords']['latitude'], location['coords']['longitude']
        # 하버사인 계산 (생략...)
        target_station, target_line = "반야월", "1" 
    else:
        target_station, target_line = "반야월", "1"
else:
    target_line = line_choice[0]
    # 즐겨찾기 클릭 시 상태 동기화
    default_idx = 0
    if 'manual_station' in st.session_state and st.session_state.manual_station in LINE_STATIONS[line_choice]:
        default_idx = LINE_STATIONS[line_choice].index(st.session_state.manual_station)
    
    target_station = st.selectbox("🚉 역 선택", LINE_STATIONS[line_choice], index=default_idx)

# 즐겨찾기 저장/삭제 버튼 (로컬 스토리지 연동)
if target_station:
    fav_names = [f['name'] for f in st.session_state.favorites]
    c_fav1, c_fav2 = st.columns([1, 5])
    
    if target_station not in fav_names:
        if st.button(f"💛 '{target_station}' 즐겨찾기 추가"):
            if len(st.session_state.favorites) >= 3:
                st.session_state.favorites.pop(0)
            st.session_state.favorites.append({"name": target_station, "line": target_line})
            save_favorites(st.session_state.favorites) # 로컬에 저장
            st.rerun()
    else:
        if st.button(f"💔 '{target_station}' 즐겨찾기 해제"):
            st.session_state.favorites = [f for f in st.session_state.favorites if f['name'] != target_station]
            save_favorites(st.session_state.favorites) # 로컬에 반영
            st.rerun()

# ---------------------------------------------------------
# [4] 결과 출력
# ---------------------------------------------------------
if target_station:
    st.divider()
    st.subheader(f"🚅 {target_station}역 시간표")
    
    dest_labels = {"1": ("설화명곡", "하양"), "2": ("문양", "영남대"), "3": ("칠곡경대병원", "용지")}
    up_txt, down_txt = dest_labels[target_line]

    c1, c2 = st.columns(2)
    with c1:
        st.info(f"🔼 상행 ({up_txt})")
        up = get_dtro_api_data(target_station, target_line, "UP")
        if up == "TERMINUS": st.warning("🏁 종점역입니다.")
        elif up: 
            for t in up: st.write(f"⏱️ **{t}**")
        else: st.error("❌ 데이터 없음")

    with c2:
        st.info(f"🔽 하행 ({down_txt})")
        down = get_dtro_api_data(target_station, target_line, "DOWN")
        if down == "TERMINUS": st.warning("🏁 종점역입니다.")
        elif down: 
            for t in down: st.write(f"⏱️ **{t}**")
        else: st.error("❌ 데이터 없음")

st.divider()
if st.button('🔄 새로고침'): st.rerun()
