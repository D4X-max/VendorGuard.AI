import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from app.domain.services.vendor_service import VendorService
from app.domain.schemas.vendor import VendorCreate
from app.models.all_models import VendorCriticalityTier


class TestInherentRiskCalculation:
    """Unit tests — no DB required."""

    def setup_method(self):
        mock_session = AsyncMock()
        self.service = VendorService(mock_session)

    def test_max_risk_score(self):
        vendor = VendorCreate(
            legal_name="HighRisk Corp",
            domain="highrisk.com",
            stores_customer_data=True,
            access_production_systems=True,
            handles_payments=True,
            handles_phi_pii=True,
        )
        score = self.service._calculate_inherent_risk(vendor)
        assert score == 100.0

    def test_zero_risk_score(self):
        vendor = VendorCreate(
            legal_name="LowRisk Corp",
            domain="lowrisk.com",
        )
        score = self.service._calculate_inherent_risk(vendor)
        assert score == 0.0

    def test_partial_risk_score(self):
        vendor = VendorCreate(
            legal_name="Mid Corp",
            domain="mid.com",
            stores_customer_data=True,
            handles_payments=True,
        )
        score = self.service._calculate_inherent_risk(vendor)
        assert score == 60.0  # 40 + 20