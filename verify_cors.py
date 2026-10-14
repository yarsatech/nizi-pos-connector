import requests

BASE_URL = "http://127.0.0.1:9121"

def test_cors_allowlist_blocking():
    print("Testing CORS rejection for unauthorized origin (https://malicious-site.com)...")
    headers = {
        "Origin": "https://malicious-site.com",
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "X-API-Key"
    }
    response = requests.options(f"{BASE_URL}/api/status", headers=headers)
    print(f"Status Code: {response.status_code}")
    assert response.status_code == 403, f"Expected 403 Forbidden, got {response.status_code}"
    print("✅ Disallowed origin correctly rejected!")

def test_cors_allowlist_permitting():
    print("Testing CORS acceptance for approved banking origin (https://nagarik.gibl.com.np)...")
    approved_origin = "https://nagarik.gibl.com.np"
    headers = {
        "Origin": approved_origin,
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "X-API-Key"
    }
    response = requests.options(f"{BASE_URL}/api/status", headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Allow-Origin: {response.headers.get('Access-Control-Allow-Origin')}")
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
    assert response.headers.get("Access-Control-Allow-Origin") == approved_origin
    print("✅ Approved banking origin correctly allowed!")

def test_unauthorized_get():
    print("\nTesting Unauthorized GET /api/status (should return 401)...")
    response = requests.get(f"{BASE_URL}/api/status")
    print(f"Status Code: {response.status_code}")
    assert response.status_code == 401
    print("✅ Unauthorized GET test passed!")

if __name__ == "__main__":
    try:
        test_cors_allowlist_blocking()
        test_cors_allowlist_permitting()
        test_unauthorized_get()
        print("\n🎉 All CORS verification tests passed!")
    except Exception as e:
        print(f"❌ Test failed: {e}")
