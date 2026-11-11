import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="데이터 정제", page_icon="🧹", layout="wide")

st.title("🧹 데이터 정제 (Data Cleaning)")

# ---------------------------------------------------------
# [사이드바] 설정 옵션
# ---------------------------------------------------------
st.sidebar.header("⚙️ 정제 옵션 설정")

# 이상치 허용 범위 (분 단위)
max_ai_hours = st.sidebar.slider(
    "AI 사용 시간 이상치 허용 범위 (분)",
    min_value=60,
    max_value=1440,
    value=480,
    step=30,
    help="설정한 분(minute)을 초과하는 데이터를 이상치로 처리하여 제거합니다."
)

# 결측치 처리 방식
na_option = st.sidebar.radio(
    "결측치(빈칸) 처리 방식",
    options=["그대로 두기", "행 삭제"],
    index=0
)


# ---------------------------------------------------------
# [도우미 함수] 텍스트 변환 로직
# ---------------------------------------------------------
def parse_ai_time(val):
    """'1시간 30분', '90분', '2' 등 다양한 텍스트를 분 단위 정수로 변환"""
    if pd.isna(val):
        return None
    val_str = str(val).strip()

    hours = 0
    minutes = 0

    h_match = re.search(r'(\d+)\s*시간', val_str)
    m_match = re.search(r'(\d+)\s*분', val_str)

    if h_match:
        hours = int(h_match.group(1))
    if m_match:
        minutes = int(m_match.group(1))

    if not h_match and not m_match:
        nums = re.findall(r'\d+', val_str)
        if nums:
            return int(nums[0])
        return None

    return hours * 60 + minutes


def parse_grade(val):
    """'1학년', '일학년', '1' 등 텍스트를 숫자 형태 문자열로 통일"""
    if pd.isna(val):
        return None
    val_str = str(val).strip()

    korean_num_map = {'일': '1', '이': '2', '삼': '3', '사': '4', '오': '5', '육': '6'}
    for kor, num in korean_num_map.items():
        if kor in val_str:
            return num

    digit = re.findall(r'\d+', val_str)
    if digit:
        return digit[0]

    return val_str


def classify_college(val):
    """단과대학 키워드 매핑"""
    if pd.isna(val):
        return "기타"
    val_str = str(val)
    if "인문" in val_str:
        return "인문대학"
    elif "사과" in val_str or "사회" in val_str:
        return "사회과학대학"
    elif "경통" in val_str or "경제" in val_str:
        return "경제통상대학"
    elif "경영" in val_str:
        return "경영대학"
    elif "사범" in val_str:
        return "사범대학"
    else:
        return "기타"


# ---------------------------------------------------------
# [메인] 파일 업로드 및 정제 프로세스
# ---------------------------------------------------------
uploaded_file = st.file_uploader("구글 설문지 CSV 파일(survey_raw.csv)을 업로드하세요.", type=["csv"])

