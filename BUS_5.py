# MY_SERVICE_KEY = "6fc222f7a07ce61876bf07b46533721a192b38b26b2ff8aff34d8bdc837f5ba1" 

import streamlit as st
import requests
import holidays
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# ---------------------------------------------------------
# [필수] 본인의 공공데이터포털 버스 인증키를 입력하세요
MY_SERVICE_KEY = "6fc222f7a07ce61876bf07b46533721a192b38b26b2ff8aff34d8bdc837f5ba1" 
# ---------------------------------------------------------

st.set_page_config(page_title="대구 실시간 교통 안내", page_icon="🚇")

def get_now_korea():
    return datetime.utcnow() + timedelta(hours=9)

# 대구교통공사 API 호출 함수
import re  # 정규표현식 추가

def get_dtro_api_data(station_nm, direction):
    now, is_holiday = get_now_korea(), (get_now_korea() in holidays.KR())
    weekday = now.weekday()
    
    if is_holiday or weekday == 6:
        s_type = "SUNDAY"
    elif weekday == 5:
        s_type = "SATURDAY"
    else:
        s_type = "WEEKDAY"
    
    url = f"https://www.dtro.or.kr/open_content_new/ko/OpenApi/stationTime.php?STT_NM={station_nm}&LINE_NO=1&SCHEDULE_METH={direction}&SCHEDULE_TYPE={s_type}"
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10, verify=False)
        res.encoding = 'utf-8'
        
        # 1. BeautifulSoup 대신 정규표현식으로 직접 숫자 데이터 추출
        # <stime_hh>시간</stime_hh> <stime_mm>분</stime_mm> 형태를 모두 찾습니다.
        h_list = re.findall(r'<[sS][tT][iI][mM][eE]_[hH][hH]>(.*?)</', res.text)
        m_list = re.findall(r'<[sS][tT][iI][mM][eE]_[mM][mM]>(.*?)</', res.text)
        
        now_str = now.strftime("%H:%M")
        upcoming = []
        
        # 2. 시간과 분 리스트를 조합
        for h, m in zip(h_list, m_list):
            time_val = f"{h.strip().zfill(2)}:{m.strip().zfill(2)}"
            if time_val >= now_str:
                upcoming.append(time_val)
        
        result = sorted(list(set(upcoming)))
        
        # 만약 데이터가 하나도 없다면 서버 응답 자체를 화면에 찍어서 디버깅 (필요시 주석 해제)
        # st.text(res.text[:500]) 
        
        return result[:5], s_type
    except Exception as e:
        return [], f"연결 에러: {str(e)}"
        
# 버스 데이터 함수 (기존 유지)
def get_bus_data(bsId):
    url = f"http://apis.data.go.kr/6270000/dbmsapi02/getRealtime02?serviceKey={MY_SERVICE_KEY}&bsId={bsId}&_type=json"
    try:
        res = requests.get(url, timeout=5)
        return res.json().get('body', {}).get('items', []) if res.status_code == 200 else []
    except: return []

# --- UI 레이아웃 ---
now_k = get_now_korea()
st.title("🚇 대구 실시간 교통 API")
st.write(f"현재 시각: **{now_k.strftime('%Y-%m-%d %H:%M:%S')}**")

# 지하철 섹션
st.header("🚅 지하철 (DTRO API 실시간)")
col1, col2 = st.columns(2)

with col1:
    st.success("🚉 반야월역 (상행)")
    st.caption("설화명곡 방면")
    # 반야월역 상행은 UP
    times, s_mode = get_dtro_api_data("반야월", "UP")
    st.write(f"기준: `{s_mode}`")
    if times:
        for t in times: st.write(f"⏱️ **{t}** 출발")
    else: st.info("운행 정보 없음")

with col2:
    st.success("🚉 동대구역 (하행)")
    st.caption("안심 방면")
    # 동대구역 하행은 DOWN
    times, s_mode = get_dtro_api_data("동대구", "DOWN")
    st.write(f"기준: `{s_mode}`")
    if times:
        for t in times: st.write(f"⏱️ **{t}** 출발")
    else: st.info("운행 정보 없음")

st.divider()

# 버스 섹션
st.header("🚌 실시간 버스 (동구5)")
for bs in [{'name': '📍 율하고가교1', 'id': '7011061400'}, {'name': '📍 항공교통본부앞', 'id': '7011060900'}]:
    with st.expander(bs['name'], expanded=True):
        items = get_bus_data(bs['id'])
        if items:
            for item in items:
                if '동구5' in str(item.get('routeNo', '')):
                    for info in item.get('arrList', []):
                        st.metric("도착 정보", info.get('arrState'))
                        st.caption(f"현재 위치: {info.get('bsNm')}")
        else: st.write("실시간 정보 없음")

if st.button('🔄 새로고침'):
    st.rerun()


