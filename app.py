import streamlit as st
import numpy_financial as npf
import pandas as pd
from io import BytesIO

# 1. 화면 기본 설정
st.set_page_config(page_title="민자사업 사업성 분석", layout="wide")

# --- 🎨 디자인 및 가독성 강화 (CSS) ---
st.markdown("""
<style>
    html, body, [class*="css"], * {
        font-family: 'Pretendard', 'Apple SD Gothic Neo', '맑은 고딕', sans-serif !important;
    }
    h1 { 
        font-size: clamp(24px, 5vw, 32px) !important; 
        font-weight: 800 !important; 
        color: #1e293b !important;
        text-align: center;
        margin-bottom: 30px !important;
    }
    div[data-testid="stSelectbox"] label p {
        font-size: 22px !important;
        font-weight: 800 !important;
        color: #1f77b4 !important;
        margin-bottom: 12px !important;
    }
    .stNumberInput label p {
        font-size: 17px !important;
        font-weight: 700 !important;
        color: #334155 !important;
    }
    .stNumberInput input { font-size: 18px !important; }
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }

    .summary-card {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-top: 5px solid #1f77b4;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 10px;
    }
    .summary-label { font-size: 15px; color: #64748b; font-weight: 600; margin-bottom: 5px; }
    .summary-value { font-size: 22px; font-weight: 800; color: #1e293b; }
</style>
""", unsafe_allow_html=True)

st.title("🛣️ 도로 민자사업 사업성 분석")

# 2. [메인 화면] 입력 구역
st.subheader("⚙️ 사업 조건 입력")

business_model = st.selectbox("사업 방식 선택", ["BTO (수익형)", "BTO-a (손익공유형)"])

col_in1, col_in2, col_in3 = st.columns(3)
with col_in1:
    capex_base = st.number_input("1. 공사비 (억원)", value=5000.0, format="%.1f")
    length_km = st.number_input("2. 사업연장 (km)", value=20.0, format="%.1f")
    op_years = st.number_input("3. 운영기간 (년)", value=30.0, format="%.1f")
with col_in2:
    annual_revenue = st.number_input("4. 연평균 운영수입 (억원)", value=450.0, format="%.1f")
    discount_rate = st.number_input("5. 할인율 (%)", value=4.5, format="%.1f")
    opex_per_km = st.number_input("6. 년간운영비 (억원/km)", value=3.0, format="%.1f")
with col_in3:
    build_years = st.number_input("7. 공사기간 (년)", value=5.0, format="%.1f")
    incidental_pct = st.number_input("8. 부대비 (%)", value=15.0, format="%.1f")
    subsidy_pct = st.number_input("9. 건설보조금 (%)", value=30.0, format="%.1f")

# 산출 정보 계산
incidental_cost = capex_base * (incidental_pct / 100.0)
total_project_cost = capex_base + incidental_cost
subsidy_amount = total_project_cost * (subsidy_pct / 100.0)

st.markdown("<br>", unsafe_allow_html=True)
sc1, sc2, sc3 = st.columns(3)
with sc1:
    st.markdown(f'<div class="summary-card"><div class="summary-label">총 사업비</div><div class="summary-value">{total_project_cost:,.1f} 억</div></div>', unsafe_allow_html=True)
with sc2:
    st.markdown(f'<div class="summary-card"><div class="summary-label">건설보조금</div><div class="summary-value">{subsidy_amount:,.1f} 억</div></div>', unsafe_allow_html=True)
with sc3:
    st.markdown(f'<div class="summary-card"><div class="summary-label">기타 부대비</div><div class="summary-value">{incidental_cost:,.1f} 억</div></div>', unsafe_allow_html=True)

risk_sharing_pct, min_guarantee_rate, private_share_pct = 70.0, 2.5, 50.0
if business_model == "BTO-a (손익공유형)":
    st.markdown("---")
    st.subheader("🔒 BTO-a 전용 조건")
    col_a1, col_a2, col_a3 = st.columns(3)
    with col_a1: risk_sharing_pct = st.number_input("10. 위험분담비율 (%)", value=70.0, format="%.1f")
    with col_a2: min_guarantee_rate = st.number_input("11. 최소보장수익률 (%)", value=2.5, format="%.1f")
    with col_a3: private_share_pct = st.number_input("12. 초과수익 공유비율 (%)", value=50.0, format="%.1f")

# 3. 계산 로직
safe_build_years, safe_op_years = max(1.0, build_years), max(1.0, op_years)
private_capex = total_project_cost - subsidy_amount
annual_capex = private_capex / safe_build_years
annual_opex = length_km * opex_per_km

if business_model == "BTO (수익형)":
    annual_net_cash = annual_revenue - annual_opex
