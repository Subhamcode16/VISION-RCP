"""Vision-RCP Device Identity — Ed25519-based device authentication."""

import hashlib
import socket
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519


class DeviceIdentity:
    """Generates and manages ed25519 keypair for zero-trust device auth."""

    def __init__(self, data_dir: Path):
        self._data_dir = data_dir
        self._key_path = data_dir / "device.key"
        self._pub_path = data_dir / "device.pub"
        self._private_key = None
        self._public_key = None

    def init(self) -> str:
        """Initialize the device identity. Generates keypair if missing."""
        self._data_dir.mkdir(parents=True, exist_ok=True)

        if not self._key_path.exists():
            # Generate new Ed25519 private key
            private_key = ed25519.Ed25519PrivateKey.generate()
            
            # Save private key (PEM format)
            private_bytes = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            self._key_path.write_bytes(private_bytes)

            # Save public key (OpenSSH format for easy logging/sharing)
            public_key = private_key.public_key()
            public_bytes = public_key.public_bytes(
                encoding=serialization.Encoding.OpenSSH,
                format=serialization.PublicFormat.OpenSSH
            )
            self._pub_path.write_bytes(public_bytes)
            
            self._private_key = private_key
            self._public_key = public_key
        else:
            # Load existing keys
            self._private_key = serialization.load_pem_private_key(
                self._key_path.read_bytes(),
                password=None
            )
            self._public_key = self._private_key.public_key()

        return self.fingerprint

    def sign(self, message: bytes) -> bytes:
        """Sign a message with the device private key."""
        if not self._private_key:
            self.init()
        return self._private_key.sign(message)

    @staticmethod
    def verify(message: bytes, signature: bytes, public_key_bytes: bytes) -> bool:
        """Verify a signature against a public key."""
        try:
            # Assume public_key_bytes is in OpenSSH format or Raw
            try:
                public_key = serialization.load_ssh_public_key(public_key_bytes)
            except Exception:
                public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)
                
            public_key.verify(signature, message)
            return True
        except Exception:
            return False

    @property
    def fingerprint(self) -> str:
        """SHA256 fingerprint of the public key."""
        if not self._public_key:
            self.init()
        
        # We use the raw public bytes for fingerprinting
        pub_bytes = self._public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        sha256 = hashlib.sha256(pub_bytes).hexdigest()
        
        # Format as colon-separated pairs: aa:bb:cc...
        return ":".join(sha256[i:i+2] for i in range(0, 32, 2))

    @property
    def public_key_bytes(self) -> bytes:
        """Returns raw public key bytes."""
        if not self._public_key:
            self.init()
        return self._public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )

    @property
    def device_name(self) -> str:
        """Default device name using hostname."""
        return socket.gethostname()
