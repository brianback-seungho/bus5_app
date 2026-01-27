import streamlit as st
import requests
from datetime import datetime

st.set_page_config(page_title="버스 출도착 전광판", page_icon="🚌")

# [주의] 인증키를 꼭 확인하세요!
SERVICE_KEY = "6fc222f7a07ce61876bf07b46533721a192b38b26b2ff8aff34d8bdc837f5ba1".strip()

stations = [
    {'name': '📍 율하고가교1', 'bsId': '7011061400'},
    {'name': '📍 항공교통본부앞', 'bsId': '7011060900'}
]

def get_bus_data(bsId):
    url = "http://apis.data.go.kr/6270000/dbmsapi02/getRealtime02"
    params = {
        'serviceKey': requests.utils.unquote(SERVICE_KEY).strip(),
        'bsId': bsId,
        'numOfRows': '30',
        'pageNo': '1',
        '_type': 'json'
    }
    try:
        res = requests.get(url, params=params, timeout=5)
        # 로그 확인용: 데이터가 오는지 체크
        data = res.json()
        return data.get('body', {}).get('items', [])
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return []

st.title("🚌 전광판 테스트 모드")
st.write(f"현재 시각: {datetime.now().strftime('%H:%M:%S')}")

if st.button('🔄 새로고침'):
    st.rerun()

for st_info in stations:
    st.subheader(st_info['name'])
    items = get_bus_data(st_info['bsId'])
    
    if items:
        for item in items:
            # 필터링 없이 일단 다 보여주기!
            route_no = item.get('routeNo')
            arr_list = item.get('arrList', [])
            for bus in arr_list:
                st.write(f"✅ **{route_no}번** | {bus.get('arrState')} | {bus.get('bsNm')}")
    else:
        st.write("📭 이 정류소는 현재 검색되는 버스가 없습니다.")
    st.divider()


