"""
Personal Data Encryption Module

Provides enterprise-grade encryption for personal voice data across all corpora.
Protects ChatGPT exports, social media data, and published content with AES-256 encryption.
"""

import os
import json
import base64
import hashlib
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from pydantic import BaseModel, Field

from mcg_agent.config import get_settings
from mcg_agent.utils.exceptions import EncryptionError, DecryptionError
from mcg_agent.utils.audit import AuditLogger


class EncryptedCorpus(BaseModel):
    """Encrypted corpus data with metadata"""
    corpus_type: str = Field(description="Type of corpus: personal, social, published")
    encrypted_data: str = Field(description="Base64 encoded encrypted data")
    encryption_metadata: Dict[str, Any] = Field(description="Encryption metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    data_hash: str = Field(description="Hash of original data for integrity verification")
    
    
class EncryptionKey(BaseModel):
    """Encryption key with metadata"""
    key_id: str = Field(description="Unique key identifier")
    key_data: str = Field(description="Base64 encoded key")
    salt: str = Field(description="Base64 encoded salt")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    corpus_type: str = Field(description="Corpus type this key encrypts")


class PersonalDataEncryption:
    """
    Enterprise-grade encryption for personal voice data.
    
    Provides AES-256 encryption for all personal corpus data including:
    - ChatGPT conversation exports (personal reasoning patterns)
    - Social media posts and interactions (public voice patterns)
    - Published articles and content (professional voice patterns)
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.audit_logger = AuditLogger()
        self._keys: Dict[str, Fernet] = {}
        self._ensure_encryption_setup()
        
    def _ensure_encryption_setup(self) -> None:
        """Ensure encryption keys and directories are properly set up"""
        # Create encryption directory if it doesn't exist
        encryption_dir = Path(self.settings.ENCRYPTION_KEY_PATH).parent
        encryption_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize or load encryption keys
        self._initialize_encryption_keys()
        
    def _initialize_encryption_keys(self) -> None:
        """Initialize encryption keys for each corpus type"""
        corpus_types = ["personal", "social", "published"]
        
        for corpus_type in corpus_types:
            key_file = Path(self.settings.ENCRYPTION_KEY_PATH) / f"{corpus_type}_key.json"
            
            if key_file.exists():
                self._load_encryption_key(corpus_type, key_file)
            else:
                self._generate_encryption_key(corpus_type, key_file)
                
    def _generate_encryption_key(self, corpus_type: str, key_file: Path) -> None:
        """Generate a new encryption key for a corpus type"""
        try:
            # Generate salt
            salt = os.urandom(16)
            
            # Derive key from master password and salt
            master_password = self.settings.ENCRYPTION_MASTER_PASSWORD.encode()
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(master_password))
            
            # Create Fernet instance
            fernet = Fernet(key)
            self._keys[corpus_type] = fernet
            
            # Save key metadata
            key_metadata = EncryptionKey(
                key_id=f"{corpus_type}_{datetime.utcnow().isoformat()}",
                key_data=key.decode(),
                salt=base64.b64encode(salt).decode(),
                corpus_type=corpus_type
            )
            
            with open(key_file, 'w') as f:
                json.dump(key_metadata.dict(), f, indent=2, default=str)
                
            self.audit_logger.log_security_event(
                event_type="encryption_key_generated",
                details={
                    "corpus_type": corpus_type,
                    "key_id": key_metadata.key_id
                }
            )
            
        except Exception as e:
            raise EncryptionError(f"Failed to generate encryption key for {corpus_type}: {str(e)}")
            
    def _load_encryption_key(self, corpus_type: str, key_file: Path) -> None:
        """Load existing encryption key for a corpus type"""
        try:
            with open(key_file, 'r') as f:
                key_data = json.load(f)
                
            key_metadata = EncryptionKey(**key_data)
            
            # Recreate the key using stored salt
            master_password = self.settings.ENCRYPTION_MASTER_PASSWORD.encode()
            salt = base64.b64decode(key_metadata.salt.encode())
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(master_password))
            
            # Create Fernet instance
            fernet = Fernet(key)
            self._keys[corpus_type] = fernet
            
        except Exception as e:
            raise EncryptionError(f"Failed to load encryption key for {corpus_type}: {str(e)}")
            
    def _calculate_data_hash(self, data: Union[str, bytes]) -> str:
        """Calculate SHA-256 hash of data for integrity verification"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        return hashlib.sha256(data).hexdigest()
        
    def encrypt_personal_corpus(self, chatgpt_exports: List[Dict[str, Any]]) -> EncryptedCorpus:
        """
        Encrypt ChatGPT conversation exports (personal reasoning patterns).
        
        Args:
            chatgpt_exports: List of ChatGPT conversation data
            
        Returns:
            EncryptedCorpus: Encrypted personal corpus data
        """
        try:
            # Serialize data
            data_json = json.dumps(chatgpt_exports, ensure_ascii=False, separators=(',', ':'))
            data_bytes = data_json.encode('utf-8')
            
            # Calculate hash for integrity
            data_hash = self._calculate_data_hash(data_bytes)
            
            # Encrypt data
            fernet = self._keys["personal"]
            encrypted_data = fernet.encrypt(data_bytes)
            
            # Create encrypted corpus
            encrypted_corpus = EncryptedCorpus(
                corpus_type="personal",
                encrypted_data=base64.b64encode(encrypted_data).decode(),
                encryption_metadata={
                    "algorithm": "AES-256",
                    "mode": "Fernet",
                    "original_size": len(data_bytes),
                    "encrypted_size": len(encrypted_data),
                    "record_count": len(chatgpt_exports)
                },
                data_hash=data_hash
            )
            
            self.audit_logger.log_security_event(
                event_type="personal_corpus_encrypted",
                details={
                    "record_count": len(chatgpt_exports),
                    "original_size": len(data_bytes),
                    "encrypted_size": len(encrypted_data)
                }
            )
            
            return encrypted_corpus
            
        except Exception as e:
            raise EncryptionError(f"Failed to encrypt personal corpus: {str(e)}")
            
    def encrypt_social_corpus(self, social_data: List[Dict[str, Any]]) -> EncryptedCorpus:
        """
        Encrypt social media posts and interactions (public voice patterns).
        
        Args:
            social_data: List of social media data
            
        Returns:
            EncryptedCorpus: Encrypted social corpus data
        """
        try:
            # Serialize data
            data_json = json.dumps(social_data, ensure_ascii=False, separators=(',', ':'))
            data_bytes = data_json.encode('utf-8')
            
            # Calculate hash for integrity
            data_hash = self._calculate_data_hash(data_bytes)
            
            # Encrypt data
            fernet = self._keys["social"]
            encrypted_data = fernet.encrypt(data_bytes)
            
            # Create encrypted corpus
            encrypted_corpus = EncryptedCorpus(
                corpus_type="social",
                encrypted_data=base64.b64encode(encrypted_data).decode(),
                encryption_metadata={
                    "algorithm": "AES-256",
                    "mode": "Fernet",
                    "original_size": len(data_bytes),
                    "encrypted_size": len(encrypted_data),
                    "record_count": len(social_data)
                },
                data_hash=data_hash
            )
            
            self.audit_logger.log_security_event(
                event_type="social_corpus_encrypted",
                details={
                    "record_count": len(social_data),
                    "original_size": len(data_bytes),
                    "encrypted_size": len(encrypted_data)
                }
            )
            
            return encrypted_corpus
            
        except Exception as e:
            raise EncryptionError(f"Failed to encrypt social corpus: {str(e)}")
            
    def encrypt_published_corpus(self, articles: List[Dict[str, Any]]) -> EncryptedCorpus:
        """
        Encrypt published articles and content (professional voice patterns).
        
        Args:
            articles: List of published article data
            
        Returns:
            EncryptedCorpus: Encrypted published corpus data
        """
        try:
            # Serialize data
            data_json = json.dumps(articles, ensure_ascii=False, separators=(',', ':'))
            data_bytes = data_json.encode('utf-8')
            
            # Calculate hash for integrity
            data_hash = self._calculate_data_hash(data_bytes)
            
            # Encrypt data
            fernet = self._keys["published"]
            encrypted_data = fernet.encrypt(data_bytes)
            
            # Create encrypted corpus
            encrypted_corpus = EncryptedCorpus(
                corpus_type="published",
                encrypted_data=base64.b64encode(encrypted_data).decode(),
                encryption_metadata={
                    "algorithm": "AES-256",
                    "mode": "Fernet",
                    "original_size": len(data_bytes),
                    "encrypted_size": len(encrypted_data),
                    "record_count": len(articles)
                },
                data_hash=data_hash
            )
            
            self.audit_logger.log_security_event(
                event_type="published_corpus_encrypted",
                details={
                    "record_count": len(articles),
                    "original_size": len(data_bytes),
                    "encrypted_size": len(encrypted_data)
                }
            )
            
            return encrypted_corpus
            
        except Exception as e:
            raise EncryptionError(f"Failed to encrypt published corpus: {str(e)}")
            
    def decrypt_corpus(self, encrypted_corpus: EncryptedCorpus) -> List[Dict[str, Any]]:
        """
        Decrypt corpus data and verify integrity.
        
        Args:
            encrypted_corpus: Encrypted corpus data
            
        Returns:
            List[Dict[str, Any]]: Decrypted corpus data
        """
        try:
            corpus_type = encrypted_corpus.corpus_type
            
            if corpus_type not in self._keys:
                raise DecryptionError(f"No encryption key available for corpus type: {corpus_type}")
                
            # Decode and decrypt data
            encrypted_data = base64.b64decode(encrypted_corpus.encrypted_data.encode())
            fernet = self._keys[corpus_type]
            decrypted_bytes = fernet.decrypt(encrypted_data)
            
            # Verify data integrity
            calculated_hash = self._calculate_data_hash(decrypted_bytes)
            if calculated_hash != encrypted_corpus.data_hash:
                raise DecryptionError("Data integrity check failed - hash mismatch")
                
            # Deserialize data
            data_json = decrypted_bytes.decode('utf-8')
            corpus_data = json.loads(data_json)
            
            self.audit_logger.log_security_event(
                event_type="corpus_decrypted",
                details={
                    "corpus_type": corpus_type,
                    "record_count": len(corpus_data),
                    "data_size": len(decrypted_bytes)
                }
            )
            
            return corpus_data
            
        except Exception as e:
            raise DecryptionError(f"Failed to decrypt {encrypted_corpus.corpus_type} corpus: {str(e)}")
            
    def rotate_encryption_keys(self, corpus_type: Optional[str] = None) -> None:
        """
        Rotate encryption keys for security.
        
        Args:
            corpus_type: Specific corpus type to rotate, or None for all
        """
        try:
            corpus_types = [corpus_type] if corpus_type else ["personal", "social", "published"]
            
            for ctype in corpus_types:
                # Generate new key
                key_file = Path(self.settings.ENCRYPTION_KEY_PATH) / f"{ctype}_key.json"
                old_key_file = Path(self.settings.ENCRYPTION_KEY_PATH) / f"{ctype}_key_old.json"
                
                # Backup old key
                if key_file.exists():
                    key_file.rename(old_key_file)
                    
                # Generate new key
                self._generate_encryption_key(ctype, key_file)
                
                self.audit_logger.log_security_event(
                    event_type="encryption_key_rotated",
                    details={"corpus_type": ctype}
                )
                
        except Exception as e:
            raise EncryptionError(f"Failed to rotate encryption keys: {str(e)}")
            
    def verify_encryption_integrity(self) -> Dict[str, bool]:
        """
        Verify encryption system integrity.
        
        Returns:
            Dict[str, bool]: Integrity status for each corpus type
        """
        integrity_status = {}
        
        for corpus_type in ["personal", "social", "published"]:
            try:
                # Test encryption/decryption cycle
                test_data = [{"test": "data", "timestamp": datetime.utcnow().isoformat()}]
                
                if corpus_type == "personal":
                    encrypted = self.encrypt_personal_corpus(test_data)
                elif corpus_type == "social":
                    encrypted = self.encrypt_social_corpus(test_data)
                else:
                    encrypted = self.encrypt_published_corpus(test_data)
                    
                decrypted = self.decrypt_corpus(encrypted)
                
                # Verify data matches
                integrity_status[corpus_type] = (decrypted == test_data)
                
            except Exception:
                integrity_status[corpus_type] = False
                
        return integrity_status


__all__ = [
    "PersonalDataEncryption",
    "EncryptedCorpus", 
    "EncryptionKey"
]
