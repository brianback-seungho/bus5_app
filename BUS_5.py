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
# [1] 기본 설정 및 데이터 (좌표 정밀도 상향)
# ---------------------------------------------------------
MY_SERVICE_KEY = "6fc222f7a07ce61876bf07b46533721a192b38b26b2ff8aff34d8bdc837f5ba1" 
st.set_page_config(page_title="동구5번 교통 안내", page_icon="🚌", layout="wide")

# 대구 1호선 주요 역 정밀 좌표 (구글 지도 기준)
STATION_DATA = [
    {"name": "반야월", "lat": 35.871842, "lon": 128.706725},
    {"name": "각산", "lat": 35.868984, "lon": 128.718047},
    {"name": "안심", "lat": 35.875322, "lon": 128.727402},
    {"name": "신기", "lat": 35.870025, "lon": 128.694625},
    {"name": "율하", "lat": 35.867142, "lon": 128.682855},
    {"name": "동대구", "lat": 35.877400, "lon": 128.628500},
    {"name": "반월당", "lat": 35.864800, "lon": 128.593300}
]

# ---------------------------------------------------------
# [2] 핵심 로직 함수
# ---------------------------------------------------------
def get_now_korea():
    return datetime.utcnow() + timedelta(hours=9)

def haversine_distance(lat1, lon1, lat2, lon2):
    """두 지점 사이의 실제 거리 계산 (km)"""
    r = 6371 
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlambda/2)**2
    return 2 * r * np.arcsin(np.sqrt(a))

def get_dtro_api_data(station_nm, direction):
    """대구교통공사 실시간 시간표 API 호출"""
    now = get_now_korea()
    is_holiday = now in holidays.KR()
    weekday = now.weekday()
    s_type = "HOLIDAY" if (is_holiday or weekday == 6) else ("SATURDAY" if weekday == 5 else "WEEKDAY")
    
    session = requests.Session()
    headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.dtro.or.kr/'}
    url = "https://www.dtro.or.kr/open_content_new/ko/OpenApi/stationTime.php"
    
    try:
        # 보안 시그니처 처리
        first = session.get(url, headers=headers, verify=False, timeout=5)
        sig = re.search(r"sabSignature=([^']+)'", first.text)
        if sig:
            session.cookies.set('sabFingerPrint', '1920,1080,www.dtro.or.kr', domain='www.dtro.or.kr')
            session.cookies.set('sabSignature', sig.group(1), domain='www.dtro.or.kr')

        # 역 이름 보정 시도 (역 이름 뒤에 '역' 유무 대응)
        for name_variant in [station_nm, station_nm + "역"]:
            params = {'STT_NM': name_variant, 'LINE_NO': '1', 'SCHEDULE_METH': direction, 'SCHEDULE_TYPE': s_type}
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
    except:
        return [], "연결 오류"

# ---------------------------------------------------------
# [3] 스트림릿 UI 구성
# ---------------------------------------------------------
st.title("🚌 동구5번 스마트 안내판")
now_k = get_now_korea()
st.info(f"📅 현재 시각: **{now_k.strftime('%Y-%m-%d %H:%M:%S')}**")

# GPS 데이터 수신
location = get_geolocation()

if location:
    u_lat = location['coords']['latitude']
    u_lon = location['coords']['longitude']
    u_acc = location['coords']['accuracy']
    
    # 모든 역과의 거리 계산 및 정렬
    dists = []
    for s in STATION_DATA:
        d = haversine_distance(u_lat, u_lon, s['lat'], s['lon'])
        dists.append({"역이름": s['name'], "거리(m)": int(d * 1000)})
    
    df_dist = pd.DataFrame(dists).sort_values(by="거리(m)")
    nearest_station = df_dist.iloc[0]['역이름']
    
    # 상단 결과 출력
    st.success(f"📍 현재 **{nearest_station}역**이 가장 가깝습니다. (오차범위: 약 {int(u_acc)}m)")
    
    # 지하철 시간표 출력 (2열 레이아웃)
    col1, col2 = st.columns(2)
    with col1:
        st.subheader(f"🚅 {nearest_station}역 상행")
        st.caption("설화명곡 방면")
        times, _ = get_dtro_api_data(nearest_station, "UP")
        if times:
            for t in times: st.write(f"⏱️ **{t}** 출발")
        else: st.warning("운행 정보 없음")

    with col2:
        st.subheader(f"🚅 {nearest_station}역 하행")
        st.caption("안심 방면")
        times, _ = get_dtro_api_data(nearest_station, "DOWN")
        if times:
            for t in times: st.write(f"⏱️ **{t}** 출발")
        else: st.warning("운행 정보 없음")

    # [디버깅 영역] 거리 상세 정보
    with st.expander("🔍 내 위치와 역별 거리 상세 확인 (오차 진단)"):
        st.write(f"현재 수신된 좌표: `{u_lat}, {u_lon}`")
        st.table(df_dist)
        st.caption("※ 반야월역과 각산역은 매우 가까우므로 GPS 오차에 따라 결과가 바뀔 수 있습니다.")

else:
    st.warning("🛰️ GPS 신호를 기다리는 중입니다... 스마트폰의 위치 허용 팝업을 확인하세요.")
    st.info("반드시 HTTPS 주소로 접속해야 위치 정보가 작동합니다.")

st.divider()
if st.button('🔄 정보 새로고침'):
    st.rerun()
