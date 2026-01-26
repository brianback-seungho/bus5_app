import requests
import time
from datetime import datetime

def monitor_518_dual():
    url = "http://apis.data.go.kr/6270000/dbmsapi02/getRealtime02"
    # 인증키를 아래 작은따옴표(' ') 사이에 넣어주세요
    key = requests.utils.unquote('6fc222f7a07ce61876bf07b46533721a192b38b26b2ff8aff34d8bdc837f5ba1').strip()

    # 모니터링할 정류소 정보
    stations = [
        {'name': '📍 율하고가교1', 'bsId': '7011061400'},
        {'name': '📍 항공교통본부앞', 'bsId': '7011060900'}
    ]
    
    # 목표 노선: 518번
    #target_route = '518'
    # 수정 (내일 아침 추천)
    target_route = '동구5' 
    # 또는 가장 확실한 ID 방식
    #target_route = '3000505000'

    print(f"\n🚀 [518번] 버스 실시간 듀얼 모니터링을 시작합니다.")
    print(f"종료하려면 Ctrl+C를 누르세요.")

    while True:
        print(f"\n{'='*60}")
        print(f"🕒 현재 시각: {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*60}")

        for st in stations:
            params = {
                'serviceKey': key,
                'bsId': st['bsId'],
                'routeNo': target_route,
                'numOfRows': '10',
                'pageNo': '1',
                '_type': 'json'
            }

            try:
                # API 호출
                response = requests.get(url, params=params, timeout=10)
                
                # 응답이 정상인지 확인
                if response.status_code != 200:
                    print(f"❌ {st['name']}: 서버 응답 오류 (HTTP {response.status_code})")
                    continue
                
                data = response.json()
                items = data.get('body', {}).get('items', [])

                print(f"{st['name']}")
                print("-" * 45)

                found = False
                if items:
                    for item in items:
                        # API에서 반환된 노선번호와 우리가 찾는 번호가 같은지 확인
                        if str(item.get('routeNo')) == target_route:
                            arr_list = item.get('arrList', [])
                            for bus in arr_list:
                                found = True
                                state = bus.get('arrState')  # 예: "5분"
                                pos = bus.get('bsNm')        # 현재 위치
                                print(f"🚍 동구5번 | 도착까지 {state.center(6)} | 현재위치: {pos}")
                
                if not found:
                    print("📭 현재 운행 중인 동구5번 버스가 없습니다.")
                print("-" * 45)

            except Exception as e:
                # 구체적인 에러 내용 출력 (디버깅용)
                print(f"❌ {st['name']} 조회 실패: {str(e)[:50]}...")

        print(f"\n📡 30초 후 데이터를 다시 가져옵니다...")
        time.sleep(30)

if __name__ == "__main__":
    monitor_518_dual()