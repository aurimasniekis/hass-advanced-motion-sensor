"""Shared fixtures."""
import pytest

# Import this repository's custom_components package before Home Assistant
# mounts the test config dir, which ships its own custom_components package.
import custom_components  # noqa: F401


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Load integrations from custom_components in every test."""
    yield
