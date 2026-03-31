"""Tests for fulfillment module."""
import pytest
from fulfillment.resi_parser import extract_resi
from store.repricing_bot import calculate_floor_price, calculate_optimal_price


def test_extract_resi_jne():
    results = extract_resi("Kak ini resinya CGKF01234567890")
    assert len(results) >= 1
    assert results[0]["resi"] == "CGKF01234567890"


def test_extract_resi_jt():
    results = extract_resi("Resi: JP1234567890123")
    assert len(results) >= 1
    assert results[0]["resi"] == "JP1234567890123"


def test_extract_resi_sicepat():
    results = extract_resi("Nomor resi 001234567890123")
    assert len(results) >= 1
    assert "001234567890123" in results[0]["resi"]


def test_extract_resi_no_match():
    results = extract_resi("Barang sudah dikirim ya kak")
    assert len(results) == 0


def test_floor_price():
    # COGS 25000, margin 15%, platform fee 8%
    floor = calculate_floor_price(25000, 0.15, 0.08)
    assert floor == 32468  # 25000 / (1 - 0.15 - 0.08) = 32467.5 → ceil = 32468


def test_optimal_price():
    competitors = [45000, 48000, 50000, 52000, 55000, 58000, 60000, 65000, 70000, 75000]
    optimal = calculate_optimal_price(competitors, cogs_idr=25000)
    assert optimal >= calculate_floor_price(25000)
    assert optimal % 1000 == 0  # Rounded to nearest 1000
