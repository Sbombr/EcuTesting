# Mac Algorithms

import hmac
import hashlib
from Crypto.Hash import CMAC, KMAC128
from Crypto.Cipher import AES


class Mac:
    name = "none"

    def __init__(self, key: bytes, tag_len: int = 16):
        self.key = key
        self.tag_len = 0 if self.name == "none" else tag_len

    def compute(self, data: bytes) -> bytes:
        return b""

    def verify(self, data: bytes, tag: bytes) -> bool:
        return hmac.compare_digest(self.compute(data), tag)


class HmacSha256(Mac):
    name = "hmac-sha256"
    def compute(self, data):
        return hmac.new(self.key, data, hashlib.sha256).digest()[:self.tag_len]


class HmacSha512(Mac):
    name = "hmac-sha512"
    def compute(self, data):
        return hmac.new(self.key, data, hashlib.sha512).digest()[:self.tag_len]


class AesCmac(Mac):
    name = "aes-cmac"
    def compute(self, data):
        # AES block size caps the tag at 16 bytes
        return CMAC.new(self.key, msg=data, ciphermod=AES).digest()[:self.tag_len]


class Kmac128(Mac):
    name = "kmac128"
    def compute(self, data):
        # pycryptodome requires mac_len >= 8
        return KMAC128.new(key=self.key, data=data,
                           mac_len=self.tag_len, custom=b"CAN-RPM").digest()


ALGORITHMS = {c.name: c for c in (Mac, HmacSha256, HmacSha512, AesCmac, Kmac128)}


def get_mac(name: str, key: bytes, tag_len: int = 16) -> Mac:
    return ALGORITHMS[name](key, tag_len)