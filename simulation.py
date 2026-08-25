"""
simulation.py
─────────────
풍선효과 트래킹 대시보드 · 데이터 시뮬레이션 파트.

이 모듈이 하는 일 (노트북에서 조각조각 만든 것을 하나로 정리):
  1) 상태와 전이확률표 정의 (transition_probs.py에서 가져옴)
  2) next_state()       : 확률표대로 다음 상태 하나 뽑기
  3) simulate_path()    : 한 차주의 여러 달 경로 만들기
  4) build_panel()      : N명을 굴려 long format 패널(borrower_id×month×state) 생성
  5) add_next_state()   : 각 행에 '다음 달 상태' 붙이기 (전이 분석용)
  6) transition_matrix(): 패널에서 전이행렬(비율) 추정

⚠️ 합성 데이터입니다. 확률표 근거는 REFERENCES.md 참조.
   실배포 시 build_panel()을 실제 여신 데이터 로딩으로 교체하면
   transition_matrix()는 코드 변경 없이 그대로 실측 전이행렬을 산출합니다.
"""

import numpy as np
import pandas as pd

from transition_probs import STATES, prob_normal, prob_regulated, validate

# 시작 시 확률표 검산 (합이 1.0이 아니면 여기서 바로 실패)
validate(prob_normal, "prob_normal")
validate(prob_regulated, "prob_regulated")

# 재현성: 실행할 때마다 같은 결과가 나오도록 시드 고정
RNG = np.random.default_rng(seed=20260620)


def next_state(state, regulated=False):
    """현재 상태를 받아 확률표대로 다음 달 상태 하나를 반환."""
    table = prob_regulated if regulated else prob_normal
    return RNG.choice(STATES, p=table[state])


def simulate_path(start_state, reg_month=6, n_months=12):
    """한 차주의 n_months 경로를 반환. reg_month부터 규제 확률표 적용."""
    path = [start_state]
    for month in range(1, n_months):
        prev = path[-1]
        path.append(next_state(prev, regulated=(month >= reg_month)))
    return path


# 시작 상태 분포: 현실성을 위해 안전한 상품에서 시작할 확률을 높게 둠
# (균등 배정하면 시작부터 1/6이 리볼빙이 되어 비현실적)
START_DIST = {
    "mortgage": 0.34, "deposit": 0.30, "credit": 0.22,
    "card": 0.09, "revolving": 0.05, "cleared": 0.00,
}


def _draw_start():
    return RNG.choice(list(START_DIST), p=list(START_DIST.values()))


def build_panel(n_borrowers=6000, reg_month=6, n_months=12):
    """
    N명의 차주를 시뮬레이션해 long format 패널을 반환.
    컬럼: borrower_id, month, state
    실배포 시 이 함수를 실제 데이터 로딩으로 교체.
    """
    rows = []
    for bid in range(n_borrowers):
        start = _draw_start()
        path = simulate_path(start, reg_month, n_months)
        for month, state in enumerate(path):
            rows.append({"borrower_id": bid, "month": month, "state": state})
    return pd.DataFrame(rows)


def add_next_state(panel):
    """각 행에 '다음 달 상태'(state_next)를 붙임. 차주 경계를 지킴."""
    panel = panel.copy()
    panel["state_next"] = panel.groupby("borrower_id")["state"].shift(-1)
    return panel


def transition_matrix(panel, month_from=None, month_to=None, normalize="index"):
    """
    패널에서 전이행렬을 추정.
    month_from/month_to로 출발 달 구간을 필터링(규제 전/후 분리에 사용).
    normalize='index'면 행별 비율(합 1.0), None이면 개수.
    """
    if "state_next" not in panel.columns:
        panel = add_next_state(panel)
    sub = panel
    if month_from is not None:
        sub = sub[sub["month"] >= month_from]
    if month_to is not None:
        sub = sub[sub["month"] < month_to]
    return pd.crosstab(sub["state"], sub["state_next"],
                       normalize=normalize if normalize else False)


def state_counts_by_month(panel):
    """
    월별·상품별 차주 수 (라인차트용 wide 테이블).
    행=month, 열=state, 값=인원.
    """
    counts = pd.crosstab(panel["month"], panel["state"])
    # 상태 순서를 위험도 순으로 고정
    return counts.reindex(columns=STATES)


if __name__ == "__main__":
    panel = build_panel()
    panel = add_next_state(panel)
    print("패널 shape:", panel.shape)
    print("\n[규제 전 전이행렬 · credit 행]")
    print(transition_matrix(panel, month_to=6).round(2).loc["credit"])
    print("\n[규제 후 전이행렬 · card 행]")
    print(transition_matrix(panel, month_from=6).round(2).loc["card"])
    print("\n[월별 상품 분포 head]")
    print(state_counts_by_month(panel).head())