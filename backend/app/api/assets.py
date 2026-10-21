"""Process-local signing key; credentials are not part of domain responses."""
import os
import secrets

ASSET_SIGN_KEY = os.getenv('FOOD_ASSET_SIGNING_KEY', secrets.token_hex(32)).encode()
