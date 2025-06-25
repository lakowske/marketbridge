"""A simple test to check if pytest is working."""

from marketbridge import build


def test_pytest() -> None:
    """A simple assertion to check if pytest is working."""
    a = 1
    assert a == 1
    build()
