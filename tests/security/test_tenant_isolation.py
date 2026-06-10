import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_tenant_a_cannot_access_tenant_b_vendor(client: AsyncClient):
    """
    Core security test.
    Vendor created by Tenant A must return 404 when
    requested by Tenant B — not a 403 (which would confirm existence).
    """
    # Register Tenant A
    resp_a = await client.post("/api/v1/auth/register", json={
        "tenant_name": "Tenant A",
        "tenant_domain": "tenant-a-test.com",
        "admin_email": "admin@tenant-a-test.com",
        "admin_password": "SecurePass123!",
        "admin_first_name": "Admin", "admin_last_name": "A",
    })
    assert resp_a.status_code == 201

    login_a = await client.post("/api/v1/auth/login", json={
        "email": "admin@tenant-a-test.com", "password": "SecurePass123!"
    })
    token_a = login_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Register Tenant B
    await client.post("/api/v1/auth/register", json={
        "tenant_name": "Tenant B",
        "tenant_domain": "tenant-b-test.com",
        "admin_email": "admin@tenant-b-test.com",
        "admin_password": "SecurePass123!",
        "admin_first_name": "Admin", "admin_last_name": "B",
    })
    login_b = await client.post("/api/v1/auth/login", json={
        "email": "admin@tenant-b-test.com", "password": "SecurePass123!"
    })
    token_b = login_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Tenant A creates a vendor
    vendor_resp = await client.post("/api/v1/vendors", json={
        "legal_name": "Secret Vendor",
        "domain": "secret-vendor.com",
    }, headers=headers_a)
    vendor_id = vendor_resp.json()["id"]

    # Tenant B tries to access Tenant A's vendor — must get 404
    isolation_resp = await client.get(
        f"/api/v1/vendors/{vendor_id}", headers=headers_b
    )
    assert isolation_resp.status_code == 404, (
        "CRITICAL: Cross-tenant data leak detected!"
    )