"""Tests for AI module."""
import pytest
from ai.escalation import RISK_KEYWORDS


def test_risk_keywords_exist():
    assert len(RISK_KEYWORDS) > 0
    assert "tipu" in RISK_KEYWORDS
    assert "palsu" in RISK_KEYWORDS
    assert "somasi" in RISK_KEYWORDS


def test_risk_keyword_detection():
    from ai.escalation import RISK_KEYWORDS
    message = "ini barang palsu, mau saya laporkan"
    found = any(kw in message.lower() for kw in RISK_KEYWORDS)
    assert found is True


def test_normal_message_no_escalation():
    from ai.escalation import RISK_KEYWORDS
    message = "Kak, barangnya ready? Mau order dong"
    found = any(kw in message.lower() for kw in RISK_KEYWORDS)
    assert found is False