else:
    guaranteed_principal = private_capex * (risk_sharing_pct / 100.0)
    capital_recovery = npf.pmt(min_guarantee_rate / 100.0, safe_op_years, -guaranteed_principal) if min_guarantee_rate > 0 else guaranteed_principal / safe_op_years
    base_rev = annual_opex + capital_recovery
    annual_net_cash = capital_recovery + ((annual_revenue - base_rev) * (private_share_pct / 100.0)) if annual_revenue > base_rev else capital_recovery

cash_flows = [-annual_capex] * int(safe_build_years) + [annual_net_cash] * int(safe_op_years)
firr = float(npf.irr(cash_flows)) * 100.0 if not str(npf.irr(cash_flows)) == 'nan' else 0.0
npv = float(npf.npv(discount_rate / 100.0, cash_flows))

# 4. 결과 출력
st.markdown("---")
st.subheader("📊 분석 결과 요약")
res_col1, res_col2 = st.columns(2)
res_col1.metric("예상 사업수익률 (FIRR)", f"{firr:.2f} %")
res_col2.metric("순현재가치 (NPV)", f"{npv:,.0f} 억원")

if npv > 0 and firr > discount_rate: st.success("**🟢 사업성 양호** : 타당성이 확보된 것으로 추정됩니다.")
else: st.error("**🔴 타당성 부족** : 요구 수익률에 미달합니다.")

st.info(f"**민간 투입 총액:** {private_capex:,.1f} 억원 | **민간 회수 총액:** {annual_net_cash * safe_op_years:,.1f} 억원 | **단순 예상 차익:** {(annual_net_cash * safe_op_years) - private_capex:,.1f} 억원")

# --- 📥 엑셀 내보내기 (보고서 양식 적용) ---
def get_report_excel():
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('사업성 분석 보고서')

        # 서식 설정
        title_fmt = workbook.add_format({'bold': True, 'size': 16, 'bg_color': '#1f77b4', 'color': 'white', 'align': 'center', 'border': 1})
        header_fmt = workbook.add_format({'bold': True, 'bg_color': '#f1f5f9', 'border': 1, 'align': 'left'})
        val_fmt = workbook.add_format({'border': 1, 'align': 'right', 'num_format': '#,##0.0'})
        res_val_fmt = workbook.add_format({'bold': True, 'border': 1, 'align': 'right', 'font_color': '#1f77b4', 'num_format': '#,##0.00'})
        
        # 1. 제목
        worksheet.merge_range('A1:C1', f'도로 민자사업({business_model}) 개략 사업성 분석 보고서', title_fmt)
        
        # 2. 사업 개요 섹션
        worksheet.write('A3', '[1. 사업 기본 개요]', workbook.add_format({'bold': True, 'size': 12}))
        overview_data = [
            ("사업방식", business_model),
            ("사업연장", f"{length_km} km"),
            ("공사기간", f"{build_years} 년"),
            ("운영기간", f"{op_years} 년")
        ]
        for i, (k, v) in enumerate(overview_data):
            worksheet.write(i+3, 0, k, header_fmt)
            worksheet.write(i+3, 1, v, val_fmt)

        # 3. 투자비 및 재원조달 섹션
        worksheet.write('A9', '[2. 투자비 및 재원조달]', workbook.add_format({'bold': True, 'size': 12}))
        investment_data = [
            ("총 사업비", total_project_cost),
            ("건설보조금", subsidy_amount),
            ("기타 부대비", incidental_cost),
            ("실제 민간투자비", private_capex)
        ]
        for i, (k, v) in enumerate(investment_data):
            worksheet.write(i+9, 0, k, header_fmt)
            worksheet.write(i+9, 1, v, val_fmt)

        # 4. 사업성 분석 결과 섹션
        worksheet.write('A15', '[3. 사업성 분석 결과]', workbook.add_format({'bold': True, 'size': 12}))
        result_data = [
            ("예상 사업수익률(FIRR)", f"{firr:.2f}%"),
            ("순현재가치(NPV)", f"{npv:,.0f} 억원"),
            ("할인율 적용 기준", f"{discount_rate}%")
        ]
        for i, (k, v) in enumerate(result_data):
            worksheet.write(i+15, 0, k, header_fmt)
            worksheet.write(i+15, 1, v, res_val_fmt)

        # 열 너비 조정
        worksheet.set_column('A:A', 25)
        worksheet.set_column('B:B', 25)
        
    return output.getvalue()

st.download_button(
    label="📊 보고서 양식 엑셀 다운로드",
    data=get_report_excel(),
    file_name=f"민자사업_분석보고서_{business_model}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
