"""Shared stateless pipeline services initialized once per process."""

from app.services.preprocessing import Preprocessor
from app.services.privacy_engine import PrivacyEngine

preprocessor = Preprocessor()
privacy_engine = PrivacyEngine()
