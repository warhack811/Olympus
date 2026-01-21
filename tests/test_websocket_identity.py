import pytest
from unittest.mock import AsyncMock, MagicMock
from app.core.websockets import connected, register_connection, unregister_connection, send_to_user

@pytest.fixture(autouse=True)
def clean_connections():
    """Clear connected dict before each test."""
    connected.clear()
    yield
    connected.clear()

@pytest.mark.asyncio
async def test_websocket_identity_registration():
    ws = MagicMock()
    register_connection(ws, 123, "alice")
    
    assert ws in connected
    assert "123" in connected[ws]
    assert "alice" in connected[ws]
    
    unregister_connection(ws)
    assert ws not in connected

@pytest.mark.asyncio
async def test_send_to_user_by_id_and_username():
    ws = MagicMock()
    ws.send_json = AsyncMock()
    
    register_connection(ws, 123, "alice")
    
    message = {"type": "test", "content": "hello"}
    
    # Test send by user_id (stringified)
    sent_count = await send_to_user("123", message)
    assert sent_count == 1
    ws.send_json.assert_called_with(message)
    
    # Test send by username
    ws.send_json.reset_mock()
    sent_count = await send_to_user("alice", message)
    assert sent_count == 1
    ws.send_json.assert_called_with(message)
    
    unregister_connection(ws)

@pytest.mark.asyncio
async def test_multi_user_isolation():
    ws_alice = MagicMock()
    ws_alice.send_json = AsyncMock()
    register_connection(ws_alice, 101, "alice")
    
    ws_bob = MagicMock()
    ws_bob.send_json = AsyncMock()
    register_connection(ws_bob, 102, "bob")
    
    message = {"type": "secret"}
    
    # Send to alice, bob should not receive
    await send_to_user("alice", message)
    assert ws_alice.send_json.called
    assert not ws_bob.send_json.called
    
    # Send to bob's user_id, alice should not receive
    ws_alice.send_json.reset_mock()
    ws_bob.send_json.reset_mock()
    await send_to_user("102", message)
    assert not ws_alice.send_json.called
    assert ws_bob.send_json.called
    
    unregister_connection(ws_alice)
    unregister_connection(ws_bob)

@pytest.mark.asyncio
async def test_no_leak_to_anonymous_users():
    ws_anon = MagicMock()
    ws_anon.send_json = AsyncMock()
    # Anonymous connection (not registered via register_connection)
    
    ws_alice = MagicMock()
    ws_alice.send_json = AsyncMock()
    register_connection(ws_alice, 101, "alice")
    
    message = {"type": "target_only"}
    
    # Send to alice
    await send_to_user("alice", message)
    
    # Alice should receive, Anon should NOT
    assert ws_alice.send_json.called
    assert not ws_anon.send_json.called
    
    unregister_connection(ws_alice)
