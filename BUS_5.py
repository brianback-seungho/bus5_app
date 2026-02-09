import streamlit as st
import requests
import holidays
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from streamlit_js_eval import get_geolocation, set_cookie, get_cookie
import time
import json

# ---------------------------------------------------------
# [1] 설정 및 전 노선 데이터 (RainbowFarm 종목검색기 연계 가능)
# ---------------------------------------------------------
st.set_page_config(page_title="RainbowFarm 종목검색기 - 지하철", page_icon="🚇", layout="wide")

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

def get_now_korea():
    return datetime.utcnow() + timedelta(hours=9)

def time_to_minutes(t_str):
    """ 'HH:MM' 또는 'H:MM' 형식을 분 단위 정수로 변환하여 정확한 비교 보장 """
    try:
        # 시간 문자열에서 숫자만 추출 (예: '08:05' -> 8, 5)
        h, m = map(int, t_str.split(':'))
        return h * 60 + m
    except:
        return 0

# ---------------------------------------------------------
# [2] 로컬 저장 및 세션 관리
# ---------------------------------------------------------
def save_favorites(fav_list):
    try:
        set_cookie("my_fav_stations", json.dumps(fav_list, ensure_ascii=False), 365)
    except: pass

def load_favorites():
    try:
        raw_saved = get_cookie("my_fav_stations")
        if raw_saved and raw_saved != "undefined":
            return json.loads(raw_saved)
    except: return []
    return []

if 'favorites' not in st.session_state:
    st.session_state.favorites = load_favorites()
if 'current_line' not in st.session_state:
    st.session_state.current_line = "자동 (GPS)"
if 'current_station' not in st.session_state:
    st.session_state.current_station = "반야월"

# ---------------------------------------------------------
# [3] API 엔진 (시간 필터링 정밀화)
# ---------------------------------------------------------
def get_dtro_api_data(station_nm, line_no, direction):
    line_key = f"{line_no}호선"
    if TERMINUS_STATIONS[line_key][direction] == station_nm:
        return "TERMINUS"

    now_kst = get_now_korea()
    current_min = now_kst.hour * 60 + now_kst.minute
    
    kr_holidays = holidays.KR(years=now_kst.year)
    weekday = now_kst.weekday()
    
    if now_kst.date() in kr_holidays or weekday == 6:
        s_type = "HOLIDAY"
    elif weekday == 5:
        s_type = "SATURDAY"
    else:
        s_type = "WEEKDAY"
    
    url = "https://www.dtro.or.kr/open_content_new/ko/OpenApi/stationTime.php"
    clean_nm = station_nm.replace("역", "")
    
    for attempt in range(2):
        try:
            session = requests.Session()
            headers = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6)', 'Referer': 'https://www.dtro.or.kr/'}
            first = session.get(url, headers=headers, verify=False, timeout=5)
            sig = re.search(r"sabSignature=([^']+)'", first.text)
            if sig:
                session.cookies.set('sabFingerPrint', '1920,1080', domain='www.dtro.or.kr')
                session.cookies.set('sabSignature', sig.group(1), domain='www.dtro.or.kr')

            test_nm = clean_nm + "역" if attempt == 0 else clean_nm
            params = {'STT_NM': test_nm, 'LINE_NO': line_no, 'SCHEDULE_METH': direction, 'SCHEDULE_TYPE': s_type}
            res = session.get(url, params=params, headers=headers, verify=False, timeout=8)
            res.encoding = 'utf-8'
            
            if "apiDataList" in res.text:
                root = ET.fromstring(res.text)
                schedule_str = root.findtext('.//SCHEDULE')
                if schedule_str and schedule_str != "-":
                    # 중복 제거 및 시간순 정렬
                    all_times = sorted(list(set(re.findall(r'(\d{1,2}:\d{2})', schedule_str))), key=time_to_minutes)
                    # 분 단위 비교로 현재 시간 이후만 필터링
                    valid_times = [t for t in all_times if time_to_minutes(t) >= current_min]
                    return valid_times[:5]
            time.sleep(0.3)
        except: continue
    return []

# ---------------------------------------------------------
# [4] UI 레이아웃 및 동기화
# ---------------------------------------------------------
st.title("🚇 도시철도역 시간표")

# 즐겨찾기 바
if st.session_state.favorites:
    st.write("⭐ **마이 즐겨찾기**")
    f_cols = st.columns(4)
    for i, fav in enumerate(st.session_state.favorites):
        if f_cols[i].button(f"{fav['name']} ({fav['line']}호선)"):
            st.session_state.current_line = f"{fav['line']}호선"
            st.session_state.current_station = fav['name']
            st.rerun()

# 호선 선택 (라디오 버튼)
line_choice = st.radio("🛤️ 호선 선택", ["자동 (GPS)", "1호선", "2호선", "3호선"], key="current_line", horizontal=True)

target_station = ""
target_line = "1"

if line_choice == "자동 (GPS)":
    location = get_geolocation()
    target_station, target_line = "반야월", "1"
else:
    target_line = line_choice[0]
    options = LINE_STATIONS[line_choice]
    try:
        default_idx = options.index(st.session_state.current_station)
    except:
        default_idx = 0
    target_station = st.selectbox("🚉 역 선택", options, index=default_idx, key="current_station")

# 즐겨찾기 추가/해제
if target_station:
    fav_names = [f['name'] for f in st.session_state.favorites]
    if target_station not in fav_names:
        if st.button(f"💛 '{target_station}' 즐겨찾기 추가"):
            if len(st.session_state.favorites) >= 3: st.session_state.favorites.pop(0)
            st.session_state.favorites.append({"name": target_station, "line": target_line})
            save_favorites(st.session_state.favorites)
            st.rerun()
    else:
        if st.button(f"💔 '{target_station}' 즐겨찾기 해제"):
            st.session_state.favorites = [f for f in st.session_state.favorites if f['name'] != target_station]
            save_favorites(st.session_state.favorites)
            st.rerun()

# ---------------------------------------------------------
# [5] 결과 출력 (현재 시각 표기 포함)
# ---------------------------------------------------------
if target_station:
    now_label = get_now_korea().strftime("%H:%M")
    st.divider()
    # 요청하신 대로 도착 정보 문구 옆에 현재 시각 표기
    st.subheader(f"🚅 {target_station}역 도착 정보 (현재 시각 {now_label})")
    
    dest_labels = {"1": ("설화명곡", "하양"), "2": ("문양", "영남대"), "3": ("칠곡경대병원", "용지")}
    up_txt, down_txt = dest_labels[target_line]

    c1, c2 = st.columns(2)
    with c1:
        st.info(f"🔼 상행 ({up_txt} 방면)")
        up = get_dtro_api_data(target_station, target_line, "UP")
        if up == "TERMINUS": st.warning("🏁 상행 종점입니다.")
        elif up: 
            for t in up: st.write(f"⏱️ **{t}** 출발")
        else: st.error("❌ 운행 종료 또는 정보 없음")

    with c2:
        st
