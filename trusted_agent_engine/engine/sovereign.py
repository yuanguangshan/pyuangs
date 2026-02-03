from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
import base64

class SovereignManager:
    """
    Manages policy signing and verification using Ed25519.
    """

    @staticmethod
    def generate_key_pair():
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        return private_pem.decode('utf-8'), public_pem.decode('utf-8')

    @staticmethod
    def sign_policy(content: str, private_key_pem: str) -> str:
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode('utf-8'),
            password=None
        )
        if not isinstance(private_key, ed25519.Ed25519PrivateKey):
            raise ValueError("Private key must be Ed25519")
        
        signature = private_key.sign(content.encode('utf-8'))
        return base64.b64encode(signature).decode('utf-8')

    @staticmethod
    def verify_policy(content: str, signature_b64: str, public_key_pem: str) -> bool:
        try:
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode('utf-8')
            )
            if not isinstance(public_key, ed25519.Ed25519PublicKey):
                return False
            
            signature = base64.b64decode(signature_b64)
            public_key.verify(signature, content.encode('utf-8'))
            return True
        except Exception:
            return False
