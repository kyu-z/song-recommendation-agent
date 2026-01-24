#!/usr/bin/env python3
"""
Test script for the FastAPI Music Agent
"""

import requests
import json

# API endpoint
API_BASE = "http://127.0.0.1:8000"

def test_health_check():
    """Test the health check endpoint"""
    print("🔍 Testing health check...")
    response = requests.get(f"{API_BASE}/")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_agent_info():
    """Test the agent info endpoint"""
    print("🔍 Testing agent info...")
    response = requests.get(f"{API_BASE}/info")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Agent Info: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    else:
        print(f"Error: {response.text}")
    print()

def test_recommendation(user_input: str):
    """Test the recommendation endpoint"""
    print(f"🎵 Testing recommendation for: {user_input}")
    
    payload = {
        "user_input": user_input
    }
    
    response = requests.post(
        f"{API_BASE}/recommend",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Success: {result['success']}")
        print(f"Search Goal: {result['search_goal']}")
        print(f"Total Found: {result['total_found']}")
        print(f"Message: {result['message']}")
        print("\nSongs:")
        
        for i, song in enumerate(result['songs'], 1):
            print(f"{i}. {song['title']} - {song['artist']}")
            print(f"   Reason: {song['reason'][:100]}...")
            if song['link']:
                print(f"   Link: {song['link']}")
                print(f"   Platform: {song['platform']}")
            print(f"   Source: {song['source']}")
            print()
    else:
        print(f"Error: {response.text}")
    print("-" * 50)

def main():
    print("🎵 FastAPI Music Agent Test Suite\n")
    
    # Test endpoints
    test_health_check()
    test_agent_info()
    
    # Test recommendations
    test_cases = [
        "我要钉鞋的歌",
        "我想要一些古典钢琴独奏",
        "来点爵士乐",
        "我想听迷幻摇滚"
    ]
    
    for test_case in test_cases:
        test_recommendation(test_case)

if __name__ == "__main__":
    main()
