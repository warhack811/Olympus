
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

@pytest.mark.asyncio
async def test_acquire_leader_lock_success():
    """Test succesful lock acquisition returning a token."""
    mock_redis = AsyncMock()
    mock_redis.set.return_value = True # Lock acquired
    
    with patch("app.core.maintenance.get_redis", return_value=mock_redis):
        from app.core.maintenance import acquire_leader_lock
        token = await acquire_leader_lock("test_lock", 60)
        assert token is not None
        assert isinstance(token, str) # Should return a UUID string
        mock_redis.set.assert_called_once()
        # Verify call args properly
        args, kwargs = mock_redis.set.call_args
        assert args[0] == "maintenance:leader:test_lock"
        assert args[1] == token # Value is generated token
        assert kwargs["nx"] is True
        assert kwargs["ex"] == 60

@pytest.mark.asyncio
async def test_acquire_leader_lock_failure():
    """Test lock acquisition failure (already locked) returning None."""
    mock_redis = AsyncMock()
    mock_redis.set.return_value = False # Lock failed (key exists)
    
    with patch("app.core.maintenance.get_redis", return_value=mock_redis):
        from app.core.maintenance import acquire_leader_lock
        token = await acquire_leader_lock("test_lock")
        assert token is None

@pytest.mark.asyncio
async def test_acquire_leader_lock_redis_down():
    """Test behavior when Redis is None (Fail-Closed)."""
    with patch("app.core.maintenance.get_redis", return_value=None):
        from app.core.maintenance import acquire_leader_lock
        token = await acquire_leader_lock("test_lock")
        assert token is None

@pytest.mark.asyncio
async def test_release_leader_lock_safe():
    """Test safe release with Lua script."""
    mock_redis = AsyncMock()
    
    with patch("app.core.maintenance.get_redis", return_value=mock_redis):
        from app.core.maintenance import release_leader_lock
        token = "test-token"
        await release_leader_lock("test_lock", token)
        
        # Verify LUA script execution
        mock_redis.eval.assert_called_once()
        args, _ = mock_redis.eval.call_args
        script = args[0]
        assert "redis.call(\"get\", KEYS[1]) == ARGV[1]" in script
        assert args[2] == "maintenance:leader:test_lock" # Correct keys
        assert args[3] == token # Correct token arg
