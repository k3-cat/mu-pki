from functools import cached_property
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import serialization as ser
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.types import CertificateIssuerPrivateKeyTypes

from mu_pki.globals import G

from . import safe_storage

KEY_EXT = "key"
FILE_MODE = 0x740


class KeyWrapper:
    def __init__(self, path: Path, tag: bytes | None = None) -> None:
        self.path = path
        self.tag = tag

        self.pvt: CertificateIssuerPrivateKeyTypes = None  # type: ignore

    def __bool__(self):
        return bool(self.pvt)

    @cached_property
    def file_path(self):
        return G.ROOT_DIR / f"{self.path}.{KEY_EXT}"

    @cached_property
    def pem(self):
        return self.pvt.private_bytes(ser.Encoding.PEM, ser.PrivateFormat.PKCS8, ser.NoEncryption())

    @cached_property
    def pub(self):
        return self.pvt.public_key()

    @cached_property
    def skid(self):
        return x509.SubjectKeyIdentifier.from_public_key(self.pub)

    @property
    def aad(self):
        if self.tag:
            return self.tag

        return self.skid.key_identifier

    def dump(self):
        with self.file_path.open("wb") as fp:
            safe_storage.write_key(fp, self.pvt, self.aad)

        self.file_path.chmod(FILE_MODE)

    def load(self):
        if self.pvt:
            return

        if not self.file_path.is_file():
            raise FileNotFoundError(
                "Missing key file '{}' (but a valid cert exist).".format(self.path)
            )

        self.file_path.chmod(FILE_MODE)
        with self.file_path.open("rb") as fp:
            self.pvt, need_upgrade = safe_storage.read_key(fp, self.aad)

        if need_upgrade:
            self.dump()

    def generate(self):
        if self.file_path.is_file():
            raise FileExistsError(("Key '{}' exists.").format(self.path))

        self.pvt = ec.generate_private_key(G.EC_CURVE)
        self.dump()
