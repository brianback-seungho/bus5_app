import streamlit as st
from streamlit_js_eval import get_geolocation
import pandas as pd
import numpy as np

# 1. 정밀 좌표 데이터 (반야월역 1번 출구 vs 각산역 2번 출구 기준)
STATION_DATA = [
    {"name": "반야월", "lat": 35.871842, "lon": 128.706725},
    {"name": "각산", "lat": 35.868984, "lon": 128.718047}
]

def haversine_distance(lat1, lon1, lat2, lon2):
    r = 6371 
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi, dlambda = np.radians(lat2-lat1), np.radians(lon2-lon1)
    a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlambda/2)**2
    return 2 * r * np.arcsin(np.sqrt(a))

st.title("🚌 동구5번 GPS 정밀 진단")

location = get_geolocation()

if location:
    u_lat = location['coords']['latitude']
    u_lon = location['coords']['longitude']
    u_acc = location['coords']['accuracy']
    
    st.error(f"🛰️ 현재 수신된 좌표: 위도 {u_lat} / 경도 {u_lon}")
    st.write(f"🎯 GPS 정확도 오차범위: 약 {int(u_acc)}m")
    
    # 구글 지도 확인 버튼
    map_url = f"https://www.google.com/maps?q={u_lat},{u_lon}"
    st.link_button("📍 내 GPS가 찍고 있는 실제 위치 보기 (클릭)", map_url)
    
    # 거리 계산
    results = []
    for s in STATION_DATA:
        dist = haversine_distance(u_lat, u_lon, s['lat'], s['lon'])
        results.append({"역이름": s['name'], "거리(m)": int(dist * 1000)})
    
    st.table(pd.DataFrame(results))
    
    if results[1]['거리(m)'] > 1000:
        st.warning("⚠️ 각산역이 1,000m(1km) 넘게 측정되고 있습니다. GPS 신호가 부정확할 수 있습니다.")
else:
    st.info("GPS 신호를 기다리는 중입니다...")
