# -*- coding: utf-8 -*-
"""알파스 커넥터 — 실행 계층 (모의 구현).
이 파일의 함수 목록이 곧 벤더에게 요청할 연동 명세다:
아래 다섯 함수를 실제 알파스 API/DB 호출로 바꾸면 커넥터가 완성되고,
같은 시스템을 쓰는 전국 도서관이 그 커넥터를 재사용한다.
모의 데이터는 fixtures/에 있으며 상태 변화(신청·알림)는 메모리에만 기록된다."""
import json, datetime
from pathlib import Path

FIX = Path(__file__).resolve().parent.parent / "fixtures"
_hold = json.load(open(FIX/"holdings.json", encoding="utf-8"))["holdings"]
_members = json.load(open(FIX/"members.json", encoding="utf-8"))["members"]
_requests, _outbox = [], []          # 운영: 알파스 DB 트랜잭션 / 알림 게이트웨이

def member_status(member_id: str) -> dict:            # [벤더 구현 ①] 회원 대출 현황
    m = _members.get(member_id)
    if not m: raise KeyError("회원 없음")
    return m

def holdings_realtime(isbn13: str) -> dict:           # [벤더 구현 ②] 관내 실시간 재고
    h = _hold.get(isbn13)
    if h is None: return {}
    return dict(h)                                    # ok=서가에 있음, busy=대출중, none=미소장

def on_shelf(lib: str, isbn13: str) -> bool:          # [벤더 구현 ③] 특정관 서가 비치 여부
    return _hold.get(isbn13, {}).get(lib) == "ok"

def create_ill(member_id, isbn13, from_lib, pickup):  # [벤더 구현 ④] 상호대차 신청 생성
    no = f"ILL-{datetime.date.today():%Y%m%d}-{len(_requests)+1:04d}"
    _requests.append({"no": no, "member": member_id, "isbn13": isbn13,
                      "from": from_lib, "pickup": pickup})
    _members[member_id]["ill_count"] += 1             # 한도 즉시 반영
    return no

def send_notice(member_id, channel, message):         # [벤더 구현 ⑤] 알림 발송
    _outbox.append({"member": member_id, "channel": channel, "message": message})
    return {"queued": True, "channel": channel}
