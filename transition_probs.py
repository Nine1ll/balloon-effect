"""
───────────────────
풍선효과 트래킹 대시보드용 상태 전이확률표 (합성 데이터 시뮬레이션).

이 확률은 '실측값'이 아니라 '가정값'입니다.
   차주 단위 실제 전이율(credit→card 등)은 한국크레딧뷰로(KCB)·신용정보원의
   미공개 미시데이터로만 계산 가능하므로, 여기서는
     (1) 공개 집계 통계로 '하강 방향과 상대적 크기'를 보정하고
     (2) 남는 빈칸을 합리적 가정으로 채웠습니다.
   실배포 시 이 표는 내부 CB 데이터에서 실측한 전이행렬로 대체됩니다.
   (실측 방법은 파이프라인 3단계 '전이행렬 집계'와 동일한 계산입니다.)

근거 요약 (자세한 출처는 REFERENCES.md 참조):
   [R1] 카드론 규제 → 현금서비스·리볼빙으로 이동하는 '풍선효과'가
        반복 관측됨 (여신금융협회 리볼빙 잔액 4개월 연속 증가). newspim 2026-08
   [R2] 카드론 감소분의 약 90%를 현금서비스·리볼빙이 메워 카드빚 총액은
        거의 불변 → '더 비싼 빚으로의 대체'. ftoday 2026-07
   [R3] 은행 문턱 넘지 못한 중·저신용 차주가 카드론·리볼빙·보험계약대출 등
        '은행 밖 급전창구'로 이동. fnnews 2026-06
   [R4] 대출잔고↑ 시 연체확률↑, 특히 DTI 상승 시 급증 (KCB 미시자료 연구).
        김원혁·김승현·이윤수(2020), 국제경제연구 26(2).

반영 원칙:
   · 상태는 위험도 순서: mortgage < deposit < credit < card < revolving,
     cleared(상환·이탈)는 흡수 상태.
   · 각 리스트 = [mortgage, deposit, credit, card, revolving, cleared], 합 = 1.0
   · 규제 전(prob_normal): 유지가 지배적, 하강 약함.
   · 규제 후(prob_regulated): 하강 확률↑, 상환(cleared)↓,
     특히 card→revolving 가속([R1][R2] 근거), mortgage→credit 점프↑([R3] 근거).
   · 검산: 두 표 모두 각 줄 합 1.0, 하강확률 총합 규제전 0.30 → 규제후 1.14.
"""

STATES = ["mortgage", "deposit", "credit", "card", "revolving", "cleared"]

# 규제 전: 하강 압력 낮음 (평온기)
prob_normal = {
    #             mort  depo  cred  card  revo  clear
    "mortgage":  [0.88, 0.05, 0.04, 0.00, 0.00, 0.03],
    "deposit":   [0.06, 0.80, 0.07, 0.01, 0.00, 0.06],
    "credit":    [0.00, 0.10, 0.76, 0.05, 0.01, 0.08],
    # card→revolving은 규제 전에도 0이 아님: 급전성 이동은 상시 존재 [R1]
    "card":      [0.00, 0.01, 0.10, 0.72, 0.07, 0.10],
    "revolving": [0.00, 0.00, 0.02, 0.10, 0.80, 0.08],
    "cleared":   [0.00, 0.00, 0.03, 0.00, 0.00, 0.97],  # 흡수 상태
}

# 규제 후: 하강 확률 상승 · 상환 감소 · card→revolving 가속
prob_regulated = {
    #             mort  depo  cred  card  revo  clear
    # 주담대 규제로 막힌 수요가 신용대출·마통으로 점프 [R3]
    "mortgage":  [0.62, 0.06, 0.26, 0.02, 0.00, 0.04],
    "deposit":   [0.03, 0.62, 0.26, 0.04, 0.01, 0.04],
    # credit→card 하강 확대 [R3]
    "credit":    [0.00, 0.05, 0.66, 0.18, 0.05, 0.06],
    # card→revolving 대폭 상승: 카드론 감소분을 리볼빙이 메움 [R1][R2]
    "card":      [0.00, 0.01, 0.05, 0.62, 0.26, 0.06],
    "revolving": [0.00, 0.00, 0.01, 0.06, 0.87, 0.06],
    "cleared":   [0.00, 0.00, 0.04, 0.00, 0.00, 0.96],  # 상환 유입 소폭 감소
}


def validate(table, name=""):
    """각 줄 확률 합이 1.0인지 검산. 어긋나면 AssertionError."""
    for state, probs in table.items():
        total = round(sum(probs), 10)
        assert abs(total - 1.0) < 1e-9, f"[{name}] '{state}' 합={total} ≠ 1.0"
    return True


if __name__ == "__main__":
    validate(prob_normal, "prob_normal")
    validate(prob_regulated, "prob_regulated")
    print("확률표 검산 통과: 모든 줄 합 = 1.0")