import streamlit as st
import numpy_financial as npf

# 1. 화면 기본 설정 (여백을 넓게 써서 시원하게 배치)
st.set_page_config(page_title="민자사업 사업성 분석기", layout="wide")

# --- 🎨 모던/세련된 UI 디자인 적용 (CSS 반응형 추가) ---
st.markdown("""
<style>
    /* 전체 폰트 및 배경색 정리 */
    html, body, [class*="css"], * {
        font-family: 'Pretendard', 'Apple SD Gothic Neo', '맑은 고딕', sans-serif !important;
    }
    
    /* 제목 그라데이션 및 디자인 */
    h1 { 
        font-size: clamp(22px, 3vw, 32px) !important; /* 화면 크기에 따라 반응 */
        font-weight: 800 !important; 
        color: #1e293b !important;
        padding-bottom: 20px !important;
        border-bottom: 2px solid #e2e8f0;
        margin-bottom: 30px !important;
    }
    h2, h3 { 
        color: #334155 !important; 
        font-weight: 700 !important; 
        margin-top: 20px !important;
    }

    /* 📊 결과값을 [고급스러운 카드 형태]로 변환 */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 20px 24px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        transition: transform 0.2s ease-in-out;
        overflow-wrap: break-word !important; /* 단어가 길면 줄바꿈 허용 */
        word-break: keep-all !important;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }
    
    /* 카드 안의 핵심 숫자 크기 반응형 조절 (잘림 방지) */
    div[data-testid="stMetricValue"] {
        /* 화면이 작아지면 글씨도 20px까지 부드럽게 작아짐 */
        font-size: clamp(20px, 3vw, 30px) !important; 
        font-weight: 800 !important;
        color: #0f172a !important; 
        white-space: pre-wrap !important; /* 줄바꿈 허용 */
    }
    
    /* 카드 안의 항목 이름 반응형 조절 */
    div[data-testid="stMetricLabel"] p {
        font-size: clamp(13px, 1.5vw, 15px) !important;
        font-weight: 600 !important;
        color: #64748b !important; 
        margin-bottom: 5px !important;
        white-space: pre-wrap !important;
    }

    /* 알림창 모서리 둥글게 */
    div[data-testid="stAlert"] {
        border-radius: 10px !important;
        border: none !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("🛣️ 도로 민자사업(BTO) 사업성 분석 대시보드")
st.markdown("💡 **Tip: 왼쪽 입력창에서 숫자를 입력한 뒤 `Tab` 키를 누르면 다음 항목으로 바로 이동합니다.**")

# 2. 좌측 입력창 (사이드바)
with st.sidebar:
    st.header("⚙️ 입력 변수 설정")
    
    business_model = st.selectbox("0. 사업 방식 선택", ["BTO (수익형)", "BTO-a (손익공유형)"])
    
    st.markdown("---")
    capex_base = st.number_input("1. 공사비 (억원)", value=5000.0, step=100.0)
    length_km = st.number_input("2. 사업연장 (km)", value=20.0, step=1.0)
    op_years = st.number_input("3. 운영기간 (년)", value=30.0, step=1.0)
    annual_revenue = st.number_input("4. 연평균 운영수입 (억원)", value=450.0, step=10.0)
    discount_rate = st.number_input("5. 할인율 (%)", value=4.5, step=0.1)
    opex_per_km = st.number_input("6. 년간운영비 (억원/km)", value=3.0, step=0.1)
    build_years = st.number_input("7. 공사기간 (년)", value=5.0, step=1.0)
    
    st.markdown("---")
    incidental_pct = st.number_input("8. 부대비 (%)", value=15.0, step=1.0)
    incidental_cost = capex_base * (incidental_pct / 100.0)
    st.info(f"↳ 산출 부대비: **{incidental_cost:,.0f} 억원**")
    
    subsidy_pct = st.number_input("9. 건설보조금 (%)", value=30.0, step=1.0)
    total_project_cost = capex_base + incidental_cost
    subsidy_amount = total_project_cost * (subsidy_pct / 100.0)
    st.info(f"↳ 산출 건설보조금: **{subsidy_amount:,.0f} 억원**")

    risk_sharing_pct = 70.0
    min_guarantee_rate = 2.5
    private_share_pct = 50.0
    
    if business_model == "BTO-a (손익공유형)":
        st.markdown("---")
        st.subheader("🔒 BTO-a 전용 조건")
        risk_sharing_pct = st.number_input("10. 위험분담비율 (%)", value=70.0, step=1.0)
        min_guarantee_rate = st.number_input("11. 최소보장수익률 (%)", value=2.5, step=0.1)
        private_share_pct = st.number_input("12. 초과수익 공유비율 (%)", value=50.0, step=1.0)

# 3. 핵심 현금흐름 계산
safe_build_years = max(1.0, build_years)
safe_op_years = max(1.0, op_years)

private_capex = total_project_cost - subsidy_amount
annual_capex = private_capex / safe_build_years
annual_opex = length_km * opex_per_km

base_revenue = 0.0
surplus_profit = 0.0

if business_model == "BTO (수익형)":
    annual_net_cash = annual_revenue - annual_opex
else:
    guaranteed_principal = private_capex * (risk_sharing_pct / 100.0)
    
    if min_guarantee_rate > 0:
        annual_capital_recovery = npf.pmt(min_guarantee_rate / 100.0, safe_op_years, -guaranteed_principal)
    else:
        annual_capital_recovery = guaranteed_principal / safe_op_years

    base_revenue = annual_opex + annual_capital_recovery
    
    if annual_revenue > base_revenue:
        surplus_profit = annual_revenue - base_revenue
        annual_net_cash = annual_capital_recovery + (surplus_profit * (private_share_pct / 100.0))
    else:
        surplus_profit = 0.0
        annual_net_cash = annual_capital_recovery

cash_flows = [-annual_capex] * int(safe_build_years) + [annual_net_cash] * int(safe_op_years)

try:
    firr = float(npf.irr(cash_flows)) * 100.0
    if str(firr) == 'nan':
        firr = 0.0
except:
    firr = 0.0
    
try:
    npv = float(npf.npv(discount_rate / 100.0, cash_flows))
except:
    npv = 0.0

# 4. 결과 화면 (UI)
st.subheader(f"📊 투자 및 현금흐름 요약 [{business_model}]")

col1, col2, col3, col4 = st.columns(4)
col1.metric("총 사업비 (부대비 포함)", f"{total_project_cost:,.0f} 억원")
col2.metric("실제 민간투자비", f"{private_capex:,.0f} 억원")
col3.metric("연간 운영비", f"{annual_opex:,.0f} 억원")
col4.metric("연간 민간 순수익", f"{annual_net_cash:,.0f} 억원")

st.markdown("<br>", unsafe_allow_html=True)
st.subheader("🎯 핵심 타당성 지표")

col5, col6 = st.columns(2)
col5.metric("예상 사업수익률 (FIRR)", f"{firr:.2f} %")
col6.metric("순현재가치 (NPV)", f"{npv:,.0f} 억원")

st.markdown("<br>", unsafe_allow_html=True)

if npv > 0 and firr > discount_rate:
    st.success(f"**🟢 사업성 양호** : 예상 수익률({firr:.2f}%)이 요구 할인율({discount_rate}%)을 상회하여 사업 타당성이 확보된 것으로 추정됩니다.")
else:
    st.error(f"**🔴 타당성 부족** : 예상 수익률이 요구 할인율에 미치지 못합니다. 공사비 절감, 보조금 증액 또는 수입 증대 방안이 필요합니다.")

st.markdown("<hr style='margin-top: 30px; margin-bottom: 30px;'>", unsafe_allow_html=True)
st.subheader("💰 단순 사업 수지 (할인율 미적용)")

if business_model == "BTO-a (손익공유형)":
    bto_a_msg = f"**[BTO-a 수익 구조]** 보전기준수입({base_revenue:,.0f}억) 초과분({surplus_profit:,.0f}억) 중 **{private_share_pct}%**만 민간 수익으로 반영되었습니다."
    st.warning(bto_a_msg)

total_net_inflow = annual_net_cash * safe_op_years
simple_profit = total_net_inflow - private_capex

summary_msg = f"**민간 투입 누적:** {private_capex:,.0f} 억원 &nbsp;&nbsp;➡️&nbsp;&nbsp; **민간 회수 누적:** {total_net_inflow:,.0f} 억원 &nbsp;&nbsp;|&nbsp;&nbsp; **단순 예상 차익:** {simple_profit:,.0f} 억원"
st.info(summary_msg)