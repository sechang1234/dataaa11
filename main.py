import streamlit as st
import pandas as pd
import numpy as np
import os

# 1. 웹앱 제목 및 서론
st.set_page_config(page_title="원화 환율 변동 추이 분석", layout="wide")
st.title("📈 주요국 통화의 대원화 환율 변동 추이 및 통계적 분석")
st.markdown("""
본 웹앱은 제공된 환율 데이터를 바탕으로 주요국 통화(미국 달러, 일본 엔, 중국 위안)의 대원화 환율 추이를 통계적으로 분석한 탐구 보고서 양식의 대시보드입니다.
""")

# 2. 데이터 업로드 및 자동 로드 기능 (CSV 인코딩 오류 방지 추가)
st.sidebar.header("📁 데이터 업로드")
uploaded_file = st.sidebar.file_uploader("주요국 통화 파일을 업로드하세요 (CSV 또는 엑셀 모두 가능)", type=["csv", "xlsx"])

@st.cache_data
def load_data(file_source, is_excel=False):
    if is_excel:
        df = pd.read_excel(file_source, skiprows=8, names=['날짜', '원/달러', '원/100엔', '원/위안'])
    else:
        # 한글 인코딩 오류(UnicodeDecodeError) 해결을 위한 다중 인코딩 시도 로직
        encodings = ['utf-8', 'cp949', 'euc-kr', 'utf-8-sig']
        df = None
        for enc in encodings:
            try:
                if hasattr(file_source, 'seek'):
                    file_source.seek(0)
                df = pd.read_csv(file_source, skiprows=8, names=['날짜', '원/달러', '원/100엔', '원/위안'], encoding=enc)
                break # 성공하면 루프 탈출
            except (UnicodeDecodeError, LookupError):
                continue
        
        if df is None:
            raise ValueError("파일의 인코딩을 지원하지 않습니다. UTF-8 또는 CP949 형식이어야 합니다.")
    
    # 날짜 데이터 변환 및 인덱스 설정
    df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
    df = df.dropna(subset=['날짜']).sort_values('날짜')
    
    # 숫자형 데이터 변환
    for col in ['원/달러', '원/100엔', '원/위안']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        
    return df

# 기본 파일 이름 정의들
FILE_NAME_CSV = "주요국 통화의 대원화 환율.xlsx - Sheet1.csv"
FILE_NAME_XLSX = "주요국 통화의 대원화 환율.xlsx"

df_raw = None

# 1순위: 사용자가 직접 웹 화면에 업로드했을 때
if uploaded_file is not None:
    is_excel = uploaded_file.name.endswith('.xlsx')
    df_raw = load_data(uploaded_file, is_excel=is_excel)
# 2순위: 깃허브 서버 내에 CSV 파일이 존재할 때
elif os.path.exists(FILE_NAME_CSV):
    df_raw = load_data(FILE_NAME_CSV, is_excel=False)
# 3순위: 깃허브 서버 내에 진짜 엑셀 파일이 존재할 때
elif os.path.exists(FILE_NAME_XLSX):
    df_raw = load_data(FILE_NAME_XLSX, is_excel=True)
else:
    st.warning("⚠️ 데이터 파일을 찾을 수 없습니다. 왼쪽 사이드바에서 엑셀(.xlsx) 또는 CSV 파일을 업로드해 주세요.")

