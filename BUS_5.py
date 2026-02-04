# MY_SERVICE_KEY = "6fc222f7a07ce61876bf07b46533721a192b38b26b2ff8aff34d8bdc837f5ba1" 

import streamlit as st
import requests
import holidays
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

# ---------------------------------------------------------
# [필수] 본인의 공공데이터포털 버스 인증키를 입력하세요
MY_SERVICE_KEY = "6fc222f7a07ce61876bf07b46533721a192b38b26b2ff8aff34d8bdc837f5ba1" 
# ---------------------------------------------------------

st.set_page_config(page_title="대구 실시간 교통 안내", page_icon="🚇", layout="wide")

# 지하철 데이터 함수
def get_now_korea():
    # UTC 기준 현재 시간에 9시간을 더해 한국 시간 생성
    return datetime.utcnow() + timedelta(hours=9)

def get_dtro_api_data(station_nm, direction):
    now = get_now_korea()
    is_holiday = now in holidays.KR()
    weekday = now.weekday()
    
    # 요일 타입 결정 (문자열 방식)
    if is_holiday or weekday == 6:
        s_type = "HOLIDAY"
    elif weekday == 5:
        s_type = "SATURDAY"
    else:
        s_type = "WEEKDAY"
    
    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.dtro.or.kr/'
    }
    
    url = "https://www.dtro.or.kr/open_content_new/ko/OpenApi/stationTime.php"
    
    try:
        # 1. 시그니처 자동 추출 (보안 통과)
        first_res = session.get(url, headers=headers, verify=False, timeout=5)
        sig_match = re.search(r"sabSignature=([^']+)'", first_res.text)
        if sig_match:
            session.cookies.set('sabFingerPrint', '1920,1080,www.dtro.or.kr', domain='www.dtro.or.kr')
            session.cookies.set('sabSignature', sig_match.group(1), domain='www.dtro.or.kr')

        # 2. 데이터 요청 (역 이름 '역' 유무 2번 시도)
        test_names = [station_nm, station_nm + "역"] if not station_nm.endswith("역") else [station_nm, station_nm[:-1]]
        
        final_schedule = "-"
        for name in test_names:
            params = {
                'STT_NM': name,
                'LINE_NO': '1',
                'SCHEDULE_METH': direction, # UP/DOWN
                'SCHEDULE_TYPE': s_type
            }
            res = session.get(url, params=params, headers=headers, verify=False, timeout=10)
            res.encoding = 'utf-8'
            
            # 데이터 확인 (SCHEDULE이 "-"이 아니면 성공)
            if "apiDataList" in res.text:
                root = ET.fromstring(res.text)
                schedule_str = root.findtext('.//SCHEDULE')
                if schedule_str and schedule_str != "-":
                    final_schedule = schedule_str
                    break
        
        # 3. 시간 추출 및 필터링
        if final_schedule != "-":
            all_times = re.findall(r'(\d{1,2}:\d{2})', final_schedule)
            now_str = now.strftime("%H:%M")
            upcoming = sorted(list(set([t for t in all_times if t >= now_str])))
            return upcoming[:5], s_type
            
        return [], s_type
            
    except Exception as e:
        return [], f"에러: {str(e)}"
        
# 버스 데이터 함수 (기존 유지)
def get_bus_data(bsId):
    url = f"http://apis.data.go.kr/6270000/dbmsapi02/getRealtime02?serviceKey={MY_SERVICE_KEY}&bsId={bsId}&_type=json"
    try:
        res = requests.get(url, timeout=5)
        return res.json().get('body', {}).get('items', []) if res.status_code == 200 else []
    except: return []

# --- UI 레이아웃 ---
now_k = get_now_korea()
st.title("🚇 대구 실시간 교통 안내 (동구5 연계)")
st.info(f"📅 현재 시각: **{now_k.strftime('%Y-%m-%d %H:%M:%S')}**")

# 지하철 섹션
st.subheader("🚅 지하철 실시간 도착 (반야월/동대구)")
col1, col2 = st.columns(2)

with col1:
    st.success("🚉 반야월역 (상행)")
    st.caption("설화명곡 방면")
    times, s_mode = get_dtro_api_data("반야월", "UP")
    st.markdown(f"**요일 기준:** `{s_mode}`")
    if isinstance(times, list) and times:
        for t in times:
            st.write(f"⏱️ **{t}** 출발")
    else:
        st.warning("운행 정보 없음")

with col2:
    st.success("🚉 동대구역 (하행)")
    st.caption("안심 방면")
    times, s_mode = get_dtro_api_data("동대구역", "DOWN")
    st.markdown(f"**요일 기준:** `{s_mode}`")
    if isinstance(times, list) and times:
        for t in times:
            st.write(f"⏱️ **{t}** 출발")
    else:
        st.warning("운행 정보 없음")

st.divider()

# 버스 섹션
st.subheader("🚌 실시간 버스 (동구5)")
bus_stops = [
    {'name': '📍 율하고가교1', 'id': '7011061400'},
    {'name': '📍 항공교통본부앞', 'id': '7011060900'}
]

cols = st.columns(len(bus_stops))
for idx, bs in enumerate(bus_stops):
    with cols[idx]:
        st.info(bs['name'])
        items = get_bus_data(bs['id'])
        found = False
        if items:
            for item in items:
                if '동구5' in str(item.get('routeNo', '')):
                    for info in item.get('arrList', []):
                        st.metric("도착 예정", info.get('arrState'))
                        st.caption(f"🚌 현재 위치: {info.get('bsNm')}")
                        found = True
        if not found:
            st.write("실시간 정보 없음")

if st.button('🔄 정보 새로고침'):
    st.rerun()






