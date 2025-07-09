import os
import requests
import pandas as pd
import io
from fastapi import FastAPI, UploadFile, File, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="우체국 API 연동 서버",
    description="등기/택배 배송조회, 우편번호 자동화, 엑셀 대량조회까지 지원하는 FastAPI 서버",
    version="1.1.0"
)

# (1) 환경변수에서 우체국 API Key 불러오기
EPOST_KEY = os.environ.get("EPOST_KEY", "SERVICE_KEY_HERE")  # 실제 배포시 반드시 환경변수로!

# (2) CORS 허용 (프론트, GPT, 외부연동용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# (3) 루트 경로 (헬스체크)
@app.get("/")
def root():
    return {"status": "ok", "message": "우체국 API 연동 FastAPI 정상 작동 중"}

# (4) 단일 등기/택배 배송조회 (운송장번호 1개)
@app.get("/track")
def track(tracking_number: str = Query(..., description="운송장/등기번호")):
    url = (
        f"https://biz.epost.go.kr/KpostPortal/openapi?"
        f"regiNo={tracking_number}&target=regi&serviceKey={EPOST_KEY}"
    )
    try:
        res = requests.get(url, timeout=10)
        try:
            data = res.json()    # JSON 파싱 성공
        except Exception:
            data = {"raw_response": res.text}  # JSON 파싱 실패시 원본 반환
        return JSONResponse(content={
            "tracking_number": tracking_number,
            "url": url,
            "status_code": res.status_code,
            "result": data
        })
    except Exception as e:
        return JSONResponse(content={
            "error": str(e),
            "tracking_number": tracking_number,
            "url": url
        }, status_code=500)

# (5) 단일 주소 → 우편번호 변환
@app.get("/zipcode")
def zipcode(address: str = Query(..., description="주소(도로명/지번 등)")):
    url = (
        f"https://biz.epost.go.kr/KpostPortal/openapi?"
        f"searchSe=road&srchwrd={address}&serviceKey={EPOST_KEY}"
    )
    try:
        res = requests.get(url, timeout=10)
        try:
            data = res.json()
        except Exception:
            data = {"raw_response": res.text}
        return JSONResponse(content={
            "address": address,
            "url": url,
            "status_code": res.status_code,
            "result": data
        })
    except Exception as e:
        return JSONResponse(content={
            "error": str(e),
            "address": address,
            "url": url
        }, status_code=500)

# (6) 엑셀 업로드 → 등기번호 대량조회
@app.post("/track_bulk")
async def track_bulk(file: UploadFile = File(...)):
    results = []
    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        if 'tracking_number' not in df.columns:
            return JSONResponse(
                content={"error": "'tracking_number' 컬럼이 필요합니다."}, status_code=400
            )
        for tr in df['tracking_number'].astype(str):
            url = (
                f"https://biz.epost.go.kr/KpostPortal/openapi?"
                f"regiNo={tr}&serviceKey={EPOST_KEY}"
            )
            try:
                res = requests.get(url, timeout=10)
                try:
                    data = res.json()
                except Exception:
                    data = {"raw_response": res.text}
                results.append({
                    "tracking_number": tr,
                    "status_code": res.status_code,
                    "result": data
                })
            except Exception as e:
                results.append({
                    "tracking_number": tr,
                    "error": str(e)
                })
        return JSONResponse(content={"results": results})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
