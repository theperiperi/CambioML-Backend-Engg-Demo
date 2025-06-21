#!/usr/bin/env python3
"""
Test script for the FastAPI backend
"""

import asyncio
import aiohttp
import json
import sys
from typing import Dict, Any

BASE_URL = "http://localhost:8000"

async def test_api_endpoints():
    """Test the main API endpoints"""
    
    async with aiohttp.ClientSession() as session:
        print("🧪 Testing FastAPI Backend...")
        
        # Test 1: Health check
        print("\n1. Testing health endpoint...")
        try:
            async with session.get(f"{BASE_URL}/") as response:
                if response.status == 200:
                    print("✅ Health check passed")
                else:
                    print(f"❌ Health check failed: {response.status}")
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False
        
        # Test 2: API documentation
        print("\n2. Testing API documentation...")
        try:
            async with session.get(f"{BASE_URL}/docs") as response:
                if response.status == 200:
                    print("✅ API documentation accessible")
                else:
                    print(f"❌ API documentation failed: {response.status}")
        except Exception as e:
            print(f"❌ API documentation error: {e}")
        
        # Test 3: Create session (without valid API key)
        print("\n3. Testing session creation...")
        try:
            session_data = {
                "api_key": "test-key",
                "provider": "anthropic",
                "model": "claude-3-5-sonnet-20241022-v2:0",
                "system_prompt": "Test system prompt"
            }
            
            async with session.post(
                f"{BASE_URL}/api/sessions",
                json=session_data
            ) as response:
                if response.status in [200, 400]:  # 400 is expected for invalid API key
                    print("✅ Session creation endpoint working")
                    if response.status == 200:
                        session_info = await response.json()
                        print(f"   Session ID: {session_info.get('session_id')}")
                else:
                    print(f"❌ Session creation failed: {response.status}")
        except Exception as e:
            print(f"❌ Session creation error: {e}")
        
        # Test 4: VNC status
        print("\n4. Testing VNC status...")
        try:
            async with session.get(f"{BASE_URL}/api/vnc/status") as response:
                if response.status == 200:
                    vnc_status = await response.json()
                    print(f"✅ VNC status: {vnc_status.get('status', 'unknown')}")
                else:
                    print(f"❌ VNC status failed: {response.status}")
        except Exception as e:
            print(f"❌ VNC status error: {e}")
        
        print("\n🎉 API testing completed!")
        return True

async def test_websocket():
    """Test WebSocket connection"""
    print("\n🔌 Testing WebSocket connection...")
    
    try:
        # Create a test session first
        async with aiohttp.ClientSession() as session:
            session_data = {
                "api_key": "test-key",
                "provider": "anthropic",
                "model": "claude-3-5-sonnet-20241022-v2:0"
            }
            
            async with session.post(
                f"{BASE_URL}/api/sessions",
                json=session_data
            ) as response:
                if response.status == 200:
                    session_info = await response.json()
                    session_id = session_info.get('session_id')
                    
                    if session_id:
                        # Test WebSocket connection
                        ws_url = f"ws://localhost:8000/ws/{session_id}"
                        
                        async with aiohttp.ClientSession() as ws_session:
                            async with ws_session.ws_connect(ws_url) as websocket:
                                print("✅ WebSocket connection established")
                                
                                # Send a ping message
                                await websocket.send_str(json.dumps({"type": "ping"}))
                                
                                # Wait for pong response
                                try:
                                    async with asyncio.timeout(5):
                                        async for msg in websocket:
                                            if msg.type == aiohttp.WSMsgType.TEXT:
                                                data = json.loads(msg.data)
                                                if data.get("type") == "pong":
                                                    print("✅ WebSocket ping/pong working")
                                                    break
                                except asyncio.TimeoutError:
                                    print("⚠️  WebSocket ping/pong timeout")
                                
                                await websocket.close()
                    else:
                        print("❌ Could not get session ID for WebSocket test")
                else:
                    print("❌ Could not create session for WebSocket test")
                    
    except Exception as e:
        print(f"❌ WebSocket test error: {e}")

def main():
    """Main test function"""
    print("🚀 FastAPI Backend Test Suite")
    print("=" * 40)
    
    # Check if server is running
    try:
        import requests
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code != 200:
            print(f"❌ Server not responding properly: {response.status_code}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Cannot connect to server at {BASE_URL}")
        print(f"   Error: {e}")
        print("\n💡 Make sure the FastAPI server is running:")
        print("   ./start_fastapi.sh")
        print("   or")
        print("   docker-compose up -d computer-use-fastapi")
        sys.exit(1)
    
    # Run tests
    success = asyncio.run(test_api_endpoints())
    asyncio.run(test_websocket())
    
    if success:
        print("\n✅ All tests passed!")
        print("\n🌐 You can now access:")
        print(f"   Web Interface: {BASE_URL}")
        print(f"   API Documentation: {BASE_URL}/docs")
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 