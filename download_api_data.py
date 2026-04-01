import requests
import xml.etree.ElementTree as ET
import pandas as pd
import time

SERVICE_KEY = "37062a7e7c42deb34c615daa2614de121a420ddbed2a98fc7c24fce67c065303"
BASE_URL = "https://apis.data.go.kr/1471000/DURPrdlstInfoService03/getUsjntTabooInfoList03"

page = 1
num_of_rows = 100
all_items = []

while True:
    params = {
        "serviceKey": SERVICE_KEY,
        "pageNo": page,
        "numOfRows": num_of_rows,
        "type": "xml"
    }

    print(f"{page}페이지 요청 중...")
    response = requests.get(BASE_URL, params=params)

    if response.status_code != 200:
        print("요청 실패:", response.status_code)
        print(response.text[:1000])
        break

    try:
        root = ET.fromstring(response.content)
    except ET.ParseError:
        print("XML 파싱 실패")
        print(response.text[:1000])
        break

    page_items = root.findall(".//item")

    if not page_items:
        print("더 이상 데이터 없음")
        break

    for item in page_items:
        all_items.append({
            "drug1": item.findtext("INGR_KOR_NAME") or item.findtext("ingrKorName"),
            "drug2": item.findtext("MIXTURE_INGR_KOR_NAME") or item.findtext("mixtureIngrKorName"),
            "reason": item.findtext("PROHBT_CONTENT") or item.findtext("prohbtContent")
        })

    print("누적:", len(all_items))

    if len(page_items) < num_of_rows:
        break

    page += 1
    time.sleep(0.3)

print("총 데이터 수:", len(all_items))

if all_items:
    df = pd.DataFrame(all_items)
    df.to_csv("drug_interactions.csv", index=False, encoding="utf-8-sig")
    print("CSV 저장 완료: drug_interactions.csv")
else:
    print("데이터 없음")


