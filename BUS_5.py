# MY_SERVICE_KEY = "6fc222f7a07ce61876bf07b46533721a192b38b26b2ff8aff34d8bdc837f5ba1" 

import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# [중요] 버스용 인증키는 본인 것을 입력하세요
MY_SERVICE_KEY = "6fc222f7a07ce61876bf07b46533721a192b38b26b2ff8aff34d8bdc837f5ba1"

st.set_page_config(page_title="실시간 대구 교통", page_icon="🚇")

def get_now_korea():
    return datetime.utcnow() + timedelta(hours=9)

# --- 지하철 실시간 정보 (DTRO 서버 직접 조회) ---
def get_subway_realtime(station_code, up_down):
    # station_code: 144(반야월), 135(동대구) | up_down: 1(상행/설화명곡), 2(하행/안심)
    url = f"https://www.dtro.or.kr/open_content_new/ko/OpenApi/stationTime.php?station_code={station_code}&up_down={up_down}"
    try:
        # SSL 인증서를 무시하고 브라우저인 척 접근합니다.
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=5, verify=False)
        res.encoding = 'utf-8'
        
        soup = BeautifulSoup(res.text, 'xml')
        items = soup.find_all('item')
        
        now_str = get_now_korea().strftime("%H:%M")
        upcoming = []
        
        for item in items:
            hh = item.find('stime_hh').text.strip().zfill(2)
            mm = item.find('stime_mm').text.strip().zfill(2)
            time_val = f"{hh}:{mm}"
            if time_val >= now_str:
                upcoming.append(time_val)
        
        return sorted(list(set(upcoming)))[:4] # 다음 열차 4개
    except:
        return []

# --- 버스 실시간 정보 ---
def get_bus_data(bsId):
    url = f"http://apis.data.go.kr/6270000/dbmsapi02/getRealtime02?serviceKey={MY_SERVICE_KEY}&bsId={bsId}&_type=json"
    try:
        res = requests.get(url, timeout=5)
        return res.json().get('body', {}).get('items', [])
    except:
        return []

# --- UI 화면 구성 ---
st.title("🚇 실시간 동구 교통 안내")
st.write(f"현재 시간: **{get_now_korea().strftime('%H:%M:%S')}**")

# [지하철 섹션] - 전광판 데이터
st.header("🚅 실시간 열차 (전광판 기준)")
col1, col2 = st.columns(2)

with col1:
    st.subheader("🚉 반야월 (상행)")
    st.caption("설화명곡 방면")
    sub_ban = get_subway_realtime('144', '1')
    if sub_ban:
        for t in sub_ban:
            st.info(f"**{t}** 출발 예정")
    else: st.write("도착 정보 없음")

with col2:
    st.subheader("🚉 동대구 (하행)")
    st.caption("안심 방면")
    sub_dong = get_subway_realtime('135', '2')
    if sub_dong:
        for t in sub_dong:
            st.success(f"**{t}** 출발 예정")
    else: st.write("도착 정보 없음")

# [버스 섹션]
st.divider()
st.header("🚌 실시간 버스 (동구5)")
bus_list = [{'name': '📍 율하고가교1', 'id': '7011061400'}, {'name': '📍 항공교통본부앞', 'id': '7011060900'}]

for bus in bus_list:
    with st.expander(bus['name'], expanded=True):
        data = get_bus_data(bus['id'])
        if data:
            for item in data:
                if '동구5' in str(item.get('routeNo', '')):
                    for info in item.get('arrList', []):
                        st.metric("도착 정보", info.get('arrState'))
                        st.caption(f"현재 위치: {info.get('bsNm')}")
        else: st.write("실시간 버스 없음")

if st.button('🔄 새로고침'):
    st.rerun()
