"""
app.py — 풍선효과 트래킹 대시보드 (Streamlit)

주담대 규제로 눌린 자금이 신용대출·마통을 거쳐 카드론·리볼빙으로 이동하는
'풍선효과'를 차주 단위 전이로 추적한다. (합성 데이터 시뮬레이션)

실행:  streamlit run app.py
필요 패키지: streamlit plotly pandas numpy matplotlib
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from simulation import build_panel, add_next_state, state_counts_by_month, STATES

# ── 페이지 설정 ────────────────────────────────────────
st.set_page_config(page_title="풍선효과 트래킹", layout="wide",
                   initial_sidebar_state="collapsed")

INK, INK_DIM, PANEL = "#e6edf7", "#8ea3c0", "#0e1727"
COOL, MID, WARN, HOT, EXIT = "#3fb4c4", "#e0a13a", "#e8743b", "#e5484d", "#4a9d6b"

KOR = {"mortgage":"주담대", "deposit":"예금은행", "credit":"신용대출·마통",
       "card":"카드론", "revolving":"리볼빙", "cleared":"상환·이탈"}
NODE_COLOR = {"mortgage":COOL, "deposit":COOL, "credit":MID,
              "card":WARN, "revolving":HOT, "cleared":EXIT}
RISK = {s: i for i, s in enumerate(STATES)}

st.markdown(f"""
<style>
  .stApp {{ background: radial-gradient(1200px 600px at 78% -10%, #14233c 0%, transparent 60%), #0a1120; }}
  [data-testid="stMetric"] {{
     background: linear-gradient(180deg,#111c30,#0e1828);
     border:1px solid #22344f; border-radius:14px; padding:14px 16px;
  }}
  [data-testid="stMetricLabel"] p {{ color:{INK_DIM} !important; font-weight:600; }}
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_panel(n_borrowers=6000, reg_month=6):
    panel = add_next_state(build_panel(n_borrowers=n_borrowers, reg_month=reg_month))
    counts = state_counts_by_month(panel)
    return panel, counts


REG_MONTH = 6
panel, counts = load_panel(reg_month=REG_MONTH)

st.markdown(f"""
<div style="border-bottom:1px solid #22344f;padding-bottom:14px;margin-bottom:6px">
  <div style="font-size:12px;letter-spacing:.28em;color:{INK_DIM};
              text-transform:uppercase;font-weight:600">
    여신 포트폴리오 · 업권 이동 모니터</div>
  <div style="font-size:30px;font-weight:800;color:{INK};letter-spacing:-.02em">
    풍선효과 <span style="color:{WARN}">트래킹</span> 대시보드</div>
  <div style="font-size:13px;color:{INK_DIM};margin-top:4px">
    규제로 눌린 자금이 신용대출·마통을 거쳐 카드론·리볼빙으로 이동하는
    <b>차주 단위 전이</b>를 추적합니다. · <span style="color:{MID}">합성 데이터</span></div>
</div>
""", unsafe_allow_html=True)

selected_month = st.slider("관측 시점 (월)", 0, 11, REG_MONTH,
    help="라인차트의 주황 선과 산키가 이 달을 가리킵니다. 회색 점선(규제 강화)은 6월 고정입니다.")

this_month = counts.loc[selected_month]
prev_month = counts.loc[max(0, selected_month - 1)]


def downward_rate(panel, month):
    md = panel[panel["month"] == month].dropna(subset=["state_next"])
    if len(md) == 0:
        return None
    down = md.apply(lambda r: RISK.get(r["state_next"], -1) > RISK[r["state"]]
                    and r["state_next"] != "cleared", axis=1).sum()
    return down / len(md)


def make_line(counts, selected_month):
    fig = px.line(counts.rename(columns=KOR),
                  labels={"month":"월", "value":"차주 수", "variable":"상품"},
                  color_discrete_map={KOR[s]: NODE_COLOR[s] for s in STATES})
    fig.add_vline(x=REG_MONTH, line_dash="dash", line_color=INK_DIM, line_width=1.5,
                  annotation_text="규제 강화", annotation_font_color=INK_DIM)
    fig.add_vline(x=selected_month, line_dash="solid", line_color=WARN, line_width=2.5,
                  annotation_text="관측 시점", annotation_font_color=WARN,
                  annotation_position="top left")
    fig.update_layout(plot_bgcolor=PANEL, paper_bgcolor=PANEL, font_color=INK,
                      title="상품별 차주 수 추이", height=420,
                      margin=dict(t=46, l=8, r=8, b=8),
                      legend=dict(orientation="h", y=-0.2, title=""))
    fig.update_xaxes(gridcolor="#1b2a44"); fig.update_yaxes(gridcolor="#1b2a44")
    return fig


def make_sankey(panel, selected_month):
    md = panel[panel["month"] == selected_month]
    trans = pd.crosstab(md["state"], md["state_next"])
    n = len(STATES)
    idx = {s: i for i, s in enumerate(STATES)}
    labels = [KOR[s] for s in STATES] * 2
    node_colors = [NODE_COLOR[s] for s in STATES] * 2
    source, target, value, link_color, cdata = [], [], [], [], []
    for f in trans.index:
        for t in trans.columns:
            v = trans.loc[f, t]
            if v <= 0:
                continue
            source.append(idx[f]); target.append(idx[t] + n); value.append(int(v))
            if t == "cleared":      c, tag = "rgba(74,157,107,0.5)",  "상환·개선"
            elif f == "cleared":    c, tag = "rgba(90,112,147,0.25)", "상환 상태"
            elif RISK[t] > RISK[f]: c, tag = "rgba(229,72,77,0.55)",  "위험 하강"
            elif RISK[t] < RISK[f]: c, tag = "rgba(63,180,196,0.4)",  "개선"
            else:                   c, tag = "rgba(120,140,170,0.22)","유지"
            link_color.append(c); cdata.append(f"{KOR[f]} → {KOR[t]} · {tag}")
    fig = go.Figure(go.Sankey(
        node=dict(label=labels, color=node_colors, pad=18, thickness=16,
                  line=dict(width=0),
                  hovertemplate="%{label}: %{value}명<extra></extra>"),
        link=dict(source=source, target=target, value=value, color=link_color,
                  customdata=cdata,
                  hovertemplate="%{customdata}<br>%{value}명<extra></extra>")))
    fig.update_layout(title=f"{selected_month}월 → {selected_month+1}월 자금 이동",
                      font_color=INK, paper_bgcolor=PANEL, height=420,
                      margin=dict(t=46, l=8, r=8, b=8))
    return fig


def make_matrix(md):
    pct = pd.crosstab(md["state"], md["state_next"], normalize="index")
    pct.index = [KOR[s] for s in pct.index]
    pct.columns = [KOR[s] for s in pct.columns]
    return pct.style.background_gradient(cmap="magma", vmin=0, vmax=0.5).format("{:.0%}")


def get_alerts(md, top=4):
    cnt = pd.crosstab(md["state"], md["state_next"])
    out = []
    for f in cnt.index:
        rt = cnt.loc[f].sum()
        for t in cnt.columns:
            v = cnt.loc[f, t]
            if RISK.get(t, -1) > RISK[f] and t != "cleared" and v > 0:
                out.append((f, t, int(v), v / rt if rt else 0, RISK[t]))
    out.sort(key=lambda x: (-x[4], -x[2]))
    return out[:top]


dr = downward_rate(panel, selected_month)
k1, k2, k3, k4 = st.columns(4)
k1.metric("위험 하강 전이율", "해당 없음" if dr is None else f"{dr:.1%}",
          help="더 위험한 상품으로 이동한 차주 비율 (마지막 달은 다음 달 없어 해당 없음)")
k2.metric("리볼빙·현금서비스", f"{this_month['revolving']:,}명",
          delta=int(this_month['revolving'] - prev_month['revolving']), delta_color="inverse")
k3.metric("카드론", f"{this_month['card']:,}명",
          delta=int(this_month['card'] - prev_month['card']), delta_color="inverse")
k4.metric("주담대", f"{this_month['mortgage']:,}명",
          delta=int(this_month['mortgage'] - prev_month['mortgage']))

st.write("")

r1_left, r1_right = st.columns([1.1, 1])
with r1_left:
    st.plotly_chart(make_line(counts, selected_month), width="stretch")
with r1_right:
    st.plotly_chart(make_sankey(panel, selected_month), width="stretch")

md = panel[panel["month"] == selected_month]
r2_left, r2_right = st.columns([1.3, 1])

with r2_left:
    st.markdown(f"##### 전이행렬 · {selected_month}월 → {selected_month+1}월")
    st.caption("행(이전) → 열(현재) 이동 비중. 대각선은 상태 유지, 우상단일수록 위험 방향.")
    if selected_month == 11:
        st.info("마지막 달은 다음 달이 없어 전이행렬이 없습니다.")
    else:
        st.dataframe(make_matrix(md), width="stretch")

with r2_right:
    st.markdown("##### 위험 전이 경보")
    st.caption("위험 방향 전이 상위 후보 — 개인 조기경보(프로젝트 1)로 넘길 대상.")
    alerts = get_alerts(md)
    if not alerts:
        st.info("이 달에는 위험 하강 전이가 없습니다.")
    for f, t, v, share, r in alerts:
        color = HOT if t in ("card", "revolving") else MID
        note = ("초고금리 종착 — 즉시 조기경보 대상" if t == "revolving"
                else "2금융 하강 — 선제 상담 권고" if t == "card"
                else "상위 위험군 진입 감시")
        st.markdown(f"""
        <div style="background:#160f10;border:1px solid #3a1f1f;border-radius:12px;
                    padding:12px 14px;margin-bottom:9px">
          <span style="color:{color};font-weight:800">{KOR[f]} → {KOR[t]}</span>
          <span style="color:{INK}"> · {v}명 ({share:.0%})</span><br>
          <span style="color:{INK_DIM};font-size:12px">{note}</span>
        </div>""", unsafe_allow_html=True)

st.caption(
    "합성 데이터 시뮬레이션입니다. 규제 강화(6월) 이후 하강 전이 확률이 상승하도록 설계했으며, "
    "확률 가정의 근거는 REFERENCES.md를 참조하세요. 실배포 시 build_panel을 실제 여신 데이터로 "
    "교체하면 동일 파이프라인으로 실측 전이가 산출됩니다.")