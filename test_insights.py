#!/usr/bin/env python3
"""
Test script to verify AMU insights API endpoints work with seeded data
"""
import requests
import json
from datetime import datetime

# API base URL
BASE_URL = "http://localhost:8000"

def test_authentication():
    """Test user authentication"""
    print("🔐 Testing Authentication...")
    
    # Test login
    login_data = {
        "email": "owner@greenpastures.com",
        "password": "testpass123"
    }
    
    response = requests.post(f"{BASE_URL}/auth/jwt/create/", json=login_data)
    
    if response.status_code == 200:
        tokens = response.json()
        print("✅ Login successful")
        return tokens['access']
    else:
        print(f"❌ Login failed: {response.status_code} - {response.text}")
        return None

def test_amu_insights(access_token):
    """Test AMU insights generation"""
    print("\n🤖 Testing AMU Insights Generation...")
    
    headers = {
        "Authorization": f"JWT {access_token}",
        "Content-Type": "application/json"
    }
    
    # Test insights generation for a dairy cow
    insights_data = {"livestock_id": 1}  # COW-001
    
    response = requests.post(
        f"{BASE_URL}/api/amu-insights/generate/",
        json=insights_data,
        headers=headers
    )
    
    if response.status_code == 200:
        insights = response.json()
        print("✅ AMU insights generated successfully!")
        print(f"📝 Insights: {insights['insights'][:200]}...")
        return True
    else:
        print(f"❌ AMU insights failed: {response.status_code} - {response.text}")
        return False

def test_chart_data(access_token):
    """Test AMU chart data"""
    print("\n📊 Testing AMU Chart Data...")
    
    headers = {
        "Authorization": f"JWT {access_token}",
        "Content-Type": "application/json"
    }
    
    # Test chart data for a dairy cow
    response = requests.get(
        f"{BASE_URL}/api/amu-insights/chart-data/?livestock_id=1",
        headers=headers
    )
    
    if response.status_code == 200:
        chart_data = response.json()
        print("✅ AMU chart data retrieved successfully!")
        print(f"📈 Chart labels: {chart_data['chart_data']['labels']}")
        print(f"📊 Datasets: {len(chart_data['chart_data']['datasets'])}")
        print(f"📋 Summary: {chart_data['summary']}")
        return True
    else:
        print(f"❌ AMU chart data failed: {response.status_code} - {response.text}")
        return False

def test_feed_insights(access_token):
    """Test feed insights"""
    print("\n🌾 Testing Feed Insights...")
    
    headers = {
        "Authorization": f"JWT {access_token}",
        "Content-Type": "application/json"
    }
    
    # Test feed insights for a dairy cow
    response = requests.get(
        f"{BASE_URL}/api/feed-insights/chart-data/?livestock_id=1",
        headers=headers
    )
    
    if response.status_code == 200:
        feed_data = response.json()
        print("✅ Feed insights retrieved successfully!")
        print(f"💰 Total spend: ${feed_data['summary']['total_spend']}")
        print(f"📊 Time period: {feed_data['summary']['time_period']}")
        return True
    else:
        print(f"❌ Feed insights failed: {response.status_code} - {response.text}")
        return False

def test_yield_insights(access_token):
    """Test yield insights"""
    print("\n📈 Testing Yield Insights...")
    
    headers = {
        "Authorization": f"JWT {access_token}",
        "Content-Type": "application/json"
    }
    
    # Test yield insights for a dairy cow
    response = requests.get(
        f"{BASE_URL}/api/yield-insights/chart-data/?livestock_id=1",
        headers=headers
    )
    
    if response.status_code == 200:
        yield_data = response.json()
        print("✅ Yield insights retrieved successfully!")
        print(f"📈 Total yield: {yield_data['summary']['total_yield']}")
        print(f"📊 Yield types: {yield_data['summary']['types']}")
        return True
    else:
        print(f"❌ Yield insights failed: {response.status_code} - {response.text}")
        return False

def main():
    """Main test function"""
    print("🚀 Starting FarmSense API Insights Test")
    print("=" * 50)
    
    # Test authentication
    access_token = test_authentication()
    if not access_token:
        print("❌ Cannot proceed without authentication")
        return
    
    # Test all insights endpoints
    tests = [
        test_amu_insights,
        test_chart_data,
        test_feed_insights,
        test_yield_insights
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test(access_token):
                passed += 1
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"🎯 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The insights system is working perfectly!")
    else:
        print("⚠️ Some tests failed. Check the API endpoints and data.")

if __name__ == "__main__":
    main()
