import pandas as pd

df = pd.read_csv("의약품안전사용서비스(DUR)_노인주의 품목리스트 2025.6.csv", encoding="cp949")  # 또는 utf-8-sig

print(df.head())
print(df.columns)
