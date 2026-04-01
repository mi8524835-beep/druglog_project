import pandas as pd

df = pd.read_csv("drug_interactions.csv", encoding="cp949", low_memory=False)

drug1 = input("첫 번째 약 입력: ")
drug2 = input("두 번째 약 입력: ")

result = df[
    (
        (df["성분명A"].str.contains(drug1, na=False) &
         df["성분명B"].str.contains(drug2, na=False))
    ) |
    (
        (df["성분명A"].str.contains(drug2, na=False) &
         df["성분명B"].str.contains(drug1, na=False))
    )
]

if not result.empty:
    print("⚠️ 병용금기입니다!")
    print(result[["성분명A", "성분명B", "상세정보"]].head())
else:
    print("병용금기 없음")