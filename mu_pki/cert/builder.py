import datetime as dt
from pathlib import Path

from cryptography import x509
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID, ObjectIdentifier

from mu_pki.globals import G
from mu_pki.menu import sel_menu, sel_sl, sel_sl_with_default, show_ekus
from mu_pki.menu.item import ChoiceItem, Item
from mu_pki.menu.item_provider import ChoiceItemProvider, ItemProvider

from .meta import CRT_EXT

PKI_ENDPOINT = f"https://c.{G.ORG}/pki/"

T_NOW = dt.datetime.now(dt.timezone.utc)
T_LAST_GRID = dt.datetime(year=T_NOW.year // 4 * 4, month=G.T_MONTH, day=G.T_DAY)


KU_CA = x509.KeyUsage(
    digital_signature=False,
    content_commitment=False,
    key_encipherment=False,
    data_encipherment=False,
    key_agreement=False,
    key_cert_sign=True,
    crl_sign=True,
    encipher_only=False,
    decipher_only=False,
)


def root_ca_csr():
    subject = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, f"{G.ORG} Root CA"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, G.ORG),
        ]
    )
    return (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .serial_number(x509.random_serial_number())
        .not_valid_before(G.T_ORIGIN)
        .not_valid_after(G.T_ORIGIN + dt.timedelta(days=365 * 400 + 24 * 4 + 1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(KU_CA, critical=True)
    )


def sub(name: str, isCA: bool | None):
    if isCA:
        cn_ = f"{G.ORG} {name.capitalize()} CA"
    else:
        cn_ = name

    return x509.Name(
        {
            x509.NameAttribute(NameOID.COMMON_NAME, sel_sl_with_default("CN", cn_)),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, G.ORG),
        }
    )


def ku(isCA: bool | None):
    if isCA:
        return KU_CA

    else:
        return x509.KeyUsage(
            digital_signature=True,
            content_commitment=True,
            key_encipherment=False,
            data_encipherment=False,
            key_agreement=True,
            key_cert_sign=False,
            crl_sign=False,
            encipher_only=False,
            decipher_only=False,
        )


def exp(isCA: bool | None):
    if isCA:
        lifetime = 12
    else:
        lifetime = 4

    return dt.datetime(year=T_LAST_GRID.year + lifetime, month=G.T_MONTH, day=G.T_DAY)


def crl_dp(path: str | Path) -> x509.CRLDistributionPoints:
    return x509.CRLDistributionPoints(
        {
            x509.DistributionPoint(
                full_name={x509.UniformResourceIdentifier(PKI_ENDPOINT + f"{path}.crl")},
                relative_name=None,
                reasons=None,
                crl_issuer=None,
            )
        }
    )


def aia(path: str | Path) -> x509.AuthorityInformationAccess:
    return x509.AuthorityInformationAccess(
        {
            x509.AccessDescription(
                x509.OID_CA_ISSUERS,
                x509.UniformResourceIdentifier(PKI_ENDPOINT + f"{path}.{CRT_EXT}"),
            )
        }
    )


class EkuChoiceItem(ChoiceItem):
    def __init__(self, text: str, init_state: bool) -> None:
        self.__oid = ObjectIdentifier(text)
        text = f"{self.__oid.dotted_string} ({self.__oid._name})"
        super().__init__(text, init_state)


_COMMON_EKU = {
    ExtendedKeyUsageOID.SERVER_AUTH,
    ExtendedKeyUsageOID.CLIENT_AUTH,
    ExtendedKeyUsageOID.CODE_SIGNING,
    ExtendedKeyUsageOID.EMAIL_PROTECTION,
    ExtendedKeyUsageOID.TIME_STAMPING,
    ExtendedKeyUsageOID.OCSP_SIGNING,
    ExtendedKeyUsageOID.SMARTCARD_LOGON,
    ExtendedKeyUsageOID.KERBEROS_PKINIT_KDC,
    ExtendedKeyUsageOID.IPSEC_IKE,
    ExtendedKeyUsageOID.BUNDLE_SECURITY,
    ExtendedKeyUsageOID.CERTIFICATE_TRANSPARENCY,
}

COMMON_EKU = {EkuChoiceItem(eku.dotted_string, False) for eku in _COMMON_EKU}
_EKU_OPT = {"a", "y"}


def eku(init_ekus: list[str]):
    opt_itp = ItemProvider()
    opt_itp.append(Item("a - add extra"))
    opt_itp.append(Item("y - confirm"))

    ekus_itp = ChoiceItemProvider(COMMON_EKU)  # type: ignore
    for eku in init_ekus:
        ekus_itp.extra(EkuChoiceItem(eku, True))

    while True:
        show_ekus(opt_itp, ekus_itp)
        sel = sel_menu(_EKU_OPT, ekus_itp)

        if sel == "y":
            return [ObjectIdentifier(eku._text) for eku in ekus_itp.items if eku.state]

        elif sel == "a":
            oid = sel_sl("OID")
            ekus_itp.extra(EkuChoiceItem(oid, True))

        else:
            assert isinstance(sel, int)
            ekus_itp.input(sel)