if uploaded_file is not None:
    # 0. 데이터 불러오기
    raw_df = pd.read_csv(uploaded_file)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("총 응답자 수", f"{len(raw_df)} 명")
    with col2:
        st.metric("전체 열(Column) 수", f"{len(raw_df.columns)} 개")

    with st.expander("📄 업로드된 원본 데이터 전체 보기"):
        st.dataframe(raw_df, use_container_width=True)

    st.write("---")
    st.subheader("🛠️ 데이터 정제 수행")

    # ---------------------------------------------------------
    # 정제 순서 진행 (원본 보존 후 복사본 정제)
    # ---------------------------------------------------------
    df = raw_df.copy()
    logs = []

    # 1. 열 제목 축소
    original_cols_cnt = len(df.columns)
    new_cols = ['타임스탬프', '성별', '학년', '소속단과대학', 'AI사용시간', 'Q1', 'Q2', 'Q3', 'Q4', 'Q5', 'Q6', '서술형']

    if len(df.columns) == len(new_cols):
        df.columns = new_cols
        logs.append({"정제 단계": "1. 열 제목 변경", "내용": f"열 이름을 숏폼 형태({', '.join(new_cols[:5])}...)로 변경"})
    else:
        # 열 개수가 일치하지 않을 때 안전하게 변경
        cols_mapping = {df.columns[i]: new_cols[i] for i in range(min(len(df.columns), len(new_cols)))}
        df = df.rename(columns=cols_mapping)
        logs.append({"정제 단계": "1. 열 제목 변경", "내용": "일부 열 이름을 기본 표준명으로 변경"})

    # 2. 중복 제거 (타임스탬프 제외)
    non_timestamp_cols = [c for c in df.columns if c != '타임스탬프']
    before_dup = len(df)
    df = df.drop_duplicates(subset=non_timestamp_cols, keep='first')
    dup_removed = before_dup - len(df)
    logs.append({"정제 단계": "2. 중복 제거", "내용": f"타임스탬프 제외 동일 응답 {dup_removed}건 제거 (남은 행: {len(df)})"})

    # 3. 학년 표기 통일
    if '학년' in df.columns:
        df['학년'] = df['학년'].apply(parse_grade)
        logs.append({"정제 단계": "3. 학년 통일", "내용": "학년 표기를 숫자(1, 2, 3...) 형태로 통일"})

    # 4. 단과대학 분류
    if '소속단과대학' in df.columns:
        df['소속단과대학'] = df['소속단과대학'].apply(classify_college)
        logs.append({"정제 단계": "4. 단과대학 분류", "내용": "인문/사회과학/경제통상/경영/사범/기타 6개 범주로 재분류"})

    # 5. 이상치 처리 (AI사용시간)
    if 'AI사용시간' in df.columns:
        df['AI사용시간'] = df['AI사용시간'].apply(parse_ai_time)
        before_outlier = len(df)
        df = df[df['AI사용시간'] <= max_ai_hours]
        outlier_removed = before_outlier - len(df)
        logs.append({"정제 단계": "5. 이상치 처리", "내용": f"AI사용시간 {max_ai_hours}분 초과 데이터 {outlier_removed}건 제거"})

    # 6. 결측치 처리
    null_counts = df.isnull().sum().to_dict()
    null_info_str = ", ".join([f"{k}: {v}개" for k, v in null_counts.items() if v > 0])
    if not null_info_str:
        null_info_str = "결측치 없음"

    if na_option == "행 삭제":
        before_na = len(df)
        df = df.dropna()
        na_removed = before_na - len(df)
        logs.append({"정제 단계": "6. 결측치 처리 (행 삭제)", "내용": f"결측치 감지({null_info_str}) -> {na_removed}개 행 삭제 완료"})
    else:
        logs.append({"정제 단계": "6. 결측치 처리 (그대로 두기)", "내용": f"결측치 상태 유지 ({null_info_str})"})

    # 7. 점수 역산 (Q6R = 6 - Q6)
    if 'Q6' in df.columns:
        df['Q6'] = pd.to_numeric(df['Q6'], errors='coerce')
        df['Q6R'] = 6 - df['Q6']
        logs.append({"정제 단계": "7. 점수 역산", "내용": "Q6R = 6 - Q6 신규 역문항 컬럼 추가 계산"})

    # ---------------------------------------------------------
    # 결과 출력 및 카드/메트릭 표기
    # ---------------------------------------------------------
    st.subheader("📌 데이터 정제 요약 결과")

    card1, card2, card3 = st.columns(3)
    card1.metric("원본 데이터 행 수", f"{len(raw_df)} 행")
    card2.metric("최종 정제 데이터 행 수", f"{len(df)} 행", delta=f"{len(df) - len(raw_df)} 행")
    card3.metric("처리된 결측치 항목", f"{sum(null_counts.values())} 개")

    st.markdown("#### 📜 정제 작업 기록 (Log)")
    st.table(pd.DataFrame(logs))

    st.markdown("#### ✨ 최종 정제된 데이터")
    st.dataframe(df, use_container_width=True)

    # st.session_state 저장
    st.session_state["clean_df"] = df

    # CSV 다운로드 버튼
    csv_data = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 정제된 데이터 CSV 다운로드",
        data=csv_data,
        file_name="clean_survey_data.csv",
        mime="text/csv",
        type="primary"
    )

else:
    st.info("👆 상단의 파일 업로더를 통해 `survey_raw.csv` 파일을 등록해 주세요.")