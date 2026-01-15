#!/usr/bin/env python
import requests
import json

def test_api_endpoints():
    base_url = "http://127.0.0.1:8000"
    
    # We need to authenticate first since the views require @login_required
    print("=== Testing API Endpoints ===")
    print("Note: These endpoints require authentication")
    
    endpoints_to_test = [
        "/loans/api/borrowers/search/?q=anna&has_loans=true",
        "/loans/api/borrowers/with-loans/",
    ]
    
    for endpoint in endpoints_to_test:
        url = base_url + endpoint
        print(f"\n🔍 Testing: {url}")
        
        try:
            response = requests.get(url, timeout=5)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"✅ JSON Response: {json.dumps(data, indent=2)}")
                except json.JSONDecodeError:
                    print(f"❌ Invalid JSON: {response.text[:200]}")
            elif response.status_code == 302:
                print("🔒 Redirected (likely to login page)")
                print(f"Location: {response.headers.get('Location', 'Not specified')}")
            elif response.status_code == 404:
                print("❌ Not Found - Check URL pattern")
            else:
                print(f"❌ Error: {response.text[:200]}")
                
        except requests.exceptions.ConnectionError:
            print("❌ Connection Error - Is the server running?")
        except requests.exceptions.Timeout:
            print("❌ Timeout")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")

if __name__ == '__main__':
    test_api_endpoints()
