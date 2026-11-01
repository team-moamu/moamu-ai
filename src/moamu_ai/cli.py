import uvicorn


def main() -> None:
    uvicorn.run("moamu_ai.app:app", host="127.0.0.1", port=8000, reload=False)
