import base64
import os
from typing import BinaryIO

from cryptography.hazmat.primitives import serialization as ser
from cryptography.hazmat.primitives.asymmetric.types import CertificateIssuerPrivateKeyTypes
from cryptography.hazmat.primitives.ciphers.aead import AESGCMSIV

from mu_pki.globals import G

VER_FLAG = b"PKI2025OCT\n"

ENC_KEY_SIZE = 128 // 8
IV_SIZE = 12


def read_key(fp: BinaryIO, aad: bytes | None):
    need_upgrade = False
    if (flag := fp.readline()) != VER_FLAG:
        key = ser.load_pem_private_key(flag + fp.read(), None)
        need_upgrade = True

    else:
        aes = AESGCMSIV(G.ENC_KEY)
        key_der = aes.decrypt(
            base64.z85decode(fp.readline()[:-1]),
            base64.z85decode(fp.readline()[:-1]),
            aad,
        )
        key = ser.load_der_private_key(key_der, None)

    assert isinstance(key, CertificateIssuerPrivateKeyTypes)
    return key, need_upgrade


def write_key(fp: BinaryIO, key: CertificateIssuerPrivateKeyTypes, aad: bytes | None):
    aes = AESGCMSIV(G.ENC_KEY)
    iv = os.urandom(IV_SIZE)
    key_cipher = aes.encrypt(
        iv,
        key.private_bytes(ser.Encoding.DER, ser.PrivateFormat.PKCS8, ser.NoEncryption()),
        aad,
    )

    fp.write(VER_FLAG)
    fp.write(base64.z85encode(iv))
    fp.write(b"\n")
    fp.write(base64.z85encode(key_cipher))
    fp.write(b"\n")
