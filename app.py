import streamlit as st
import numpy_financial as npf

# 1. 화면 기본 설정
st.set_page_config(page_title="민자사업 사업성 분석기", layout="wide")

# --- 🎨 반응형 디자인 강화 (CSS) ---
st.markdown("""
<style>
    html, body, [class*="css"], * {
        font-family: 'Pretendard', 'Apple SD Gothic Neo', '맑은 고딕', sans-serif !important;
    }
    
    /* 제목 디자인 */
    h1 { 
        font-size: clamp(20px, 5vw, 28px) !important; 
        font-weight: 800 !important; 
        color: #1e293b !important;
        margin-bottom: 20px !important;
        text-align: center;
    }

    /* 입력 구역 배경색 및 테두리 */
    .input-container {
        background-color: #f8fafc;
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #e2e8f0;
        margin-bottom: 25px;
    }

    /* 결과 카드 디자인 (모바일 최적화) */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 15px !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    div[data-testid="stMetricValue"] {
        font-size: clamp(18px, 4vw, 26px) !important; 
        font-weight: 800 !important;
        color: #0f172a !important;
    }

    /* 버튼 및 입력창 크기 조절 */
    .stNumberInput input {
        font-size: 16px !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("🛣️ 도로 민자사업(BTO) 사업성 분석기")

# 2. [메인 화면] 입력 구역 (사이드바 사용 안 함)
st.subheader("⚙️ 사업 조건 입력")

# 사업 방식 선택을 가장 먼저 배치
business_model = st.selectbox("0. 사업 방식 선택", ["BTO (수익형)", "BTO-a (손익공유형)"])

# 입력창을 여러 열로 배치 (데스크탑에선 옆으로, 모바일에선 위아래로 자동 정렬)
st.markdown('<div class="input-container">', unsafe_allow_html=True)
col_in1, col_in2, col_in3 = st.columns([1, 1, 1])

with col_in1:
    capex_base = st.number_input("1. 공사비 (억원)", value=5000.0, step=100.0)
    length_km = st.number_input("2. 사업연장 (km)", value=20.0, step=1.0)
    op_years = st.number_input("3. 운영기간 (년)", value=30.0, step=1.0)

with col_in2:
    annual_revenue = st.number_input("4. 연평균 운영수입 (억원)", value=450.0, step=10.0)
    discount_rate = st.number_input("5. 할인율 (%)", value=4.5, step=0.1)
    opex_per_km = st.number_input("6. 년간운영비 (억원/km)", value=3.0, step=0.1)

with col_in3:
    build_years = st.number_input("7. 공사기간 (년)", value=5.0, step=1.0)
    incidental_pct = st.number_input("8. 부대비 (%)", value=15.0, step=1.0)
    subsidy_pct = st.number_input("9. 건설보조금 (%)", value=30.0, step=1.0)

# 부대비 및 보조금 자동 계산 결과 표시
incidental_cost = capex_base * (incidental_pct / 100.0)
total_project_cost = capex_base + incidental_cost
subsidy_amount = total_project_cost * (subsidy_pct / 100.0)

st.write(f"💡 **산출 정보:** 부대비 {incidental_cost:,.0f}억 | 총사업비 {total_project_cost:,.0f}억 | 보조금 {subsidy_amount:,.0f}억")

# BTO-a 전용 조건 (BTO-a 선택 시에만 표시)
risk_sharing_pct = 70.0
min_guarantee_rate = 2.5
private_share_pct = 50.0

if business_model == "BTO-a (손익공유형)":
    st.markdown("---")
    st.markdown("### 🔒 BTO-a 전용 조건")
    col_a1, col_a2, col_a3 = st.columns(3)
    with col_a1:
        risk_sharing_pct = st.number_input("10. 위험분담비율 (%)", value=70.0)
    with col_a2:
        min_guarantee_rate = st.number_input("11. 최소보장수익률 (%)", value=2.5)
    with col_a3:
        private_share_pct = st.number_input("12. 초과수익 공유비율 (%)", value=50.0)

st.markdown('</div>', unsafe_allow_html=True)

# 3. 계산 로직
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
        annual_net_cash = annual_capital_recovery

cash_flows = [-annual_capex] * int(safe_build_years) + [annual_net_cash] * int(safe_op_years)

try:
    firr = float(npf.irr(cash_flows)) * 100.0
    if str(firr) == 'nan': firr = 0.0
except:
    firr = 0.0
try:
    npv = float(npf.npv(discount_rate / 100.0, cash_flows))
except:
    npv = 0.0

# 4. 결과 출력
st.markdown("---")
st.subheader(f"📊 분석 결과 요약 ({business_model})")

res_col1, res_col2 = st.columns(2)
with res_col1:
    st.metric("예상 사업수익률 (FIRR)", f"{firr:.2f} %")
with res_col2:
    st.metric("순현재가치 (NPV)", f"{npv:,.0f} 억원")

st.markdown("<br>", unsafe_allow_html=True)

if npv > 0 and firr > discount_rate:
    st.success(f"**🟢 사업성 양호** : 타당성이 확보된 것으로 추정됩니다.")
else:
    st.error(f"**🔴 타당성 부족** : 요구 수익률에 미달합니다.")

# 상세 현금 요약
st.info(f"""
**민간 투입 총액:** {private_capex:,.0f} 억원 | **민간 회수 총액:** {annual_net_cash * safe_op_years:,.0f} 억원  
**단순 예상 차익:** {(annual_net_cash * safe_op_years) - private_capex:,.0f} 억원
""")
