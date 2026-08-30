# 책이지 MCP 참조 서버 (chaekiji-mcp) v0.2

부천시립도서관 상호대차 AI 에이전트 「책이지」의 **표준 도구 계층 참조 구현**입니다.
문체부 공모 원고의 표준 도구 6종 명세를 실제 MCP(Model Context Protocol) 서버로
구현했으며, 적합성 시험 17건을 통과했습니다(검증기록_20260828.txt).

v0.2에서 「책이지 패스」(구독형 완전 자동화)를 위한 확장 도구 2종이 더해졌습니다.
suggest_items(이달의 추천)·manage_mandate(위임장 생성·조회·해지)이며,
request_service는 즉시 확인 대신 mandate_id(사전 위임)로도 실행됩니다.
위임 실행은 위임 범위(월 권수·무료 경로)를 벗어나면 스스로 건너뛰고, 해지 즉시 무효화됩니다 —
완전 자동화와 이용자 통제권을 양립시키는 장치입니다.

## 무엇이 진짜이고 무엇이 모의인가 (정직 고지)

| 구성요소 | 상태 |
|---|---|
| MCP 서버 (stdio JSON-RPC, 핵심 6종+확장 2종) | **진짜** — 표준 클라이언트 연결 가능 |
| 규정 판정 엔진 + 설정(YAML) 분리 | **진짜** — 시험으로 검증 |
| 정보나루 커넥터 | demo: 2026. 8. 18. 실측 픽스처 / live: 실제 API 호출 코드 포함(인증키 필요) |
| 알파스 커넥터 | **모의** — 함수 5개가 곧 벤더 연동 명세 (connectors/alpas_stub.py 주석 참조) |
| 회원 데이터 | 가상 인물(김○자) 모의 데이터 |

## 구조

    server.py                 MCP 서버 (전송·도구 노출)
    tools.py                  표준 도구 6종 구현
    policy.py                 규정 판정 엔진 (숫자 없음 — 전부 설정에서)
    vault.py                  토큰 금고 (회원 식별자 비노출)
    config/bucheon.yaml       부천의 모든 지역 고유값
    config/example-city.yaml  가상 도시 — 확산 = 이 파일을 새로 쓰는 일
    connectors/naru.py        정보나루 커넥터 (demo/live 동일 응답 모양)
    connectors/alpas_stub.py  알파스 커넥터 모의 = 벤더 연동 명세
    fixtures/                 실측 소장 64건 · 서지 · 모의 회원
    tests/run_scenarios.py    적합성 시험 킷 (17건)

## 실행

적합성 시험:

    python3 tests/run_scenarios.py

클로드 데스크톱에 연결 (claude_desktop_config.example.json 참조):
설정 파일에 서버 등록 후 재시작 → 대화창에서
"나미야 잡화점 부천에서 빌릴 수 있어? 토큰은 tok_kimsj, 상동 수령"
→ 도구 호출이 실제로 일어나는 것을 확인할 수 있습니다.

실계(live) 모드 — 이용자 PC에서:

    NARU_KEY=발급받은키 CHAEKIJI_MODE=live python3 server.py

다른 도시 설정으로:

    CHAEKIJI_CONFIG=config/example-city.yaml python3 server.py

## 확산 절차 (이 저장소가 주장하는 바)

1. 도서관 코드표·규정 숫자를 담은 `config/<도시>.yaml` 작성 — 반나절
2. 도서관리시스템이 알파스면: `alpas_stub.py`의 함수 5개를 벤더 API로 채운 커넥터 재사용
3. 다른 시스템이면: 같은 함수 5개짜리 커넥터 1회 개발 → 전국 공유
4. `tests/run_scenarios.py` 통과 = 책이지 에이전트와 호환 보장

의존성: Python 3.9+ · PyYAML. 외부 패키지·네트워크 없이 demo 모드 전체 동작.
라이선스: MIT (LICENSE 파일 포함) · 2026. 8. 부천시립도서관 상동도서관
