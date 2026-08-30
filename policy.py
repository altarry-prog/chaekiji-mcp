# -*- coding: utf-8 -*-
"""규정 판정 엔진 — 숫자는 전부 설정(YAML)에서 온다. 코드에 지역 규정이 없다."""

def check(rules: dict, member: dict, pickup_on_shelf: bool, pickup: str):
    checks = []
    def rule(name, passed, detail):
        checks.append({"rule": name, "pass": bool(passed), "detail": detail})
    if rules.get("block_if_pickup_on_shelf", True):
        rule("수령관 동일도서 비치 시 신청 불가", not pickup_on_shelf,
             "수령관 서가에 비치 중" if pickup_on_shelf else "수령관 소장본 서가에 없음(대출중 또는 미소장)")
    rule(f"상호대차 1인 {rules['ill_limit']}권",
         member["ill_count"] < rules["ill_limit"], f"현재 {member['ill_count']}/{rules['ill_limit']}권")
    rule(f"통합 대출 {rules['total_limit']}권",
         member["total_loans"] < rules["total_limit"], f"현재 {member['total_loans']}/{rules['total_limit']}권")
    at = member.get("loans_at", {}).get(pickup, 0)
    rule(f"도서관별 {rules['per_lib_limit']}권(직접+상호대차)",
         at < rules["per_lib_limit"], f"{pickup} 현재 {at}/{rules['per_lib_limit']}권")
    return {"allowed": all(c["pass"] for c in checks), "checks": checks}
