import datetime as dt
import difflib
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Mapping, Sequence, overload

import pydantic as pd
import tomlkit
from tomlkit import items as tomlitems
from tomlkit.container import Container as TomlContainer

if TYPE_CHECKING:
    from .cert_wrapper import CertWrapper

FILE_NAME = "meta.toml"
FILE_MODE = 0o644
CRT_EXT = "crt"


@dataclass
class CertInfo:
    id: int
    exp: dt.datetime

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, CertInfo):
            return False

        return self.id.__eq__(value.id)

    def __hash__(self) -> int:
        return self.id.__hash__()


def apply_sequence_diff(toml: tomlitems.Array, original: Sequence, current: Sequence):
    # TODO: comments / reordering support
    diff = difflib.SequenceMatcher(None, original, current)
    toml.multiline(True)
    for _, ref_s, _, s, e in (op for op in diff.get_opcodes() if op[0] == "insert"):
        for i in range(e, s, -1):
            toml.insert(ref_s, current[i - 1])

    for _, ref_s, ref_e, s, e in (op for op in diff.get_opcodes() if op[0] == "replace"):
        for i, j in zip(range(ref_e, ref_s, -1), range(e, s, -1)):
            toml[i - 1] = current[j - 1]

    pending_del = [op for op in diff.get_opcodes() if op[0] == "delete"]
    pending_del.reverse()
    for _, ref_s, ref_e, _, _ in pending_del:
        for i in range(ref_e, ref_s, -1):
            toml.pop(i - 1)


def toml_from_dict(data: Mapping):
    toml = tomlkit.table()
    for k, v in data.items():
        if isinstance(v, Mapping):
            toml[k] = toml_from_dict(v)
        else:
            toml[k] = v

    return toml


# inspired by https://pypi.org/project/tomlantic/
@overload
def apply_model_diff(
    toml: TomlContainer | tomlitems.Table, original: Sequence, current: Sequence
) -> None: ...
@overload
def apply_model_diff(
    toml: TomlContainer | tomlitems.Table, original: Mapping, current: Mapping
) -> None: ...
def apply_model_diff(toml, original, current) -> None:
    for field in current.keys():
        val = current[field]
        if field not in original:
            toml[field] = toml_from_dict(val)
            continue

        ref = original[field]
        if isinstance(val, Mapping):
            if field not in toml:
                toml[field] = tomlkit.table()

            toml_part = toml[field]
            apply_model_diff(toml_part, ref, val)

        elif isinstance(val, Sequence):
            if field not in toml:
                toml[field] = tomlkit.array()

            toml_part = toml[field]
            apply_sequence_diff(toml_part, ref, val)

        elif val != ref:
            toml.update({field: val})


class Meta(pd.BaseModel):
    model_config = pd.ConfigDict(validate_assignment=True)
    _origin: dict
    _toml: tomlkit.TOMLDocument
    _cp: "CertWrapper"
    _file_path: Path

    certs: dict[str, CertInfo] = pd.Field(default_factory=dict)
    ca: list[int] = pd.Field(default_factory=list)
    miss: list[int] = pd.Field(default_factory=list)
    crl: list[CertInfo] = pd.Field(default_factory=list)

    ekus: list[str] = pd.Field(default_factory=list)

    @staticmethod
    def init_from(cp: "CertWrapper"):
        file_path = cp.sub_dir / FILE_NAME
        if not file_path.is_file():
            toml_doc = tomlkit.document()

        else:
            with file_path.open("r") as fp:
                toml_doc = tomlkit.load(fp)

        model = Meta.model_validate(toml_doc.unwrap())
        model._origin = model.model_dump()
        model._toml = toml_doc
        model._cp = cp
        model._file_path = file_path

        return model

    def clean_extra(self):
        known = {v.id for _, v in self.certs.items()}
        self.ca = list(set(self.ca) & known)
        self.miss = list(set(self.miss) & known)

    def clean_crl(self):
        now = dt.datetime.now()
        expired_info = {info for info in self.crl if info.exp < now}
        self.crl = list(set(self.crl) - expired_info)

    def update(self):
        now = dt.datetime.now(tz=dt.timezone.utc)

        known = {n for n in self.certs.keys()}
        existing = {p.stem for p in self._cp.sub_dir.glob(f"*.{CRT_EXT}")}
        missing = set(self.miss)
        missing.update(self.certs[name].id for name in (known - existing))

        for name in existing:
            sub_cp = self._cp.get_child(name)
            sub_cp.load()
            if sub_cp.akid and sub_cp.akid.key_identifier != self._cp.skid.key_identifier:
                raise ValueError("cert '{}' is from an unknown ca".format(sub_cp.path))

            info = CertInfo(sub_cp.cert.serial_number, sub_cp.cert.not_valid_after_utc)
            if info in self.crl:
                self.certs.pop(name, None)
                continue

            if sub_cp.cert.not_valid_after_utc < now:
                sub_cp.renew()
                continue

            # renamed, id must be the same as searched via recorded id
            if info.id in missing:
                missing.remove(info.id)

            # record valid but missmatch
            elif (name in known) and ((record := self.certs[name]) != info):
                self.crl.append(record)

            self.certs[name] = info
            if sub_cp.isCA:
                self.ca.append(info.id)

            else:
                if info.id in self.ca:
                    self.ca.remove(info.id)

        self.miss = list(missing)

        # clean renamed record
        for name in (n for n in (known - existing) if self.certs[n].id not in missing):
            self.certs.pop(name)

        self.clean_crl()
        self.clean_extra()
        self.save()

    def save(self):
        toml_doc = deepcopy(self._toml)
        current_model = self.model_dump()
        apply_model_diff(toml_doc, self._origin, current_model)
        self._toml = toml_doc
        self._origin = current_model

        with self._file_path.open("w") as fp:
            tomlkit.dump(toml_doc, fp)

        self._file_path.chmod(FILE_MODE)
