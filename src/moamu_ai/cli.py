import uvicorn


def main() -> None:
    """로컬 개발용 FastAPI 서버를 실행한다."""
    uvicorn.run("moamu_ai.app:app", host="127.0.0.1", port=8000, reload=False)
