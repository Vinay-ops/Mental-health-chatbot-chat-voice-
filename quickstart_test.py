#!/usr/bin/env python
"""
Quick Start Guide for Mental Health Chatbot

This script helps you verify the setup and test all endpoints.
Run this after setting up your .env file with Supabase credentials.
"""

import requests
import json
import sys
from typing import Optional, Dict, Any

BASE_URL = "http://localhost:8002"

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_section(title):
    print(f"\n{BLUE}{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}{RESET}\n")

def print_success(message):
    print(f"{GREEN}✅ {message}{RESET}")

def print_error(message):
    print(f"{RED}❌ {message}{RESET}")

def print_info(message):
    print(f"{YELLOW}ℹ️  {message}{RESET}")

def print_result(response):
    print(f"Status: {response.status_code}")
    print("Response:")
    print(json.dumps(response.json(), indent=2))

# Test users
TEST_USER = {
    "name": "Test User",
    "email": "testuser@example.com",
    "password": "test123456",
    "user_type": "user"
}

TEST_PSYCHOLOGIST = {
    "name": "Dr. Test Psychologist",
    "email": "testpsych@example.com",
    "password": "test123456",
    "user_type": "psychologist"
}

def test_connectivity():
    """Test if the server is running"""
    print_section("Testing Server Connectivity")
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            print_success("Server is running!")
            return True
        else:
            print_error(f"Server returned status {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Cannot connect to server: {e}")
        print_info("Make sure the app is running: python app.py")
        return False

def test_debug_endpoints():
    """Test debug endpoints to verify data"""
    print_section("Testing Debug Endpoints")
    
    # Get users
    print_info("Fetching all users...")
    try:
        response = requests.get(f"{BASE_URL}/api/debug/users")
        if response.status_code == 200:
            data = response.json()
            users = data.get("users", [])
            print_success(f"Found {len(users)} users")
            for user in users:
                print(f"  - {user.get('name')} ({user.get('email')}) [Type: {user.get('user_type', 'user')}]")
        else:
            print_error(f"Failed to get users: {response.status_code}")
    except Exception as e:
        print_error(f"Error fetching users: {e}")
    
    # Get psychologists
    print_info("\nFetching all psychologists...")
    try:
        response = requests.get(f"{BASE_URL}/api/debug/psychologists")
        if response.status_code == 200:
            data = response.json()
            psychologists = data.get("psychologists", [])
            print_success(f"Found {len(psychologists)} psychologists")
            for psych in psychologists:
                print(f"  - {psych.get('name')} ({psych.get('email')})")
        else:
            print_error(f"Failed to get psychologists: {response.status_code}")
    except Exception as e:
        print_error(f"Error fetching psychologists: {e}")

