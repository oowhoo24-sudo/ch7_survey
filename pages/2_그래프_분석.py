import streamlit as st
import pandas as pd
import numpy as np

# 페이지 기본 설정
st.set_page_config(
    page_title="설문 데이터 그래프 분석",
    page_icon="📈",
    layout="wide"
)


# ---------------------------------------------------------
# [Class] 데이터 분석 및 시각화를 담당하는 클래스
# ---------------------------------------------------------
class SurveyAnalyzer:
    def __init__(self, df: pd.DataFrame):
        """분석 대상 데이터프레임 초기화"""
        self.df = df

    def get_summary_metrics(self):
        """1. 요약 지표 계산 (유효 응답 수, 평균 AI 사용 시간, AI 윤리의식(Q6 또는 Q6R) 평균)"""
        valid_responses = len(self.df)

        # AI 사용 시간 평균 계산
        mean_ai_time = 0.0
        if 'AI사용시간' in self.df.columns and valid_responses > 0:
            mean_ai_time = self.df['AI사용시간'].mean()

        # AI 윤리의식 점수 평균 계산 (Q6 또는 Q6R 활용)
        mean_ethics = 0.0
        target_col = 'Q6R' if 'Q6R' in self.df.columns else ('Q6' if 'Q6' in self.df.columns else None)
        if target_col and valid_responses > 0:
            numeric_vals = pd.to_numeric(self.df[target_col], errors='coerce')
            mean_ethics = numeric_vals.mean()

        return valid_responses, mean_ai_time, mean_ethics

    def get_college_comparison_data(self, raw_df: pd.DataFrame = None):
        """2. 정제 전후 단과대학별 응답자 수 비교 데이터 생성"""
        comparison_dict = {}

        # 정제된 데이터 단과대학 분포
        if '소속단과대학' in self.df.columns:
            clean_counts = self.df['소속단과대학'].value_counts()
            comparison_dict['정제 후'] = clean_counts

        # 정제 전(원본) 데이터 단과대학 분포 (원본이 있는 경우)
        if raw_df is not None and '소속단과대학' in raw_df.columns:
            # 원본 데이터에도 동일한 단과대학 분류 함수 적용 필요 시 반영
            raw_counts = raw_df['소속단과대학'].value_counts()
            comparison_dict['정제 전'] = raw_counts

        result_df = pd.DataFrame(comparison_dict).fillna(0)
        return result_df

    def get_group_statistics(self, group_col: str):
        """3. 집단 비교 (학년별 혹은 단과대학별 평균 및 인원 수 계산)"""
        if group_col not in self.df.columns:
            return pd.DataFrame()

        # 수치형 문항 자동 탐색 (Q로 시작하는 열 또는 Q6R)
        numeric_cols = [c for c in self.df.columns if c.startswith('Q') or c == 'AI사용시간']

        # 데이터 타입을 수치형으로 강제 변환
        analysis_df = self.df.copy()
        for col in numeric_cols:
            analysis_df[col] = pd.to_numeric(analysis_df[col], errors='coerce')

        # 그룹별 평균 및 인원 수 집계
        grouped = analysis_df.groupby(group_col).agg(
            인원수=('AI사용시간', 'count'),
            **{f"{col}_평균": (col, 'mean') for col in numeric_cols}
        )

        # 소수점 둘째 자리 반올림
        grouped = grouped.round(2)
        return grouped


# ---------------------------------------------------------
# [Function] 화면 렌더링 및 UI 제어 함수
# ---------------------------------------------------------
def load_data():
    """세션 스테이트 또는 파일 업로드를 통해 데이터 확보"""
    if "clean_df" in st.session_state and st.session_state["clean_df"] is not None:
        st.info("세션에 저장된 정제 데이터를 불러왔습니다.")
        return st.session_state["clean_df"]

    st.warning("세션에 정제된 데이터가 없습니다. 정제된 CSV 파일을 업로드해주세요.")
    uploaded_file = st.file_uploader("정제된 설문 데이터 CSV 업로드", type=["csv"])

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        st.session_state["clean_df"] = df
        return df

    return None


