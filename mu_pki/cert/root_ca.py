from pathlib import Path

from cryptography.hazmat.primitives import hashes

from mu_pki.globals import G

from . import builder
from .cert_wrapper import CertWrapper


def load_or_init_root_ca():
    root = CertWrapper(Path(G.ROOT_NAME), G.ROOT_NAME)

    if root.file_path.is_file():
        root.load()

    else:
        root.key.generate()

        csr = (
            builder.root_ca_csr()
            .public_key(root.key.pub)
            .add_extension(root.key.skid, critical=False)
        )

        root.cert = csr.sign(root.key.pvt, hashes.SHA256())
        root.dump()

    return root
