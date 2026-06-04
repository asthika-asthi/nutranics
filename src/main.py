from fastapi import FastAPI

app = FastAPI(title="Wellness Clinic API", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok"}
