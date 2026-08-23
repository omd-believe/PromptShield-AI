import sys
import pytest
from pathlib import Path

sys.path.append(
    str(Path(__file__).resolve().parents[1] / "app")
)

from privacy import (
    mask_email,
    mask_phone,
    mask_card,
    mask_ip_address,
    mask_pii
)


def test_mask_email():
    text = "Contact me at test@example.com"
    assert mask_email(text) == "Contact me at <EMAIL>"


def test_mask_phone():
    text = "Call me at 98765 43210"
    assert mask_phone(text) == "Call me at <PHONE>"


def test_mask_card():
    text = "My card is 4111 1111 1111 1111"
    assert mask_card(text) == "My card is <CARD>"


def test_mask_ip_address():
    text = "Server IP is 192.168.1.10"
    assert mask_ip_address(text) == "Server IP is <IP_ADDRESS>"


def test_mask_pii():
    text = (
        "Email test@example.com, "
        "phone 9876543210, "
        "card 4111 1111 1111 1111, "
        "IP 192.168.1.10"
    )

    expected = (
        "Email <EMAIL>, "
        "phone <PHONE>, "
        "card <CARD>, "
        "IP <IP_ADDRESS>"
    )

    assert mask_pii(text) == expected 

def test_mask_pii_invalid_input():
    with pytest.raises(TypeError):
        mask_pii(123)