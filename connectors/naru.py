# -*- coding: utf-8 -*-
"""정보나루 커넥터 — 조회 계층.
demo 모드: 2026. 8. 18. 실측 픽스처로 응답 (네트워크 없음).
live 모드: 실제 Open API 호출 (NARU_KEY 환경변수 필요, 이용자 PC에서 실행).
어느 모드든 응답 모양은 같다 — 이것이 커넥터의 요점."""
import json, os, datetime, urllib.parse, urllib.request
from pathlib import Path

FIX = Path(__file__).resolve().parent.parent / "fixtures"
_cat = json.load(open(FIX/"catalog.json", encoding="utf-8"))
_hold = json.load(open(FIX/"holdings.json", encoding="utf-8"))

def _norm(s): return "".join(s.split()).lower()

def search(utterance: str, mode="demo"):
    if mode == "live":
        return _live_search(utterance)
    q = _norm(utterance)
    best = None
    for b in _cat["books"]:
        score = max((len(_norm(k)) for k in b["keys"] if _norm(k) in q), default=0)
        if score and (best is None or score > best[0]):
            best = (score, b)
    if not best:
        return {"found": False, "reason": "픽스처에 없는 도서(모의 모드 한계) — live 모드에서는 전국 서지 검색"}
    b = best[1]
    return {"found": True, "isbn13": b["isbn13"], "title": b["title"], "author": b["author"],
            "publisher": b["publisher"], "year": b["year"],
            "confidence": 0.97, "evidence": "정보나루 srchBooks(모의 픽스처 · 실측 서지)"}

def availability_nation(isbn13: str, mode="demo"):
    yday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    if mode == "live":
        return _live_nation(isbn13)
    n = _hold.get("nation", {}).get(isbn13)
    return {"basis": f"전일({yday}) 기준 · 정보나루", "found_count": (n or {}).get("count", 0),
            "note": (n or {}).get("note", "전국 조회(모의)")}

# ── live 모드 (이 샌드박스에서는 호출하지 않음 — 이용자 환경에서 동작) ──
def _key():
    k = os.environ.get("NARU_KEY")
    if not k: raise RuntimeError("live 모드에는 NARU_KEY 환경변수(정보나루 인증키)가 필요합니다")
    return k

def _get(url):
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.load(r)

def _live_search(utterance):
    u = ("https://data4library.kr/api/srchBooks?authKey=" + _key()
         + "&title=" + urllib.parse.quote(utterance) + "&exactMatch=Y&format=json&pageSize=3")
    docs = _get(u).get("response", {}).get("docs", [])
    if not docs: return {"found": False, "reason": "일치 결과 없음"}
    d = docs[0]["doc"]
    return {"found": True, "isbn13": d["isbn13"], "title": d["bookname"], "author": d["authors"],
            "publisher": d["publisher"], "year": d["publication_year"],
            "confidence": 0.9, "evidence": "정보나루 srchBooks(exactMatch, live)"}

def _live_nation(isbn13):
    u = ("https://data4library.kr/api/libSrchByBook?authKey=" + _key()
         + "&isbn=" + isbn13 + "&region=31&format=json&pageSize=200")
    libs = _get(u).get("response", {}).get("libs", [])
    return {"basis": "전일 기준 · 정보나루(live)", "found_count": len(libs), "note": "경기 광역 예시"}
