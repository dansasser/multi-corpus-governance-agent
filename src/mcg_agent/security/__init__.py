"""
Security Module

Provides enterprise-grade security for personal voice data including:
- Personal data encryption for all corpora
- Voice pattern access control  
- Personal data audit trails
- Voice governance enforcement
- Zero Trust architecture
- WAF integration
"""

from .personal_data_encryption import PersonalDataEncryption, EncryptedCorpus, EncryptionKey

__all__ = [
    "PersonalDataEncryption",
    "EncryptedCorpus", 
    "EncryptionKey"
]

