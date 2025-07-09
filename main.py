# main.py (epostapi 용)
import os
import requests
import pandas as pd
from fastapi import FastAPI, UploadFile, File, Query
from fastapi.responses import JSONResponse

app = FastAPI(
    title="우체국 API 연동 서버",
    description="등기/택배 배송조회 & 우편번호 자동화 API (for Render.com)",
    version="1.0.0"
)

# Render 환경변수에서 API KEY 불러오기
EPOST_KEY = os.environ.get("EPOST_KEY", "SERVICE_KEY_HERE")  # 꼭 환경변수로 등록!

@app.get("/")
def root():
    return {"status": "ok", "message": "우체국 API 연동 FastAPI on Render.com"}

# 1) 단일 등기/택배 배송조회 (운송장번호 1개)
@app.get("/track")
def track(tracking_number: str = Query(..., description="운송장/등기번호")):
    url = (
        f"https://biz.epost.go.kr/KpostPortal/openapi?"
        f"regiNo={tracking_number}&serviceKey={EPOST_KEY}"
    )
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        data = res.json()
        return JSONResponse(content=data)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

# 2) 단일 주소 → 우편번호 변환
@app.get("/zipcode")
def zipcode(address: str = Query(..., description="주소(도로명/지번 등)")):
    url = (
        f"https://biz.epost.go.kr/KpostPortal/openapi?"
        f"searchSe=road&srchwrd={address}&serviceKey={EPOST_KEY}"
    )
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        data = res.json()
        return JSONResponse(content=data)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

# 3) 엑셀 업로드 → 등기번호 대량조회
@app.post("/track_bulk")
async def track_bulk(file: UploadFile = File(...)):
    try:
        df = pd.read_excel(file.file)
        if 'tracking_number' not in df.columns:
            return JSONResponse(
                content={"error": "'tracking_number' 컬럼이 필요합니다."}, status_code=400
            )

        def get_status(tr_num):
            url = (
                f"https://biz.epost.go.kr/KpostPortal/openapi?"
                f"regiNo={tr_num}&serviceKey={EPOST_KEY}"
            )
            try:
                resp = requests.get(url, timeout=10)
                resp.raise_for_status()
                return resp.json().get('status', '오류')
            except Exception:
                return "조회오류"

        df['status'] = df['tracking_number'].astype(str).apply(get_status)
        result = df.to_dict(orient="records")
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
