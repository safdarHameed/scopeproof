from httpx import AsyncClient

API = "/api/v1"
USER = {"email": "Ada@Example.com", "password": "s3cure-pass", "full_name": "Ada"}


async def register(client: AsyncClient) -> None:
    r = await client.post(f"{API}/auth/register", json=USER)
    assert r.status_code == 201, r.text


async def login(client: AsyncClient, password: str = USER["password"]):
    return await client.post(
        f"{API}/auth/login", data={"username": USER["email"], "password": password}
    )


async def test_register_login_me(client: AsyncClient) -> None:
    await register(client)
    r = await login(client)
    assert r.status_code == 200
    token = r.json()["access_token"]

    r = await client.get(f"{API}/users/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "ada@example.com"
    assert "hashed_password" not in r.json()


async def test_duplicate_email_rejected(client: AsyncClient) -> None:
    await register(client)
    r = await client.post(f"{API}/auth/register", json={**USER, "email": "ada@example.com"})
    assert r.status_code == 409


async def test_wrong_password(client: AsyncClient) -> None:
    await register(client)
    r = await login(client, password="wrong-password")
    assert r.status_code == 401


async def test_me_requires_token(client: AsyncClient) -> None:
    r = await client.get(f"{API}/users/me")
    assert r.status_code == 401
    r = await client.get(f"{API}/users/me", headers={"Authorization": "Bearer garbage"})
    assert r.status_code == 401
