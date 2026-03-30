import requests

BASE_URL = "http://127.0.0.1:9121"

def test_cors_preflight():
    print("Testing CORS preflight (OPTIONS /api/status from any-company.com)...")
    origin = "https://any-company.com"
    headers = {
        "Origin": origin,
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "X-API-Key"
    }
    response = requests.options(f"{BASE_URL}/api/status", headers=headers)
    
    print(f"Status Code: {response.status_code}")
    print(f"Allow-Origin: {response.headers.get('Access-Control-Allow-Origin')}")
    
    assert response.status_code == 200
    assert response.headers.get('Access-Control-Allow-Origin') == origin
    print("✅ Universal CORS preflight test passed!")

def test_unauthorized_get():
    print("\nTesting Unauthorized GET /api/status (should return 401)...")
    response = requests.get(f"{BASE_URL}/api/status")
    print(f"Status Code: {response.status_code}")
    assert response.status_code == 401
    print("✅ Unauthorized GET test passed!")

if __name__ == "__main__":
    try:
        test_cors_preflight()
        test_unauthorized_get()
    except Exception as e:
        print(f"❌ Test failed: {e}")