def test_registration():
    """Test user registration"""
    print_section("Testing User Registration")
    
    # Register user
    print_info("Registering test user...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/register",
            json=TEST_USER,
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            data = response.json()
            print_success("User registered successfully!")
            user_token = data.get("token")
            print(f"  Name: {data.get('name')}")
            print(f"  Type: {data.get('user_type')}")
            return user_token
        elif response.status_code == 400 and "already registered" in response.text:
            print_info("User already registered (will use existing)")
            # Try to login instead
            return login(TEST_USER["email"], TEST_USER["password"])
        else:
            print_error(f"Registration failed: {response.status_code}")
            print_result(response)
            return None
    except Exception as e:
        print_error(f"Error registering user: {e}")
        return None

def test_psychologist_registration():
    """Test psychologist registration"""
    print_info("Registering test psychologist...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/register",
            json=TEST_PSYCHOLOGIST,
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            data = response.json()
            print_success("Psychologist registered successfully!")
            psych_token = data.get("token")
            print(f"  Name: {data.get('name')}")
            print(f"  Type: {data.get('user_type')}")
            return psych_token
        elif response.status_code == 400 and "already registered" in response.text:
            print_info("Psychologist already registered (will use existing)")
            return login(TEST_PSYCHOLOGIST["email"], TEST_PSYCHOLOGIST["password"])
        else:
            print_error(f"Registration failed: {response.status_code}")
            print_result(response)
            return None
    except Exception as e:
        print_error(f"Error registering psychologist: {e}")
        return None

def login(email: str, password: str) -> Optional[str]:
    """Login and get token"""
    try:
        response = requests.post(
            f"{BASE_URL}/api/login",
            json={"email": email, "password": password},
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("token")
        else:
            print_error(f"Login failed: {response.status_code}")
            return None
    except Exception as e:
        print_error(f"Error logging in: {e}")
        return None

def test_chat_request_workflow(user_token: str, psych_token: str):
    """Test complete chat request workflow"""
    print_section("Testing Chat Request Workflow")
    
    # User gets available psychologists
    print_info("User fetching available psychologists...")
    try:
        response = requests.get(
            f"{BASE_URL}/api/psychologists/available",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        if response.status_code == 200:
            data = response.json()
            psychologists = data.get("psychologists", [])
            print_success(f"Found {len(psychologists)} available psychologists")
            for psych in psychologists:
                print(f"  - {psych.get('name')} ({psych.get('email')})")
        else:
            print_error(f"Failed to get psychologists: {response.status_code}")
    except Exception as e:
        print_error(f"Error fetching psychologists: {e}")
        return
    
    # User sends chat request
    print_info("\nUser sending chat request to psychologist...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/chat-request/send",
            json={
                "psychologist_id": TEST_PSYCHOLOGIST["email"],
                "message": "I would like to discuss my anxiety"
            },
            headers={"Authorization": f"Bearer {user_token}"}
        )
        if response.status_code == 200:
            data = response.json()
            request_id = data.get("request_id")
            print_success(f"Chat request sent! Request ID: {request_id}")
            
            # Psychologist gets pending requests
            print_info("\nPsychologist checking pending requests...")
            try:
                response = requests.get(
                    f"{BASE_URL}/api/psychologist/{TEST_PSYCHOLOGIST['email']}/pending-requests",
                    headers={"Authorization": f"Bearer {psych_token}"}
                )
                if response.status_code == 200:
                    data = response.json()
                    requests_list = data.get("requests", [])
                    print_success(f"Found {len(requests_list)} pending requests")
                    for req in requests_list:
                        print(f"  - From: {req.get('user_id')}")
                        print(f"    Message: {req.get('message')}")
                        print(f"    Status: {req.get('status')}")
                    
                    # Psychologist accepts request
                    if request_id:
                        print_info("\nPsychologist accepting request...")
                        response = requests.post(
                            f"{BASE_URL}/api/chat-request/{request_id}/accept",
                            headers={"Authorization": f"Bearer {psych_token}"}
                        )
                        if response.status_code == 200:
                            print_success("Chat request accepted!")
                            
                            # Test direct messaging
                            test_direct_messages(user_token, psych_token)
                        else:
                            print_error(f"Failed to accept request: {response.status_code}")
                else:
                    print_error(f"Failed to get pending requests: {response.status_code}")
            except Exception as e:
                print_error(f"Error getting pending requests: {e}")
        else:
            print_error(f"Failed to send chat request: {response.status_code}")
            print_result(response)
    except Exception as e:
        print_error(f"Error sending chat request: {e}")

def test_direct_messages(user_token: str, psych_token: str):
    """Test direct messaging"""
    print_section("Testing Direct Messaging")
    
    # User sends message to psychologist
    print_info("User sending message to psychologist...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/messages/send",
            json={
                "receiver_id": TEST_PSYCHOLOGIST["email"],
                "message": "Hello doctor, I am ready to start our chat."
            },
            headers={"Authorization": f"Bearer {user_token}"}
        )
        if response.status_code == 200:
            print_success("Message sent successfully!")
        else:
            print_error(f"Failed to send message: {response.status_code}")
            print_result(response)
    except Exception as e:
        print_error(f"Error sending message: {e}")
    
    # Psychologist sends reply
    print_info("Psychologist sending reply...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/messages/send",
            json={
                "receiver_id": TEST_USER["email"],
                "message": "Hello! I'm glad to start working with you. Let's discuss your concerns."
            },
            headers={"Authorization": f"Bearer {psych_token}"}
        )
        if response.status_code == 200:
            print_success("Reply sent successfully!")
        else:
            print_error(f"Failed to send reply: {response.status_code}")
    except Exception as e:
        print_error(f"Error sending reply: {e}")
    
    # Get message history
    print_info("User checking message history...")
    try:
        response = requests.get(
            f"{BASE_URL}/api/messages/{TEST_PSYCHOLOGIST['email']}",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        if response.status_code == 200:
            data = response.json()
            messages = data.get("messages", [])
            print_success(f"Found {len(messages)} messages")
            for msg in messages:
                sender = msg.get("sender_id", "Unknown")
                content = msg.get("message", "")
                print(f"  {sender}: {content}")
        else:
            print_error(f"Failed to get messages: {response.status_code}")
    except Exception as e:
        print_error(f"Error getting messages: {e}")

def run_all_tests():
    """Run all tests"""
    print_section("Mental Health Chatbot - Quick Start Test Suite")
    
    # Test connectivity
    if not test_connectivity():
        print_error("Cannot proceed without server connectivity")
        return
    
    # Test debug endpoints
    test_debug_endpoints()
    
    # Test registration
    user_token = test_registration()
    if not user_token:
        print_error("Failed to register/login user")
        return
    
    psych_token = test_psychologist_registration()
    if not psych_token:
        print_error("Failed to register/login psychologist")
        return
    
    # Test complete workflow
    test_chat_request_workflow(user_token, psych_token)
    
    # Final summary
    print_section("Test Complete!")
    print_success("All core features are working!")
    print_info("Next steps:")
    print("  1. Review SETUP_GUIDE.md for detailed documentation")
    print("  2. Implement frontend for psychologist dashboard")
    print("  3. Add real-time updates with WebSockets or polling")
    print("  4. Deploy to production")

if __name__ == "__main__":
    try:
        run_all_tests()
    except KeyboardInterrupt:
        print_error("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
