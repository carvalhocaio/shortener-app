from http import HTTPStatus

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_create_url():
    response = client.post(
        "/url", json={"target_url": "https://www.example.com"}
    )
    assert response.status_code == HTTPStatus.OK

    data = response.json()
    assert data["target_url"] == "https://www.example.com"
    assert data["is_active"]
    assert data["clicks"] == 0
    assert "url" in data
    assert "admin_url" in data


def test_create_url_invalid():
    response = client.post("/url", json={"target_url": "not-a-valid-url"})

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "not valid" in response.json()["detail"]


def test_create_url_inaccessible():
    response = client.post(
        "/url", json={"target_url": "http://nonexistent.domain.abc"}
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "not accessible" in response.json()["detail"]


def test_forward_to_target_url_and_clicks():
    response_new_target_url = client.post(
        "/url", json={"target_url": "https://www.example.com"}
    )
    data = response_new_target_url.json()

    response = client.get(data["url"], allow_redirects=False)
    assert response.status_code in (
        HTTPStatus.TEMPORARY_REDIRECT,
        HTTPStatus.FOUND,
    )
    assert response.headers["location"] == "https://www.example.com"


def test_forward_to_target_url_not_found():
    response = client.get("/nonexistentkey", allow_redirects=False)
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "doesn't exist" in response.json()["detail"]


def test_get_url_info_and_delete():
    response = client.post(
        "/url", json={"target_url": "https://www.example.com"}
    )
    data = response.json()
    target_url = data["url"]
    admin_url = data["admin_url"]
    secret_key = admin_url.split("/")[-1]

    admin_path = admin_url.replace("http://testserver", "")
    response = client.get(admin_path)
    assert response.status_code == HTTPStatus.OK
    assert response.json()["target_url"] == "https://www.example.com"

    response = client.delete(f"/admin/{secret_key}")
    assert response.status_code == HTTPStatus.OK
    assert "Successfully deleted" in response.json()["detail"]

    response = client.get(target_url)
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_delete_url_not_found():
    response = client.delete("/admin/invalidsecretkey")
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_reactivate_url():
    response = client.post(
        "/url", json={"target_url": "https://www.example.com"}
    )
    data = response.json()
    secret_key = data["admin_url"].split("/")[-1]

    client.delete(f"/admin/{secret_key}")

    response = client.patch(f"/admin/{secret_key}/activate")
    assert response.status_code == HTTPStatus.OK
    assert "reactivated" in response.json()["detail"]


def test_reactivate_url_not_found():
    response = client.patch("/admin/invalidsecretkey/activate")
    assert response.status_code == HTTPStatus.NOT_FOUND
