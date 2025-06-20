from http import HTTPStatus

import httpx
import validators
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from starlette.datastructures import URL

import crud
import models
import schemas
from config import get_settings
from database import SessionLocal, engine

app = FastAPI()
models.Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_admin_info(db_url: models.URL) -> schemas.URLInfo:
    base_url = URL(get_settings().base_url)
    admin_endpoint = app.url_path_for(
        "administration info", secret_key=db_url.secret_key
    )

    return schemas.URLInfo(
        target_url=db_url.target_url,
        key=db_url.key,
        secret_key=db_url.secret_key,
        is_active=db_url.is_active,
        clicks=db_url.clicks,
        url=str(base_url.replace(path=db_url.key)),
        admin_url=str(base_url.replace(path=admin_endpoint)),
    )


def raise_bad_request(message):
    raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=message)


def raise_not_found(request):
    message = f"URL: {request.url} doesn't exist"
    raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=message)


@app.get("/")
def read_root():
    return "Welcome to the URL shortener API :)"


@app.post("/url", response_model=schemas.URLInfo)
async def create_url(url: schemas.URLBase, db: Session = Depends(get_db)):
    if not validators.url(url.target_url):
        raise_bad_request(message="Your provided URL is not valid")

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(url.target_url, follow_redirects=True)
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=(
                    "Target website is not accessible "
                    f"(status code {response.status_code})."
                ),
            )
    except httpx.RequestError:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Target website is not accessible",
        )

    try:
        db_url = crud.create_db_url(db=db, url=url)
    except ValueError as e:
        raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=str(e))

    return get_admin_info(db_url)


@app.get("/{url_key}")
def forward_to_target_url(
    url_key: str,
    request: Request,
    db: Session = Depends(get_db),
):
    if db_url := crud.get_db_url_by_key(db=db, url_key=url_key):
        crud.update_db_clicks(db=db, db_url=db_url)
        return RedirectResponse(db_url.target_url)
    else:
        raise_not_found(request)


@app.get(
    "/admin/{secret_key}",
    name="administration info",
    response_model=schemas.URLInfo,
)
def get_url_info(
    secret_key: str, request: Request, db: Session = Depends(get_db)
):
    if db_url := crud.get_db_url_by_secret_key(db, secret_key=secret_key):
        return get_admin_info(db_url)
    else:
        raise_not_found(request)


@app.patch("/admin/{secret_key}/activate")
def reactivate_url(secret_key: str, db: Session = Depends(get_db)):
    db_url = crud.get_db_url_by_secret_key(db, secret_key=secret_key)
    if db_url:
        db_url.is_active = True
        db.commit()
        db.refresh(db_url)
        return {"detail": "URL reactivated successfully"}
    else:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="URL not found"
        )


@app.delete("/admin/{secret_key}")
def delete_url(
    secret_key: str, request: Request, db: Session = Depends(get_db)
):
    if db_url := crud.deactivate_db_url_by_secret_key(
        db, secret_key=secret_key
    ):
        message = (
            f"Successfully deleted shortened URL for '{db_url.target_url}'"
        )
        return {"detail": message}
    else:
        raise_not_found(request)
