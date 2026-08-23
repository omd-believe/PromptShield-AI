import unicodedata

def remove_control_characters(text: str) -> str:
    """
    Remove non-whitespace Unicode control characters.

    Normal whitespace characters such as newline, tab, and
    carriage return are preserved because they are handled
    later by whitespace normalization.
    """

    return "".join(
        char
        for char in text
        if not unicodedata.category(char).startswith("C")
        or char in "\n\t\r"
    )

def normalize_text(text: str) -> str:
    """
    Perform basic, safe text normalization.

    Operations:
    1. Validate input type
    2. Normalize Unicode
    3. Remove leading/trailing whitespace
    4. Collapse repeated whitespace
    """

    if not isinstance(text, str):
        raise TypeError("text must be a string")

    # Normalize Unicode characters
    text = unicodedata.normalize("NFKC", text)

    # Remove leading/trailing whitespace
    text = text.strip()

    # Collapse multiple spaces/newlines/tabs
    text = " ".join(text.split())

    return text

if __name__ == "__main__":
    test_cases = [
        "   Hello       World   ",
        "\n\n  What is   AI?\t\t",
        "Don't delete the database!!!",
        "Hello\x00World"
    ]

    for i, prompt in enumerate(test_cases, start=1):
        result = normalize_text(prompt)

        print(f"\nTest Case {i}")
        print("Original:  ", repr(prompt))
        print("Normalized:", repr(result))