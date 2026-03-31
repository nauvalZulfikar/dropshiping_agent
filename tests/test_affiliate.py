"""Tests for affiliate module."""
import pytest
from affiliate.niche_scorer import calculate_score


def test_score_flip_to_dropship():
    score, decision = calculate_score(epc=6000, cvr=0.06, aov=350000, clicks=2500, trend="up")
    assert score >= 65
    assert decision == "flip_to_dropship"


def test_score_scale_affiliate():
    score, decision = calculate_score(epc=3000, cvr=0.03, aov=200000, clicks=800, trend="flat")
    assert 45 <= score < 65
    assert decision == "scale_affiliate"


def test_score_optimize():
    score, decision = calculate_score(epc=1000, cvr=0.015, aov=100000, clicks=300, trend="flat")
    assert 25 <= score < 45
    assert decision == "optimize"


def test_score_abandon():
    score, decision = calculate_score(epc=500, cvr=0.005, aov=50000, clicks=50, trend="down")
    assert score < 25
    assert decision == "abandon"
