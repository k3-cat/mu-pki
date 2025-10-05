from functools import cached_property
from pathlib import Path
from typing import Self

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization as ser
from cryptography.x509.extensions import ExtensionNotFound, ExtensionTypeVar

from mu_pki.globals import G

from . import builder
from .key_wrapper import KeyWrapper
from .meta import CRT_EXT, CertInfo, Meta

FOLDER_MODE = 0o750
FILE_MODE = 0o640

SKIPED_OID = {
    x509.OID_AUTHORITY_INFORMATION_ACCESS,
    x509.OID_AUTHORITY_KEY_IDENTIFIER,
    x509.OID_CRL_DISTRIBUTION_POINTS,
}


class CertWrapper:
    def __init__(self, parent: Self | Path, name: str) -> None:
        self.name = name
        if isinstance(parent, CertWrapper):
            self.parent = parent
            self.path = parent.path / name

        else:
            self.parent = self
            self.path = parent

        self.key = KeyWrapper(self.path)
        self.cert: x509.Certificate = None  # type: ignore
        self.meta: Meta

    @cached_property
    def sub_dir(self):
        return G.ROOT_DIR / self.path

    @cached_property
    def file_path(self):
        return G.ROOT_DIR / f"{self.path}.{CRT_EXT}"

    @cached_property
    def sha256(self):
        return self.cert.fingerprint(hashes.SHA256())

    @cached_property
    def sub(self):
        cns = self.cert.subject.get_attributes_for_oid(x509.OID_COMMON_NAME)
        if cns:
            return " | ".join(n if isinstance((n := cn.value), str) else "<binary>" for cn in cns)

        return self.cert.subject

    @cached_property
    def skid(self):
        if self.key:
            return self.key.skid

        return self.cert.extensions.get_extension_for_class(x509.SubjectKeyIdentifier).value

    @cached_property
    def akid(self):
        return self.get_ext(x509.AuthorityKeyIdentifier)

    @cached_property
    def isCA(self):
        return self.cert.extensions.get_extension_for_class(x509.BasicConstraints).value.ca

    # ---
    def get_ext(self, cls: type[ExtensionTypeVar]):
        try:
            return self.cert.extensions.get_extension_for_class(cls).value
        except ExtensionNotFound:
            return None

    def get_child(self, name: str):
        return CertWrapper(self, name)

    def fix_fs(self):
        if self.isCA:
            self.sub_dir.mkdir(mode=FOLDER_MODE, parents=True, exist_ok=True)
            self.sub_dir.chmod(FOLDER_MODE)

        elif self.sub_dir.is_dir():
            self.sub_dir.rmdir()

        self.file_path.chmod(FILE_MODE)

    def load(self):
        if self.cert:
            return

        if not self.file_path.is_file():
            raise FileNotFoundError("Missing cert file '{}'.".format(self.path))

        with self.file_path.open("rb") as fp:
            self.cert = x509.load_pem_x509_certificate(fp.read())

        self.key.skid = self.skid

        self.fix_fs()
        if self.isCA:
            self.meta = Meta.init_from(self)

    def dump(self):
        with self.file_path.open("wb") as fp:
            fp.write(self.cert.public_bytes(ser.Encoding.PEM))

        self.fix_fs()

    def create(self, isCA: bool):
        if self.file_path.is_file():
            raise FileExistsError("Cert '{}' exists.".format(self.path))

        self.key.generate()

        csr = (
            x509.CertificateBuilder()
            .subject_name(builder.sub(self.name, isCA))
            .public_key(self.key.pub)
            .not_valid_before(builder.T_LAST_GRID)
            .not_valid_after(builder.exp(isCA))
            .add_extension(x509.BasicConstraints(ca=isCA, path_length=None), critical=True)
            .add_extension(builder.ku(isCA), critical=True)
            .add_extension(self.key.skid, critical=False)
        )
        if not isCA and (ekus := builder.eku(self.parent.meta.ekus)):
            self.meta.ekus = [eku.dotted_string for eku in ekus]
            self.meta.save()
            csr = csr.add_extension(x509.ExtendedKeyUsage(ekus), critical=False)

        self.cert = self.parent.sign_csr(self.path, csr)
        self.dump()
        if isCA:
            self.meta = Meta.init_from(self)

    def renew(self):
        csr = (
            x509.CertificateBuilder()
            .subject_name(self.cert.subject)
            .public_key(self.key.pub)
            .not_valid_before(builder.T_LAST_GRID)
            .not_valid_after(builder.exp(self.isCA))
        )

        for ext in (ext for ext in self.cert.extensions if ext.oid not in SKIPED_OID):
            csr.add_extension(ext.value, ext.critical)

        self.cert = self.parent.sign_csr(self.path, csr)
        self.dump()

    def sign_csr(self, path: Path, csr: x509.CertificateBuilder):
        if not self.isCA:
            raise Exception("cert '{}' is not a ca".format(self.path))

        csr = (
            csr.serial_number(x509.random_serial_number())
            .issuer_name(self.cert.subject)
            .add_extension(
                x509.AuthorityKeyIdentifier.from_issuer_subject_key_identifier(self.skid),
                critical=False,
            )
            .add_extension(builder.aia(self.path), critical=False)
            .add_extension(builder.crl_dp(self.path), critical=False)
        )

        self.key.load()

        cert = csr.sign(self.key.pvt, hashes.SHA256())

        self.meta.certs[path.name] = CertInfo(cert.serial_number, cert.not_valid_after_utc)
        self.meta.save()

        return cert
