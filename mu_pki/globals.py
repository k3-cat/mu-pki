import base64
import datetime as dt
import os
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric import ec
from dotenv import load_dotenv
from wcwidth import wcswidth

load_dotenv()


class G:
    ROOT_DIR = Path(__file__).parents[1]
    ROOT_NAME = "k1"

    ORG = os.getenv("ORG", "")

    EC_CURVE = ec.SECP256R1()

    T_MONTH = 8
    T_DAY = 24
    T_ORIGIN = dt.datetime(year=2000, month=T_MONTH, day=T_DAY, tzinfo=dt.timezone.utc)

    ENC_KEY = base64.b64decode(os.getenv("ENC_KEY", ""))

    COL_SPACER = "  "
    IDX_SPACER = ". "
    IDENT = wcswidth(COL_SPACER) // 2 + 1