# 데이터가 성공적으로 로드된 경우에만 아래 분석 코드가 실행됩니다.
if df_raw is not None:
    try:
        # 3. 사이드바 - 분석 기간 및 통화 선택
        st.sidebar.header("🔍 분석 설정")
        
        min_date = df_raw['날짜'].min().to_pydatetime()
        max_date = df_raw['날짜'].max().to_pydatetime()
        
        start_date, end_date = st.sidebar.slider(
            "분석 기간 선택",
            min_value=min_date,
            max_value=max_date,
            value=(max_date - pd.Timedelta(days=365*2), max_date)
        )
        
        # 필터링된 데이터 생성
        df = df_raw[(df_raw['날짜'] >= start_date) & (df_raw['날짜'] <= end_date)].copy()
        df.set_index('날짜', inplace=True)

        # 4. 본문 - [연구 1] 데이터 개요 및 기술 통계
        st.header("📋 1. 데이터 개요 및 기술 통계 분석")
        st.markdown("선택한 기간 동안의 기초 통계량을 통해 각 통화의 평균적인 수준과 분포의 흩어진 정도를 파악합니다.")
        
        cols = st.columns(3)
        currencies = ['원/달러', '원/100엔', '원/위안']
        
        for i, curr in enumerate(currencies):
            with cols[i]:
                valid_series = df[curr].dropna()
                if not valid_series.empty:
                    latest_val = valid_series.iloc[-1]
                    st.metric(label=f"최근 {curr}", value=f"{latest_val:,.2f} 원")
                else:
                    st.metric(label=f"최근 {curr}", value="데이터 없음")

        st.subheader("📊 주요 통계 지표")
        stats_df = df.describe().T[['count', 'mean', 'std', 'min', 'max']]
        stats_df.columns = ['관측치 개수', '평균값', '표준편차(변동성)', '최솟값', '최댓값']
        st.dataframe(stats_df.style.format("{:,.2f}"))

        # 5. 본문 - [연구 2] 환율 변동 추이 및 이동평균선 분석
        st.header("📈 2. 통화별 환율 추세 및 이동평균선(MA) 분석")
        st.markdown("각 통화의 실제 환율과 함께 **20일, 60일 이동평균선(Moving Average)**을 개별 시각화하여 단기·장기 추세를 분석합니다.")
        
        tab1, tab2, tab3 = st.tabs(["🇺🇸 원/달러", "🇯🇵 원/100엔", "🇨🇳 원/위안"])
        
        with tab1:
            st.subheader("미국 달러 (USD) 추세 분석")
            df_usd = pd.DataFrame(index=df.index)
            df_usd['실제 달러 환율'] = df['원/달러']
            df_usd['20일 이평선'] = df['원/달러'].rolling(window=20).mean()
            df_usd['60일 이평선'] = df['원/달러'].rolling(window=60).mean()
            # 🎨 블루 계열 색상 지정 (실제값은 진하게, 이평선은 연하게)
            st.line_chart(df_usd, color=["#003f5c", "#2f4b7c", "#a0c4ff"])
            
        with tab2:
            st.subheader("일본 엔 (JPY 100) 추세 분석")
            df_jpy = pd.DataFrame(index=df.index)
            df_jpy['실제 엔화 환율'] = df['원/100엔']
            df_jpy['20일 이평선'] = df['원/100엔'].rolling(window=20).mean()
            df_jpy['60일 이평선'] = df['원/100엔'].rolling(window=60).mean()
            # 🎨 레드/오렌지 계열 색상 지정
            st.line_chart(df_jpy, color=["#f95d6a", "#ff7c43", "#ffa600"])
            
        with tab3:
            st.subheader("중국 위안 (CNY) 추세 분석")
            df_cny = pd.DataFrame(index=df.index)
            df_cny['실제 위안 환율'] = df['원/위안']
            df_cny['20일 이평선'] = df['원/위안'].rolling(window=20).mean()
            df_cny['60일 이평선'] = df['원/위안'].rolling(window=60).mean()
            # 🎨 그린 계열 색상 지정
            st.line_chart(df_cny, color=["#107c41", "#1f9e55", "#7bcd9b"])

        # 6. 본문 - [연구 3] 통화 간 통계적 상관관계 분석
        st.header("🔗 3. 통화 간 상관관계 및 연동성 검증")
        st.markdown("피어슨 상관계수(Pearson Correlation Coefficient)를 활용하여 원화 대비 주요국 통화들이 서로 얼마나 같은 방향으로 움직이는지 통계적으로 증명합니다.")
        
        corr_matrix = df[currencies].corr(method='pearson')
        st.dataframe(corr_matrix.style.format("{:.4f}"))

        # 7. 본문 - [연구 4] 일일 수익률 분포 및 변동성 분석
        st.header("⚡ 4. 환율 일일 변동률 및 통계적 위험도 분석")
        st.markdown("""
        환율의 전일 대비 일일 변동률(%)을 분석합니다. 
        통계학적으로 변동률의 그래프가 0%를 중심으로 중심에 많이 몰려있을수록 안정적인 자산이며, 양옆으로 넓게 퍼질수록 변동성(리스크)이 큰 자산임을 뜻합니다.
        """)
        
        return_df = df[currencies].pct_change() * 100
        return_df_clean = return_df.dropna()
        recent_return = return_df_clean.tail(150)
        
        v_tab1, v_tab2 = st.tabs(["📉 시계열 변동률 추이 비교", "📊 변동성 분포(히스토그램) 분석"])
        
        with v_tab1:
            st.subheader("최근 150거래일 일일 변동률 추이 (%)")
            # 🎨 선들이 서로 완벽히 찢어져 보이도록 눈에 확 띄는 원색 계열(달러=블루, 엔화=핫핑크, 위안=초록) 지정
            st.line_chart(recent_return, color=["#0055ff", "#ff007f", "#00aa55"])
            
        with v_tab2:
            st.subheader("통화별 변동률 분포 비교 (Histogram)")
            
            hist_data = pd.DataFrame()
            for curr in currencies:
                counts, bin_edges = np.histogram(return_df_clean[curr], bins=30)
                bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
                hist_data[f'{curr} 분포'] = pd.Series(counts, index=np.round(bin_centers, 2))
            
            # 🎨 바 차트 히스토그램도 마찬가지로 눈에 띄는 확실한 독립 색상으로 지정
            st.bar_chart(hist_data, color=["#1f77b4", "#ff7f0e", "#2ca02c"])
            st.caption("💡 **그래프 읽는 법:** 가운데(0%) 영역이 높이 솟구칠수록 평소 안정적인 통화이며, 양끝 변동률 영역에 막대가 많을수록 갑작스러운 폭등락이 잦은 위험 통화입니다.")

        # 변동성 통계 증명 테이블
        st.subheader("📊 리스크 평가 지표 요약")
        vol_summary = pd.DataFrame({
            '일일 변동성 (표준편차 %)' : return_df_clean.std(),
            '최대 당일 상승률 (%)' : return_df_clean.max(),
            '최대 당일 하락률 (%)' : return_df_clean.min()
        })
        st.dataframe(vol_summary.style.format("{:.3f}%"))
        
        # 통계 기반 결론 도출 (자동 데이터 연동 수치 제시)
        highest_vol_curr = vol_summary['일일 변동성 (표준편차 %)'].idxmax()
        highest_vol_val = vol_summary['일일 변동성 (표준편차 %)'].max()
        
        st.info(f"""
        📝 **통계적 분석 결론:** 선택하신 기간 동안 대원화 환율 시장에서 가장 위험도(변동성)가 높은 통화는 **{highest_vol_curr}**(표준편차 {highest_vol_val:.3f}%)인 것으로 통계적으로 증명되었습니다. 
        외환 리스크 관리 시 해당 통화의 노출액에 대한 최우선적인 헤지(Hedge) 전략이 요구됩니다.
        """)

    except Exception as e:
        st.error(f"데이터 분석 중 오류가 발생했습니다. 파일 형식이 올바른지 확인해 주세요. 오류 내용: {e}")
        with v_tab2:
            st.subheader("📊 통화별 변동률 분포 분석 (Histogram)")
            st.markdown("가운데(0%) 영역에 막대가 높이 솟구칠수록 평소 안정적인 통화이며, 양끝으로 넓게 퍼질수록 변동성이 큰 위험 통화입니다.")
            
            # 1. 히스토그램 통계 데이터 선행 계산 (구간 30개)
            hist_data = pd.DataFrame()
            for curr in currencies:
                counts, bin_edges = np.histogram(return_df_clean[curr], bins=30)
                bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
                hist_data[f'{curr} 변동 빈도'] = pd.Series(counts, index=np.round(bin_centers, 2))
            
            # 2. 내부 하위 탭을 만들어 시각적 피로도 분산
            sub_tab0, sub_tab1, sub_tab2, sub_tab3 = st.tabs([
                "🔄 종합 교차 비교", "🇺🇸 미국 달러 분포", "🇯🇵 일본 엔 분포", "🇨🇳 중국 위안 분포"
            ])
            
            with sub_tab0:
                st.markdown("**💡 종합 비교:** 세 통화의 분포를 동시에 겹쳐봅니다. 어떤 통화의 스펙트럼이 가장 넓은지 확인하세요.")
                st.bar_chart(hist_data, color=["#1f77b4", "#ff7f0e", "#2ca02c"])
                
            with sub_tab1:
                st.markdown("**🇺🇸 미국 달러 (USD) 일일 변동률 분포**")
                st.bar_chart(hist_data[[f'원/달러 변동 빈도']], color=["#1f77b4"])
                
            with sub_tab2:
                st.markdown("**🇯🇵 일본 엔 (JPY 100) 일일 변동률 분포**")
                st.bar_chart(hist_data[[f'원/100엔 변동 빈도']], color=["#ff7f0e"])
                
            with sub_tab3:
                st.markdown("**🇨🇳 중국 위안 (CNY) 일일 변동률 분포**")
                st.bar_chart(hist_data[[f'원/위안 변동 빈도']], color=["#2ca02c"])
                
            st.caption("💡 **통계학적 팁:** 특정 통화의 그래프가 양옆 꼬리(Tail) 방향으로 갈수록 막대가 길고 많다면, 이는 외환 시장에서 '뚱뚱한 꼬리(Fat-tail) 현상', 즉 극단적인 폭등락 리스크가 자주 발생했음을 완벽하게 증명합니다.")
