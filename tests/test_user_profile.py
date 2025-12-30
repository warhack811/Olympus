# tests/test_user_profile.py
"""
User Profile Service Unit Tests

Phase 1.2 - Blueprint v1 Section 8 Layer 2 doğrulama testleri.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_session():
    """Mock database session."""
    session = MagicMock()
    session.exec = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]), first=MagicMock(return_value=None)))
    session.add = MagicMock()
    session.commit = MagicMock()
    session.refresh = MagicMock()
    session.get = MagicMock(return_value=None)
    return session


@pytest.fixture
def sample_fact():
    """Sample fact data."""
    return {
        "id": 1,
        "user_id": 123,
        "category": "personal",
        "key": "name",
        "value": "Ahmet",
        "confidence": 0.8,
        "source": "inferred",
        "version": 1,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }


# =============================================================================
# RESULT TYPE TESTS
# =============================================================================

class TestResultTypes:
    """Result dataclass tests."""
    
    def test_conflict_result_no_conflict(self):
        """ConflictResult çakışma yok durumu."""
        from app.services.user_profile_service import ConflictResult
        result = ConflictResult(has_conflict=False)
        assert result.has_conflict is False
        assert result.existing_fact_id is None
    
    def test_conflict_result_with_conflict(self):
        """ConflictResult çakışma var durumu."""
        from app.services.user_profile_service import ConflictResult
        result = ConflictResult(
            has_conflict=True,
            existing_fact_id=42,
            existing_value="Eski değer",
            conflict_type="direct"
        )
        assert result.has_conflict is True
        assert result.existing_fact_id == 42
        assert result.conflict_type == "direct"
    
    def test_add_fact_result_success(self):
        """AddFactResult başarılı ekleme."""
        from app.services.user_profile_service import AddFactResult
        result = AddFactResult(success=True, fact_id=1, action="created")
        assert result.success is True
        assert result.fact_id == 1
        assert result.action == "created"
    
    def test_confirm_result(self):
        """ConfirmResult testi."""
        from app.services.user_profile_service import ConfirmResult
        result = ConfirmResult(success=True, new_confidence=0.95, confirmed_by="gpt-4")
        assert result.success is True
        assert result.new_confidence == 0.95


# =============================================================================
# CATEGORY VALIDATION TESTS
# =============================================================================

class TestCategoryValidation:
    """Kategori doğrulama testleri."""
    
    def test_valid_categories(self):
        """Geçerli kategoriler listesi."""
        from app.services.user_profile_service import UserProfileService
        assert "personal" in UserProfileService.CATEGORIES
        assert "preference" in UserProfileService.CATEGORIES
        assert "context" in UserProfileService.CATEGORIES
        assert "relationship" in UserProfileService.CATEGORIES
    
    @pytest.mark.asyncio
    async def test_invalid_category_rejected(self):
        """Geçersiz kategori reddedilmeli."""
        from app.services.user_profile_service import UserProfileService
        
        result = await UserProfileService.add_fact(
            user_id=1,
            category="invalid_category",
            key="test",
            value="test"
        )
        assert result.success is False
        assert "Geçersiz kategori" in result.message


# =============================================================================
# ADD FACT TESTS
# =============================================================================

class TestAddFact:
    """Fact ekleme testleri."""
    
    @pytest.mark.asyncio
    async def test_add_fact_success(self, mock_session):
        """Başarılı fact ekleme."""
        mock_fact = MagicMock()
        mock_fact.id = 1
        
        with patch("app.core.database.get_session") as mock_get_session:
            mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_get_session.return_value.__exit__ = MagicMock(return_value=False)
            
            # Mock exec for conflict check (no conflict)
            mock_session.exec.return_value.first.return_value = None
            
            # Mock refresh to set ID
            def refresh_mock(obj):
                obj.id = 1
            mock_session.refresh = refresh_mock
            
            from app.services.user_profile_service import UserProfileService
            result = await UserProfileService.add_fact(
                user_id=123,
                category="personal",
                key="name",
                value="Ahmet"
            )
            
            assert result.success is True
            assert result.action == "created"
    
    @pytest.mark.asyncio
    async def test_add_fact_conflict_detected(self, mock_session, sample_fact):
        """Çakışma tespiti."""
        existing_fact = MagicMock(**sample_fact)
        existing_fact.value = "Mehmet"  # Farklı değer
        
        with patch("app.core.database.get_session") as mock_get_session:
            mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_get_session.return_value.__exit__ = MagicMock(return_value=False)
            
            # Mock: existing fact found
            mock_session.exec.return_value.first.return_value = existing_fact
            
            from app.services.user_profile_service import UserProfileService
            result = await UserProfileService.add_fact(
                user_id=123,
                category="personal",
                key="name",
                value="Ahmet",  # Farklı değer
                auto_resolve_conflict=False
            )
            
            assert result.success is False
            assert result.action == "conflict_detected"
            assert result.conflict is not None
            assert result.conflict.has_conflict is True


# =============================================================================
# GET FACTS TESTS
# =============================================================================

class TestGetFacts:
    """Fact sorgulama testleri."""
    
    @pytest.mark.asyncio
    async def test_get_facts_empty(self, mock_session):
        """Boş fact listesi."""
        with patch("app.core.database.get_session") as mock_get_session:
            mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_get_session.return_value.__exit__ = MagicMock(return_value=False)
            mock_session.exec.return_value.all.return_value = []
            
            from app.services.user_profile_service import UserProfileService
            facts = await UserProfileService.get_facts(user_id=123)
            
            assert facts == []
    
    @pytest.mark.asyncio
    async def test_get_facts_with_data(self, mock_session, sample_fact):
        """Fact listesi dönmeli."""
        mock_fact = MagicMock(**sample_fact)
        
        with patch("app.core.database.get_session") as mock_get_session:
            mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_get_session.return_value.__exit__ = MagicMock(return_value=False)
            mock_session.exec.return_value.all.return_value = [mock_fact]
            
            from app.services.user_profile_service import UserProfileService
            facts = await UserProfileService.get_facts(user_id=123)
            
            assert len(facts) == 1
            assert facts[0]["key"] == "name"
            assert facts[0]["value"] == "Ahmet"


# =============================================================================
# LLM CONFIRMATION TESTS
# =============================================================================

class TestConfirmFact:
    """LLM confirmation testleri."""
    
    @pytest.mark.asyncio
    async def test_confirm_fact_success(self, mock_session, sample_fact):
        """Başarılı confirmation."""
        mock_fact = MagicMock(**sample_fact)
        
        with patch("app.core.database.get_session") as mock_get_session:
            mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_get_session.return_value.__exit__ = MagicMock(return_value=False)
            mock_session.get.return_value = mock_fact
            
            from app.services.user_profile_service import UserProfileService
            result = await UserProfileService.confirm_fact(
                fact_id=1,
                new_confidence=0.95,
                confirmed_by="gpt-4"
            )
            
            assert result.success is True
            assert result.new_confidence == 0.95
            assert result.confirmed_by == "gpt-4"
    
    @pytest.mark.asyncio
    async def test_confirm_fact_not_found(self, mock_session):
        """Fact bulunamadı."""
        with patch("app.core.database.get_session") as mock_get_session:
            mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_get_session.return_value.__exit__ = MagicMock(return_value=False)
            mock_session.get.return_value = None
            
            from app.services.user_profile_service import UserProfileService
            result = await UserProfileService.confirm_fact(fact_id=999, new_confidence=0.9)
            
            assert result.success is False


# =============================================================================
# PROFILE CONTEXT TESTS
# =============================================================================

class TestProfileContext:
    """Gateway entegrasyon testleri."""
    
    @pytest.mark.asyncio
    async def test_get_profile_context_empty(self, mock_session):
        """Boş profil context."""
        with patch("app.core.database.get_session") as mock_get_session:
            mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_get_session.return_value.__exit__ = MagicMock(return_value=False)
            mock_session.exec.return_value.all.return_value = []
            
            from app.services.user_profile_service import UserProfileService
            context = await UserProfileService.get_profile_context(user_id=123)
            
            assert context["available"] is True
            assert context["fact_count"] == 0
            assert context["facts"] == []
    
    @pytest.mark.asyncio
    async def test_get_profile_context_with_facts(self, mock_session, sample_fact):
        """Dolu profil context."""
        mock_fact = MagicMock(**sample_fact)
        mock_fact.confidence = 0.8
        
        with patch("app.core.database.get_session") as mock_get_session:
            mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_get_session.return_value.__exit__ = MagicMock(return_value=False)
            mock_session.exec.return_value.all.return_value = [mock_fact]
            
            from app.services.user_profile_service import UserProfileService
            context = await UserProfileService.get_profile_context(user_id=123)
            
            assert context["available"] is True
            assert context["fact_count"] == 1
            assert "[PERSONAL]" in context["summary"]


# =============================================================================
# MODEL TESTS
# =============================================================================

class TestUserProfileFactModel:
    """Model testleri."""
    
    def test_model_exists(self):
        """Model import edilebilmeli."""
        from app.core.models import UserProfileFact
        assert UserProfileFact is not None
        assert hasattr(UserProfileFact, '__tablename__')
        assert UserProfileFact.__tablename__ == "user_profile_facts"
    
    def test_model_schema_has_required_fields(self):
        """Model şeması gerekli alanları içermeli."""
        from app.core.models import UserProfileFact
        
        # Get field names from model_fields (Pydantic v2)
        field_names = list(UserProfileFact.model_fields.keys())
        
        # Versioning fields
        assert "version" in field_names
        assert "is_active" in field_names
        assert "superseded_by" in field_names
        assert "supersedes" in field_names
        
        # LLM Confirmation fields
        assert "confidence" in field_names
        assert "confirmed_by" in field_names
        assert "confirmed_at" in field_names
        assert "source" in field_names
        
        # Cross-validation fields
        assert "conflicting_fact_id" in field_names
        assert "conflict_resolved" in field_names
        
        # Core fields
        assert "user_id" in field_names
        assert "category" in field_names
        assert "key" in field_names
        assert "value" in field_names
