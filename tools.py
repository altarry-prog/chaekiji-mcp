# -*- coding: utf-8 -*-
"""표준 도구 6종 — MCP 서버가 노출하는 전부.
에이전트는 이 여섯 함수의 이름과 인자만 알며,
그 뒤의 정보나루·알파스·규정·금고는 커넥터가 처리한다."""
import os, datetime, yaml
from pathlib import Path
import vault, policy
from connectors import naru, alpas_stub as alpas
import json as _json

# 위임장(mandate) 저장소 — 운영: DB. 구독 동의 1회가 만드는 실행 권한의 실체.
_MANDATES = {}
_MSEQ = [0]

ROOT = Path(__file__).resolve().parent
CFG = yaml.safe_load(open(os.environ.get("CHAEKIJI_CONFIG", ROOT/"config"/"bucheon.yaml"), encoding="utf-8"))
MODE = os.environ.get("CHAEKIJI_MODE", "demo")

def search_item(utterance: str, lang: str = "ko"):
    return naru.search(utterance, mode=MODE)

def check_availability(isbn13: str, realtime: bool = True):
    home = CFG["home_library"]
    rt = alpas.holdings_realtime(isbn13)              # 관내: 알파스 실시간(모의)
    ok  = sorted([l for l, s in rt.items() if s == "ok"])
    busy = sorted([l for l, s in rt.items() if s == "busy"])
    res = {"city": CFG["city"], "home_library": home, "home_status": rt.get(home, "none"),
           "available_at": ok, "loaned_at": busy,
           "basis": "관내: 도서관리시스템 실시간(모의)"}
    if not ok:                                        # 관내 전무 → 전국(정보나루, 전일 기준)
        res["nation"] = naru.availability_nation(isbn13, mode=MODE)
    return res

def check_policy(user: str, isbn13: str, pickup: str):
    member = alpas.member_status(vault.resolve(user))     # 토큰은 금고 안에서만 풀린다
    return policy.check(CFG["rules"], member,
                        alpas.on_shelf(pickup, isbn13), pickup)

def request_service(user: str, isbn13: str, from_lib: str, pickup: str,
                    confirmed_by_user: bool = False, mandate_id: str = None,
                    route: str = "ill"):
    """실행 권한은 둘 중 하나 — 그 자리의 확인(confirmed_by_user) 또는 사전 위임(mandate_id)."""
    if mandate_id:
        m = _MANDATES.get(mandate_id)
        if not m or not m["active"]:
            raise PermissionError("유효한 위임(구독)이 없습니다")
        if m["user"] != user:
            raise PermissionError("위임의 이용자가 다릅니다")
        if m["scope"]["free_routes_only"] and route != "ill":
            return {"accepted": False, "skipped": True,
                    "why": "실비 경로는 위임 범위 밖 — 자동 실행하지 않고 수동 확인으로 넘깁니다"}
        if m["used_this_cycle"] >= m["scope"]["max_per_cycle"]:
            return {"accepted": False, "skipped": True,
                    "why": f"이번 주기 한도({m['scope']['max_per_cycle']}권) 소진"}
    elif not confirmed_by_user:
        raise PermissionError("이용자 확인(confirmed_by_user) 없이는 실행하지 않습니다")
    verdict = check_policy(user, isbn13, pickup)          # 어느 경로든 실행 직전 재판정
    if not verdict["allowed"]:
        return {"accepted": False, "why": verdict["checks"]}
    receipt = alpas.create_ill(vault.resolve(user), isbn13, from_lib, pickup)
    if mandate_id:
        _MANDATES[mandate_id]["used_this_cycle"] += 1
        _MANDATES[mandate_id]["ledger"].append(receipt)
    return {"accepted": True, "receipt": receipt,
            "eta_days": CFG["ill_eta_days"], "executed_via": "알파스 커넥터(모의)",
            "authorized_by": ("사전 위임 " + mandate_id) if mandate_id else "이용자 즉시 확인"}

def suggest_items(user: str = None, count: int = 3):
    """[확장 v0.2] 이달의 추천 — 운영: AI 책큐/정보나루 recommandList 커넥터."""
    rec = _json.load(open(ROOT/"fixtures"/"recommend.json", encoding="utf-8"))["monthly"]
    return {"items": rec[:count], "basis": "월간 추천(모의 픽스처)"}

def manage_mandate(user: str, op: str, pickup: str = None):
    """[확장 v0.2] 구독 위임장 관리 — 완전 자동화의 동의 장치.
    create: 범위가 명시된 위임 생성(이 1회가 유일한 사람 확인)
    status/revoke: 조회·즉시 해지."""
    vault.resolve(user)                                   # 토큰 검증
    if op == "create":
        _MSEQ[0] += 1
        mid = f"mnd-{_MSEQ[0]:04d}"
        _MANDATES[mid] = {"user": user, "active": True, "used_this_cycle": 0,
                          "ledger": [],
                          "scope": {"max_per_cycle": CFG["pass"]["max_per_cycle"],
                                     "free_routes_only": CFG["pass"]["free_routes_only"],
                                     "pickup": pickup or CFG["home_library"],
                                     "cancel": "언제든 해지 · 실행 결과는 매회 통지"}}
        return {"mandate_id": mid, **_MANDATES[mid]}
    m = _MANDATES.get(user_mid := next((k for k,v in _MANDATES.items() if v["user"]==user and v["active"]), None))
    if op == "status":
        return {"mandate_id": user_mid, **m} if m else {"active": False}
    if op == "revoke":
        if m: m["active"] = False
        return {"revoked": bool(m)}
    raise ValueError("op은 create/status/revoke")

def find_alternative(isbn13: str, user: str = None):
    import json
    alt = json.load(open(ROOT/"fixtures"/"alternatives.json", encoding="utf-8"))["alternatives"]
    a = alt.get(isbn13, {"audiobook": False, "braille": False})
    return {**a, "basis": "국가서지 대체자료종합목록(모의)",
            "chaeknarae_eligible": bool(a.get("audiobook") or a.get("braille"))}

def notify_user(user: str, event: str, message: str):
    member_id = vault.resolve(user)
    pref = alpas.member_status(member_id).get("notify_pref", "sms")
    ch = pref if pref in CFG["notify_channels"] else CFG["notify_channels"][0]
    return alpas.send_notice(member_id, ch, message)
