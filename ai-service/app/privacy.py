import re


# Regex patterns

EMAIL_PATTERN = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"

PHONE_PATTERN = r"(?:\+91[-\s]?)?[6-9]\d{4}[-\s]?\d{5}"

CARD_PATTERN = r"\b(?:\d[ -]*?){13,19}\b"

IP_PATTERN = r"\b(?:\d{1,3}\.){3}\d{1,3}\b"


def mask_email(text: str) -> str:
    """Replace email addresses with <EMAIL>."""
    return re.sub(EMAIL_PATTERN, "<EMAIL>", text)


def mask_phone(text: str) -> str:
    """Replace supported phone numbers with <PHONE>."""
    return re.sub(PHONE_PATTERN, "<PHONE>", text)


def mask_card(text: str) -> str:
    """Replace card-like numbers with <CARD>."""
    return re.sub(CARD_PATTERN, "<CARD>", text)


def mask_ip_address(text: str) -> str:
    """Replace IP addresses with <IP_ADDRESS>."""
    return re.sub(IP_PATTERN, "<IP_ADDRESS>", text)


def mask_pii(text: str) -> str:
    """
    Mask supported personally identifiable or sensitive information.

    Currently supports:
    - Email addresses
    - Indian mobile phone numbers
    - Card-like numbers
    - IPv4 addresses
    """

    if not isinstance(text, str):
        raise TypeError("text must be a string")

    text = mask_email(text)
    text = mask_phone(text)
    text = mask_card(text)
    text = mask_ip_address(text)

    return text


if __name__ == "__main__":
    prompt = (
        "Contact me at shruti@example.com or call +91 98765 43210. "
        "My card is 4111 1111 1111 1111 and server IP is 192.168.1.10."
    )

    print("Original:")
    print(prompt)

    print("\nMasked:")
    print(mask_pii(prompt))