import pytest
from unittest.mock import MagicMock, patch
import time
from app.core.key_manager import KeyManager

@pytest.fixture
def mock_env_manager():
    with patch("app.core.key_manager.env_manager") as mock:
        yield mock

@pytest.fixture
def mock_api_monitor():
    with patch("app.core.key_manager.api_monitor") as mock:
        mock.get_stats_for_key.return_value = None
        yield mock

@pytest.fixture
def key_manager():
    # Reset singleton state
    KeyManager._instance = None
    km = KeyManager()
    km._cooldowns = {}
    km._model_failures = {}
    km._model_cooldowns = {}
    return km

def test_get_next_key_basic(key_manager, mock_env_manager, mock_api_monitor):
    """Basic key selection from available keys."""
    mock_env_manager.get_groq_keys.return_value = [
        {"key": "K1", "value": "key-1"},
        {"key": "K2", "value": "key-2"}
    ]
    mock_api_monitor.get_stats_for_key.return_value = None
    
    key = key_manager.get_next_key()
    assert key in ["key-1", "key-2"]

def test_get_next_key_least_used(key_manager, mock_env_manager, mock_api_monitor):
    """Should select least used key."""
    mock_env_manager.get_groq_keys.return_value = [
        {"key": "K1", "value": "key-heavy"},
        {"key": "K2", "value": "key-light"}
    ]
    
    def side_effect(k):
        if k == "key-heavy":
            return {"daily_usage": {"requests_today": 100}}
        if k == "key-light":
            return {"daily_usage": {"requests_today": 5}}
        return None
        
    mock_api_monitor.get_stats_for_key.side_effect = side_effect
    
    key = key_manager.get_next_key()
    assert key == "key-light"

def test_cooldown_logic(key_manager, mock_env_manager, mock_api_monitor):
    """429 should trigger cooldown and skip key."""
    mock_env_manager.get_groq_keys.return_value = [{"key": "K1", "value": "key-1"}]
    mock_api_monitor.get_stats_for_key.return_value = None
    
    k1 = key_manager.get_next_key()
    assert k1 == "key-1"
    
    key_manager.report_failure("key-1", 429)
    
    k2 = key_manager.get_next_key()
    assert k2 is None
    assert key_manager._is_in_cooldown("key-1") is True

def test_circuit_breaker_activates(key_manager, mock_env_manager, mock_api_monitor):
    """3 failures (500) should block the model."""
    mock_env_manager.get_groq_keys.return_value = [{"key": "K1", "value": "key-1"}]
    mock_api_monitor.get_stats_for_key.return_value = None
    
    model = "llama-3"
    
    # Fail 2 times
    key_manager.report_failure("key-1", 500, model)
    key_manager.report_failure("key-1", 500, model)
    assert key_manager.get_next_key(model) == "key-1" # Still active
    
    # 3rd failure -> Trip
    key_manager.report_failure("key-1", 500, model)
    
    # Should get None now
    assert key_manager.get_next_key(model) is None
    assert key_manager._is_model_broken(model) is True

def test_circuit_breaker_per_model(key_manager, mock_env_manager, mock_api_monitor):
    """Blocking model A should not block model B."""
    mock_env_manager.get_groq_keys.return_value = [{"key": "K1", "value": "key-1"}]
    
    modelA = "broken-model"
    modelB = "working-model"
    
    # Break model A
    for _ in range(3):
        key_manager.report_failure("key-1", 500, modelA)
        
    assert key_manager.get_next_key(modelA) is None
    assert key_manager.get_next_key(modelB) == "key-1"

def test_circuit_breaker_recovery(key_manager, mock_env_manager, mock_api_monitor):
    """Model should auto-recover after cooldown."""
    mock_env_manager.get_groq_keys.return_value = [{"key": "K1", "value": "key-1"}]
    model = "recovering-model"
    
    # Break model
    for _ in range(3):
        key_manager.report_failure("key-1", 500, model)
        
    assert key_manager.get_next_key(model) is None
    
    # Force expiry
    key_manager._model_cooldowns[model] = time.time() - 1 
    
    # Next call should trigger cleanup (internal logic inside get_next_key calls cleanup)
    # But wait, get_next_key calls cleanup before checking broken status.
    key = key_manager.get_next_key(model)
    
    assert key == "key-1"
    assert model not in key_manager._model_cooldowns
    assert model not in key_manager._model_failures # Should be reset
