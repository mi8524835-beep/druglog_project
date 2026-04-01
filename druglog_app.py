import streamlit as st
import pandas as pd
import json
import os
from datetime import date

st.set_page_config(page_title="DrugLog", page_icon="💊", layout="wide")

INTERACTION_FILE = "drug_interactions.csv"
AGE_FILE = "age_restriction.csv"
PREGNANCY_FILE = "pregnancy_restriction.csv"
ELDERLY_FILE = "elderly_caution.csv"
ELDERLY_NSAID_FILE = "elderly_caution_nsaid.csv"
USER_DB_FILE = "user_meds_db.json"

PLACEHOLDER_NO_INPUT = "검색어를 먼저 입력하세요"
PLACEHOLDER_NO_RESULT = "검색 결과 없음"


@st.cache_data
def load_csv(file_path):
    return pd.read_csv(file_path, encoding="cp949", low_memory=False)


interaction_df = load_csv(INTERACTION_FILE)
age_df = load_csv(AGE_FILE)
pregnancy_df = load_csv(PREGNANCY_FILE)
elderly_df = pd.concat(
    [
        load_csv(ELDERLY_FILE),
        load_csv(ELDERLY_NSAID_FILE),
    ],
    ignore_index=True,
).drop_duplicates()


def load_user_db():
    if os.path.exists(USER_DB_FILE):
        try:
            with open(USER_DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            return {}
    return {}


def save_user_db(db):
    with open(USER_DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


def normalize_text(text):
    return str(text).strip()


def safe_contains(series, keyword):
    keyword = normalize_text(keyword)
    return series.astype(str).str.contains(keyword, case=False, na=False)


def get_candidate_names():
    names = set()

    for df in [interaction_df, age_df, pregnancy_df, elderly_df]:
        for col in ["성분명", "성분명A", "성분명B", "제품명", "제품명A", "제품명B"]:
            if col in df.columns:
                values = df[col].dropna().astype(str).str.strip().tolist()
                names.update([v for v in values if v])

    return sorted(names)


candidate_names = get_candidate_names()


def filter_candidates(keyword, limit=100):
    keyword = normalize_text(keyword).lower()

    if not keyword:
        return [PLACEHOLDER_NO_INPUT]

    filtered = [name for name in candidate_names if keyword in name.lower()]

    if not filtered:
        return [PLACEHOLDER_NO_RESULT]

    return filtered[:limit]


def is_valid_selection(value):
    return value not in [PLACEHOLDER_NO_INPUT, PLACEHOLDER_NO_RESULT]


def check_interaction(drug1, drug2):
    drug1 = normalize_text(drug1)
    drug2 = normalize_text(drug2)

    if not drug1 or not drug2:
        return pd.DataFrame()

    conditions = []

    if "성분명A" in interaction_df.columns and "성분명B" in interaction_df.columns:
        conditions.append(
            safe_contains(interaction_df["성분명A"], drug1)
            & safe_contains(interaction_df["성분명B"], drug2)
        )
        conditions.append(
            safe_contains(interaction_df["성분명A"], drug2)
            & safe_contains(interaction_df["성분명B"], drug1)
        )

    if "제품명A" in interaction_df.columns and "제품명B" in interaction_df.columns:
        conditions.append(
            safe_contains(interaction_df["제품명A"], drug1)
            & safe_contains(interaction_df["제품명B"], drug2)
        )
        conditions.append(
            safe_contains(interaction_df["제품명A"], drug2)
            & safe_contains(interaction_df["제품명B"], drug1)
        )

        if "성분명A" in interaction_df.columns:
            conditions.append(
                safe_contains(interaction_df["성분명A"], drug1)
                & safe_contains(interaction_df["제품명B"], drug2)
            )
            conditions.append(
                safe_contains(interaction_df["성분명A"], drug2)
                & safe_contains(interaction_df["제품명B"], drug1)
            )

        if "성분명B" in interaction_df.columns:
            conditions.append(
                safe_contains(interaction_df["제품명A"], drug1)
                & safe_contains(interaction_df["성분명B"], drug2)
            )
            conditions.append(
                safe_contains(interaction_df["제품명A"], drug2)
                & safe_contains(interaction_df["성분명B"], drug1)
            )

    if not conditions:
        return pd.DataFrame()

    final_cond = conditions[0]
    for cond in conditions[1:]:
        final_cond = final_cond | cond

    return interaction_df[final_cond].drop_duplicates()


def find_single_drug_matches(df, drug):
    drug = normalize_text(drug)

    if not drug:
        return pd.DataFrame()

    conditions = []
    for col in ["성분명", "성분명A", "성분명B", "제품명", "제품명A", "제품명B"]:
        if col in df.columns:
            conditions.append(safe_contains(df[col], drug))

    if not conditions:
        return pd.DataFrame()

    final_cond = conditions[0]
    for cond in conditions[1:]:
        final_cond = final_cond | cond

    return df[final_cond].drop_duplicates()


def create_empty_profile(db, profile_name):
    db[profile_name] = {"meds": []}
    save_user_db(db)


def get_profile_meds(db, profile_name):
    if profile_name in db:
        return db[profile_name].get("meds", [])
    return []


def save_profile_meds(db, profile_name, meds):
    if profile_name not in db:
        db[profile_name] = {"meds": []}
    db[profile_name]["meds"] = meds
    save_user_db(db)


def med_exists(meds, med_name):
    med_name = normalize_text(med_name).lower()
    for med in meds:
        if normalize_text(med.get("name", "")).lower() == med_name:
            return True
    return False


def meds_to_dataframe(meds):
    rows = []
    for med in meds:
        rows.append(
            {
                "약 이름": med.get("name", ""),
                "복용 시작일": med.get("start_date", ""),
                "1회 용량": med.get("dose", ""),
                "1일 횟수": med.get("frequency", ""),
                "메모": med.get("memo", ""),
            }
        )
    return pd.DataFrame(rows)


def show_card(title, body, kind="info"):
    colors = {
        "danger": ("#7f1d1d", "#fee2e2", "#b91c1c"),
        "warning": ("#78350f", "#fef3c7", "#d97706"),
        "info": ("#1e3a8a", "#dbeafe", "#2563eb"),
        "success": ("#14532d", "#dcfce7", "#16a34a"),
    }

    text_color, bg_color, border_color = colors.get(kind, colors["info"])

    st.markdown(
        f"""
        <div style="
            background-color:{bg_color};
            border-left:8px solid {border_color};
            padding:16px;
            border-radius:12px;
            margin:10px 0 16px 0;
        ">
            <div style="font-size:20px; font-weight:700; color:{text_color}; margin-bottom:8px;">
                {title}
            </div>
            <div style="font-size:15px; color:#222;">
                {body}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_metric_cards(danger_count, warning_count, info_count, success_count):
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(
            f"""
            <div style="
                background:#fee2e2;
                border:1px solid #fecaca;
                border-radius:16px;
                padding:18px;
                text-align:center;
            ">
                <div style="font-size:14px; color:#991b1b;">위험</div>
                <div style="font-size:32px; font-weight:700; color:#b91c1c;">{danger_count}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
            <div style="
                background:#fef3c7;
                border:1px solid #fde68a;
                border-radius:16px;
                padding:18px;
                text-align:center;
            ">
                <div style="font-size:14px; color:#92400e;">주의</div>
                <div style="font-size:32px; font-weight:700; color:#d97706;">{warning_count}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            f"""
            <div style="
                background:#dbeafe;
                border:1px solid #bfdbfe;
                border-radius:16px;
                padding:18px;
                text-align:center;
            ">
                <div style="font-size:14px; color:#1e40af;">참고</div>
                <div style="font-size:32px; font-weight:700; color:#2563eb;">{info_count}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col4:
        st.markdown(
            f"""
            <div style="
                background:#dcfce7;
                border:1px solid #bbf7d0;
                border-radius:16px;
                padding:18px;
                text-align:center;
            ">
                <div style="font-size:14px; color:#166534;">정상</div>
                <div style="font-size:32px; font-weight:700; color:#16a34a;">{success_count}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


db = load_user_db()
if not db:
    create_empty_profile(db, "기본 사용자")
    db = load_user_db()

st.markdown(
    """
    <div style="padding: 8px 0 16px 0;">
        <h1 style="margin-bottom: 0.2rem;">💊 DrugLog</h1>
        <p style="font-size: 17px; color: #555;">
            복용약 저장, 병용금기 확인, 연령/임부/노인주의 종합 분석을 한 화면에서 할 수 있어요.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.title("👤 프로필 관리")
profile_names = list(db.keys())
selected_profile = st.sidebar.selectbox("프로필 선택", profile_names)

new_profile_name = st.sidebar.text_input("새 프로필 이름")
if st.sidebar.button("프로필 추가"):
    new_profile_name = normalize_text(new_profile_name)
    if not new_profile_name:
        st.sidebar.warning("프로필 이름을 입력해주세요.")
    elif new_profile_name in db:
        st.sidebar.info("이미 존재하는 프로필입니다.")
    else:
        create_empty_profile(db, new_profile_name)
        st.sidebar.success(f"'{new_profile_name}' 생성 완료")
        st.rerun()

if st.sidebar.button("현재 프로필 삭제"):
    if len(db) == 1:
        st.sidebar.warning("최소 1개의 프로필은 필요합니다.")
    else:
        del db[selected_profile]
        save_user_db(db)
        st.rerun()

my_meds = get_profile_meds(db, selected_profile)

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "약 2개 직접 검색",
        "복용약 저장/관리",
        "복용약 전체 점검",
        "데이터 내보내기",
        "종합 위험 분석",
    ]
)

with tab1:
    st.subheader("약 2개 직접 검색")

    col1, col2 = st.columns(2)

    with col1:
        keyword1 = st.text_input("첫 번째 약 검색어", key="keyword1")
        options1 = filter_candidates(keyword1)
        if is_valid_selection(options1[0]):
            st.caption(f"검색 결과: {len(options1)}개")
        drug1 = st.selectbox("첫 번째 약 선택", options1, key="drug1_select")

    with col2:
        keyword2 = st.text_input("두 번째 약 검색어", key="keyword2")
        options2 = filter_candidates(keyword2)
        if is_valid_selection(options2[0]):
            st.caption(f"검색 결과: {len(options2)}개")
        drug2 = st.selectbox("두 번째 약 선택", options2, key="drug2_select")

    st.divider()

    # 자동 결과 표시
    if not is_valid_selection(drug1) or not is_valid_selection(drug2):
        st.info("두 약의 검색어를 입력하고 각각 선택하면 결과가 자동으로 표시됩니다.")
    elif drug1 == drug2:
        st.warning("같은 약을 두 번 선택할 수 없습니다.")
    else:
        result = check_interaction(drug1, drug2)

        if not result.empty:
            show_card(
                "⚠️ 병용금기",
                f"<b>{drug1}</b> 와(과) <b>{drug2}</b> 사이에 병용금기 정보가 발견되었습니다.",
                kind="danger",
            )
            cols = [c for c in ["성분명A", "제품명A", "성분명B", "제품명B", "상세정보"] if c in result.columns]
            st.dataframe(result[cols], use_container_width=True)
        else:
            show_card(
                "✅ 안전",
                f"<b>{drug1}</b> 와(과) <b>{drug2}</b> 조합은 현재 데이터 기준 병용금기 정보가 발견되지 않았습니다.",
                kind="success",
            )

with tab2:
    st.subheader(f"'{selected_profile}' 복용약 저장")

    col1, col2 = st.columns(2)

    with col1:
        keyword3 = st.text_input("복용약 검색어", key="keyword3")
        options3 = filter_candidates(keyword3)
        new_med_name = st.selectbox("복용약 선택", options3, key="new_med_name_select")
        new_med_start = st.date_input("복용 시작일", value=date.today(), key="new_med_start")
        new_med_dose = st.text_input("1회 용량", placeholder="예: 1정 / 500mg", key="new_med_dose")

    with col2:
        new_med_frequency = st.text_input("1일 횟수", placeholder="예: 하루 2번", key="new_med_frequency")
        new_med_memo = st.text_area("메모", placeholder="예: 식후 복용", key="new_med_memo")

    if st.button("복용약 저장"):
        med_name = normalize_text(new_med_name)

        if not is_valid_selection(med_name):
            st.warning("검색어를 입력하고 저장할 약을 선택해주세요.")
        elif med_exists(my_meds, med_name):
            st.info("이미 저장된 약입니다.")
        else:
            new_item = {
                "name": med_name,
                "start_date": str(new_med_start),
                "dose": normalize_text(new_med_dose),
                "frequency": normalize_text(new_med_frequency),
                "memo": normalize_text(new_med_memo),
            }

            warning_results = []
            for saved in my_meds:
                result = check_interaction(med_name, saved["name"])
                if not result.empty:
                    warning_results.append((saved["name"], result))

            my_meds.append(new_item)
            save_profile_meds(db, selected_profile, my_meds)

            show_card(
                "✅ 저장 완료",
                f"<b>{med_name}</b> 이(가) 복용약 목록에 저장되었습니다.",
                kind="success",
            )

            if warning_results:
                show_card(
                    "⚠️ 주의 필요",
                    "새로 저장한 약이 기존 복용약과 병용금기일 수 있습니다.",
                    kind="warning",
                )
                for existing_name, result in warning_results:
                    st.markdown(f"**{med_name} ↔ {existing_name}**")
                    cols = [c for c in ["성분명A", "제품명A", "성분명B", "제품명B", "상세정보"] if c in result.columns]
                    st.dataframe(result[cols], use_container_width=True)

    st.divider()
    st.subheader("현재 저장된 복용약")

    if my_meds:
        st.dataframe(meds_to_dataframe(my_meds), use_container_width=True)

        for idx, med in enumerate(my_meds):
            with st.expander(f"{med['name']} 관리"):
                edit_keyword = st.text_input("수정할 약 검색어", value=med.get("name", ""), key=f"edit_keyword_{idx}")
                edit_options = filter_candidates(edit_keyword)
                default_index = 0
                if med.get("name", "") in edit_options:
                    default_index = edit_options.index(med.get("name", ""))

                edit_name = st.selectbox("약 이름", edit_options, index=default_index, key=f"edit_name_{idx}")
                edit_start = st.text_input("복용 시작일", value=med.get("start_date", ""), key=f"edit_start_{idx}")
                edit_dose = st.text_input("1회 용량", value=med.get("dose", ""), key=f"edit_dose_{idx}")
                edit_freq = st.text_input("1일 횟수", value=med.get("frequency", ""), key=f"edit_freq_{idx}")
                edit_memo = st.text_area("메모", value=med.get("memo", ""), key=f"edit_memo_{idx}")

                c1, c2 = st.columns(2)

                with c1:
                    if st.button("수정 저장", key=f"save_{idx}"):
                        if not is_valid_selection(edit_name):
                            st.warning("수정할 약을 올바르게 선택해주세요.")
                        else:
                            my_meds[idx] = {
                                "name": normalize_text(edit_name),
                                "start_date": normalize_text(edit_start),
                                "dose": normalize_text(edit_dose),
                                "frequency": normalize_text(edit_freq),
                                "memo": normalize_text(edit_memo),
                            }
                            save_profile_meds(db, selected_profile, my_meds)
                            st.success("수정 완료")
                            st.rerun()

                with c2:
                    if st.button("삭제", key=f"delete_{idx}"):
                        my_meds.pop(idx)
                        save_profile_meds(db, selected_profile, my_meds)
                        st.success("삭제 완료")
                        st.rerun()

        if st.button("복용약 전체 삭제"):
            save_profile_meds(db, selected_profile, [])
            st.success("전체 삭제 완료")
            st.rerun()
    else:
        show_card(
            "ℹ️ 저장된 복용약 없음",
            "아직 저장된 복용약이 없습니다.",
            kind="info",
        )

with tab3:
    st.subheader("복용약 전체 점검")

    if len(my_meds) < 2:
        show_card(
            "ℹ️ 복용약 부족",
            "복용약을 2개 이상 저장하면 전체 점검이 가능합니다.",
            kind="info",
        )
    else:
        found = False

        for i in range(len(my_meds)):
            for j in range(i + 1, len(my_meds)):
                med_a = my_meds[i]["name"]
                med_b = my_meds[j]["name"]
                result = check_interaction(med_a, med_b)

                if not result.empty:
                    found = True
                    show_card(
                        "⚠️ 병용금기 가능",
                        f"<b>{med_a}</b> + <b>{med_b}</b> 조합에서 위험 정보가 발견되었습니다.",
                        kind="danger",
                    )
                    cols = [c for c in ["성분명A", "제품명A", "성분명B", "제품명B", "상세정보"] if c in result.columns]
                    st.dataframe(result[cols], use_container_width=True)

        if not found:
            show_card(
                "✅ 전체 점검 완료",
                "저장된 복용약들 사이에서 병용금기 정보가 발견되지 않았습니다.",
                kind="success",
            )

with tab4:
    st.subheader("데이터 내보내기")

    meds_df = meds_to_dataframe(my_meds)
    if not meds_df.empty:
        csv_data = meds_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "복용약 목록 CSV 다운로드",
            data=csv_data,
            file_name=f"{selected_profile}_복용약목록.csv",
            mime="text/csv",
        )

        json_data = json.dumps(my_meds, ensure_ascii=False, indent=2).encode("utf-8")
        st.download_button(
            "복용약 목록 JSON 다운로드",
            data=json_data,
            file_name=f"{selected_profile}_복용약목록.json",
            mime="application/json",
        )
    else:
        show_card(
            "ℹ️ 내보낼 데이터 없음",
            "다운로드할 복용약 데이터가 없습니다.",
            kind="info",
        )

with tab5:
    st.subheader("종합 위험 분석")

    keyword4 = st.text_input("분석할 약 검색어", key="keyword4")
    options4 = filter_candidates(keyword4)
    target_drug = st.selectbox("분석할 약 선택", options4, key="target_drug_select")

    age_input = st.number_input("나이", min_value=0, max_value=120, value=65, step=1)
    is_pregnant = st.checkbox("임신 중 또는 임신 가능성 있음")

    if st.button("종합 분석 시작"):
        if not is_valid_selection(target_drug):
            st.warning("검색어를 입력하고 분석할 약을 선택해주세요.")
        else:
            found_any = False
            danger_count = 0
            warning_count = 0
            info_count = 0
            success_count = 0

            age_result = find_single_drug_matches(age_df, target_drug)
            pregnancy_result = find_single_drug_matches(pregnancy_df, target_drug)
            elderly_result = find_single_drug_matches(elderly_df, target_drug)

            interaction_results = []
            if my_meds:
                for med in my_meds:
                    result = check_interaction(target_drug, med["name"])
                    if not result.empty:
                        interaction_results.append((med["name"], result))

            if not age_result.empty:
                found_any = True
                if age_input >= 65:
                    danger_count += 1
                else:
                    info_count += 1

            if not pregnancy_result.empty:
                found_any = True
                if is_pregnant:
                    danger_count += 1
                else:
                    info_count += 1

            if not elderly_result.empty:
                found_any = True
                if age_input >= 65:
                    warning_count += 1
                else:
                    info_count += 1

            if interaction_results:
                found_any = True
                danger_count += len(interaction_results)

            if not found_any:
                success_count = 1

            show_metric_cards(danger_count, warning_count, info_count, success_count)
            st.markdown("### 분석 결과")

            if not age_result.empty:
                if age_input < 65:
                    show_card(
                        "ℹ️ 연령 관련 주의",
                        f"<b>{target_drug}</b> 에 대한 연령 관련 정보가 있습니다. 현재 입력 나이는 65세 미만입니다.",
                        kind="info",
                    )
                else:
                    show_card(
                        "⚠️ 연령금기 / 고령자 주의",
                        f"<b>{target_drug}</b> 은(는) 고령자에게 주의가 필요할 수 있습니다.",
                        kind="danger",
                    )
                st.dataframe(age_result, use_container_width=True)

            if not pregnancy_result.empty:
                if is_pregnant:
                    show_card(
                        "⚠️ 임부금기",
                        f"<b>{target_drug}</b> 은(는) 임신 중 주의가 필요합니다.",
                        kind="danger",
                    )
                else:
                    show_card(
                        "ℹ️ 임부 관련 정보",
                        f"<b>{target_drug}</b> 에 대한 임부금기 데이터가 있습니다.",
                        kind="info",
                    )
                st.dataframe(pregnancy_result, use_container_width=True)

            if not elderly_result.empty:
                if age_input >= 65:
                    show_card(
                        "⚠️ 노인주의",
                        f"<b>{target_drug}</b> 은(는) 65세 이상에서 주의가 필요할 수 있습니다.",
                        kind="warning",
                    )
                else:
                    show_card(
                        "ℹ️ 노인주의 정보",
                        f"<b>{target_drug}</b> 에 대한 노인주의 데이터가 있습니다.",
                        kind="info",
                    )
                st.dataframe(elderly_result, use_container_width=True)

            if interaction_results:
                show_card(
                    "⚠️ 복용 중인 약과 충돌 가능",
                    f"<b>{target_drug}</b> 이(가) 현재 저장된 복용약과 병용금기일 수 있습니다.",
                    kind="danger",
                )

                for med_name, result in interaction_results:
                    st.markdown(f"**{target_drug} ↔ {med_name}**")
                    cols = [c for c in ["성분명A", "제품명A", "성분명B", "제품명B", "상세정보"] if c in result.columns]
                    st.dataframe(result[cols], use_container_width=True)

            if not found_any:
                show_card(
                    "✅ 특이사항 없음",
                    f"<b>{target_drug}</b> 에 대해 현재 조건에서 특별한 위험 정보가 발견되지 않았습니다.",
                    kind="success",
                )