def render_dashboard():
    """메인 대시보드 화면 렌더링 함수"""
    st.title("설문 데이터 그래프 분석 대시보드")
    st.write("정제된 설문 데이터를 바탕으로 주요 지표와 그룹별 통계를 시각화합니다.")

    # 데이터 로드
    df = load_data()
    if df is None:
        st.stop()

    # 분석 클래스 인스턴스화
    analyzer = SurveyAnalyzer(df)

    # 1. 요약 지표 섹션
    st.subheader("1. 핵심 요약 지표")
    valid_n, mean_time, mean_ethics = analyzer.get_summary_metrics()

    col1, col2, col3 = st.columns(3)
    col1.metric("유효 응답자 수", f"{valid_n} 명")
    col2.metric("평균 AI 사용 시간", f"{mean_time:.1f} 분")
    col3.metric("AI 윤리의식 평균 점수", f"{mean_ethics:.2f} 점")

    st.markdown("---")

    # 2. 정제 전후 비교 섹션 (가로 막대 차트)
    st.subheader("2. 정제 전후 단과대학별 응답자 수 비교")

    # 원본 파일이 있는 경우 비교 수행, 없으면 현재 데이터만 표시
    raw_file = st.file_uploader("정제 전 원본 CSV 파일도 비교하려면 업로드하세요 (선택사항)", type=["csv"], key="raw_file_uploader")
    raw_df = pd.read_csv(raw_file) if raw_file else None

    comparison_df = analyzer.get_college_comparison_data(raw_df)

    if not comparison_df.empty:
        st.write("단과대학별 응답자 분포 (가로 막대 차트)")
        # Streamlit 기본 bar_chart 활용 (가로 형태 출력을 위해 데이터 프레임 구조 확인)
        st.bar_chart(comparison_df, horizontal=True)
    else:
        st.info("비교할 단과대학 데이터가 부족합니다.")

    st.markdown("---")

    # 3. 탭 구성 (4개 탭)
    st.subheader("3. 상세 분석 및 집단 비교")
    tab1, tab2, tab3, tab4 = st.tabs(["응답자 구성", "문항별 평균", "집단 비교", "사용 시간과 점수"])

    # 탭 1: 응답자 구성
    with tab1:
        st.markdown("### 응답자 구성 현황")
        col_a, col_b = st.columns(2)

        with col_a:
            if '학년' in df.columns:
                st.write("학년별 분포")
                grade_counts = df['학년'].value_counts()
                st.bar_chart(grade_counts, horizontal=True)
            else:
                st.info("학년 데이터가 존재하지 않습니다.")

        with col_b:
            if '소속단과대학' in df.columns:
                st.write("단과대학별 분포")
                college_counts = df['소속단과대학'].value_counts()
                st.bar_chart(college_counts, horizontal=True)
            else:
                st.info("단과대학 데이터가 존재하지 않습니다.")

    # 탭 2: 문항별 평균
    with tab2:
        st.markdown("### 설문 문항별 평균 점수")
        q_cols = [c for c in df.columns if c.startswith('Q')]
        if q_cols:
            # 문항별 평균 계산
            q_numeric = df[q_cols].apply(pd.to_numeric, errors='coerce')
            q_means = q_numeric.mean().round(2)

            st.dataframe(q_means.to_frame(name="평균 점수"), use_container_width=True)
            st.write("문항별 평균 시각화")
            st.bar_chart(q_means, horizontal=True)
        else:
            st.info("분석할 Q 문항 컬럼이 없습니다.")

    # 탭 3: 집단 비교
    with tab3:
        st.markdown("### 학년별 및 단과대학별 평균 통계")

        st.write("#### 학년별 집단 통계 (인원 수 및 문항별 평균)")
        if '학년' in df.columns:
            grade_stats = analyzer.get_group_statistics('학년')
            st.dataframe(grade_stats, use_container_width=True)
        else:
            st.info("학년 데이터가 존재하지 않습니다.")

        st.write("#### 단과대학별 집단 통계 (인원 수 및 문항별 평균)")
        if '소속단과대학' in df.columns:
            college_stats = analyzer.get_group_statistics('소속단과대학')
            st.dataframe(college_stats, use_container_width=True)
        else:
            st.info("단과대학 데이터가 존재하지 않습니다.")

    # 탭 4: 사용 시간과 점수
    with tab4:
        st.markdown("### AI 사용 시간과 주요 문항 간의 관계")
        if 'AI사용시간' in df.columns and q_cols:
            # 산점도를 위한 데이터 준비 (AI사용시간과 첫 번째 Q 문항 비교 등)
            scatter_target = st.selectbox("비교할 문항 선택", options=q_cols)

            if scatter_target:
                chart_data = df[['AI사용시간', scatter_target]].dropna()
                chart_data[scatter_target] = pd.to_numeric(chart_data[scatter_target], errors='coerce')

                st.write(f"AI 사용 시간과 {scatter_target} 산점도")
                st.scatter_chart(chart_data, x='AI사용시간', y=scatter_target)
        else:
            st.info("AI사용시간 또는 설문 문항 데이터가 부족합니다.")


# ---------------------------------------------------------
# [Main Execution] 앱 실행 진입점
# ---------------------------------------------------------
if __name__ == "__main__":
    render_dashboard()