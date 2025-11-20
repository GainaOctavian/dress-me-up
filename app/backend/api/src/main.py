import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from app.backend.api.src.routes import user

app = FastAPI(
    title="Dress Me Up API",
    version="1.0.0"
)

app.include_router(user.router)


@app.get("/", include_in_schema=False)
def redirect_to_docs():
    return RedirectResponse("/docs")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
