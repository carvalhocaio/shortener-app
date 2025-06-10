from http import HTTPStatus

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

CLICKS_E2E = 2


def test_e2e_full_flow():
    # 1. Check main route
    response = client.get("/")
    assert response.status_code == HTTPStatus.OK
    assert "Welcome" in response.text

    # 2. Create a URL
    response = client.post(
        "/url", json={"target_url": "https://www.example.com"}
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    admin_url = data["admin_url"]
    target_url = data["url"]
    secret_key = admin_url.split("/")[-1]

    # 3. Access admin (must have 0 clicks)
    admin_path = admin_url.replace("http://testserver", "")
    response = client.get(admin_path)
    assert response.status_code == HTTPStatus.OK
    assert response.json()["clicks"] == 0

    # 4. Access url_target (should redirect)
    response = client.get(target_url, allow_redirects=False)
    assert response.status_code in (
        HTTPStatus.TEMPORARY_REDIRECT,
        HTTPStatus.FOUND,
    )
    assert response.headers["location"] == "https://www.example.com"

    # 5. Access admin again (must be 1 click)
    response = client.get(admin_path)
    assert response.status_code == HTTPStatus.OK
    assert response.json()["clicks"] == 1

    # 6. Disable target_url
    response = client.delete(f"/admin/{secret_key}")
    assert response.status_code == HTTPStatus.OK

    # 7. Try to access target_url (should return 404)
    response = client.get(target_url, allow_redirects=False)
    assert response.status_code == HTTPStatus.NOT_FOUND

    # 8. Reactivates target_url
    response = client.patch(f"/admin/{secret_key}/activate")
    assert response.status_code == HTTPStatus.OK

    # 9. Access target_url again (should redirect)
    response = client.get(target_url, allow_redirects=False)
    assert response.status_code in (
        HTTPStatus.TEMPORARY_REDIRECT,
        HTTPStatus.FOUND,
    )
    assert response.headers["location"] == "https://www.example.com"

    # 10. Access admin to validate counter (must be 2)
    response = client.get(admin_path)
    assert response.status_code == HTTPStatus.OK
    assert response.json()["clicks"] == CLICKS_E2E
