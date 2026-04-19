"""Vision-RCP Auth — JWT token issuer, validator, and secret key management."""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import jwt

logger = logging.getLogger("rcp.auth")

_ALGORITHM = "HS256"
_ISSUER = "vision-rcp"


class AuthManager:
    """Handles secret key generation, JWT issuance, and validation."""

    def __init__(self, data_dir: Path, access_ttl: int = 86400,
                 refresh_ttl: int = 604800):
        self._data_dir = data_dir
        self._access_ttl = access_ttl
        self._refresh_ttl = refresh_ttl
        self._secret_key_path = data_dir / "secret.key"
        self._jwt_key_path = data_dir / "jwt.key"

        self._secret: str = self._load_or_generate_secret()
        self._jwt_key: str = self._load_or_generate_jwt_key()

        # Track revoked tokens (jti)
        self._revoked: set[str] = set()

    def _load_or_generate_secret(self) -> str:
        """Load the pre-shared secret or generate one on first run."""
        if self._secret_key_path.exists():
            secret = self._secret_key_path.read_text().strip()
            if secret:
                return secret

        secret = secrets.token_urlsafe(48)
        self._secret_key_path.parent.mkdir(parents=True, exist_ok=True)
        self._secret_key_path.write_text(secret)
        # Restrict file permissions (best effort on Windows)
        try:
            import os
            os.chmod(self._secret_key_path, 0o600)
        except (OSError, AttributeError):
            pass

        logger.info("Generated new secret key at %s", self._secret_key_path)
        return secret

    def _load_or_generate_jwt_key(self) -> str:
        """Load or generate the JWT signing key (separate from shared secret)."""
        if self._jwt_key_path.exists():
            key = self._jwt_key_path.read_text().strip()
            if key:
                return key

        key = secrets.token_urlsafe(64)
        self._jwt_key_path.parent.mkdir(parents=True, exist_ok=True)
        self._jwt_key_path.write_text(key)
        try:
            import os
            os.chmod(self._jwt_key_path, 0o600)
        except (OSError, AttributeError):
            pass

        return key

    @property
    def display_secret(self) -> str:
        """Return the secret key for one-time display to the user."""
        return self._secret

    def verify_secret(self, candidate: str) -> bool:
        """Constant-time comparison of the candidate secret."""
        return hmac.compare_digest(
            hashlib.sha256(candidate.encode()).digest(),
            hashlib.sha256(self._secret.encode()).digest(),
        )

    def issue_access_token(self) -> tuple[str, str]:
        """Issue a short-lived access token. Returns (token, expires_at_iso)."""
        now = time.time()
        exp = now + self._access_ttl
        jti = str(uuid.uuid4())

        payload = {
            "sub": "owner",
            "iss": _ISSUER,
            "iat": int(now),
            "exp": int(exp),
            "jti": jti,
            "type": "access",
        }

        token = jwt.encode(payload, self._jwt_key, algorithm=_ALGORITHM)
        expires_at = datetime.fromtimestamp(exp, tz=timezone.utc).isoformat()
        return token, expires_at

    def issue_refresh_token(self) -> tuple[str, str]:
        """Issue a long-lived refresh token. Returns (token, expires_at_iso)."""
        now = time.time()
        exp = now + self._refresh_ttl
        jti = str(uuid.uuid4())

        payload = {
            "sub": "owner",
            "iss": _ISSUER,
            "iat": int(now),
            "exp": int(exp),
            "jti": jti,
            "type": "refresh",
        }

        token = jwt.encode(payload, self._jwt_key, algorithm=_ALGORITHM)
        expires_at = datetime.fromtimestamp(exp, tz=timezone.utc).isoformat()
        return token, expires_at

    def validate_token(self, token: str,
                       expected_type: str = "access") -> Optional[dict[str, Any]]:
        """Validate a JWT. Returns decoded claims or None if invalid."""
        try:
            claims = jwt.decode(
                token, self._jwt_key, algorithms=[_ALGORITHM],
                issuer=_ISSUER,
                options={"require": ["sub", "iss", "iat", "exp", "jti", "type"]},
            )
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning("Invalid token: %s", e)
            return None

        if claims.get("type") != expected_type:
            logger.warning("Token type mismatch: expected=%s got=%s",
                           expected_type, claims.get("type"))
            return None

        jti = claims.get("jti", "")
        if jti in self._revoked:
            logger.warning("Token has been revoked: jti=%s", jti)
            return None

        return claims

    def revoke_token(self, token: str) -> bool:
        """Revoke a token by adding its jti to the revocation set."""
        try:
            claims = jwt.decode(
                token, self._jwt_key, algorithms=[_ALGORITHM],
                options={"verify_exp": False},
            )
            jti = claims.get("jti")
            if jti:
                self._revoked.add(jti)
                return True
        except jwt.InvalidTokenError:
            pass
        return False

    def login(self, secret: str) -> Optional[dict[str, str]]:
        """Full login flow: verify secret → issue tokens."""
        if not self.verify_secret(secret):
            logger.warning("Login failed: invalid secret")
            return None

        access_token, access_exp = self.issue_access_token()
        refresh_token, refresh_exp = self.issue_refresh_token()

        logger.info("Login successful, tokens issued")
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": access_exp,
        }

    def refresh(self, refresh_token: str) -> Optional[dict[str, str]]:
        """Refresh flow: validate refresh token → issue new access token."""
        claims = self.validate_token(refresh_token, expected_type="refresh")
        if not claims:
            return None

        # Revoke old refresh token (rotation)
        self.revoke_token(refresh_token)

        access_token, access_exp = self.issue_access_token()
        new_refresh, refresh_exp = self.issue_refresh_token()

        logger.info("Token refreshed, old refresh token revoked")
        return {
            "access_token": access_token,
            "refresh_token": new_refresh,
            "expires_at": access_exp,
        }
