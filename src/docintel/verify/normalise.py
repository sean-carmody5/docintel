"""Canonical forms for matching the same product across suppliers.

Deliberately conservative: strip salts and spelling variants that never change the
molecule, map a short list of well-known synonyms, and leave anything unknown as
is. A wrong merge costs more than a missed one, because a reviewer sees two rows
side by side either way.
"""

from __future__ import annotations

import re

_SALTS = (
    "hydrochloride",
    "hydrochlorid",
    "hcl",
    "sodium",
    "potassium",
    "calcium",
    "besylate",
    "besilate",
    "maleate",
    "mesylate",
    "sulfate",
    "sulphate",
    "trihydrate",
    "dihydrate",
    "monohydrate",
    "phosphate",
    "acetate",
    "tartrate",
    "citrate",
    "fumarate",
    "succinate",
    "disoproxil",
    "digluconate",
    "as potassium clavulanate",
    "elemental fe",
    "elemental",
)
_SYNONYMS = {
    "acetaminophen": "paracetamol",
    "albuterol": "salbutamol",
    "lignocaine": "lidocaine",
    "co-trimoxazole": "sulfamethoxazole+trimethoprim",
    "cotrimoxazole": "sulfamethoxazole+trimethoprim",
    "co-amoxiclav": "amoxicillin+clavulanic acid",
    "amoxiclav": "amoxicillin+clavulanic acid",
    "clavulanate": "clavulanic acid",
    "tld": "dolutegravir+lamivudine+tenofovir",
    "tdf/3tc/dtg": "dolutegravir+lamivudine+tenofovir",
    "al": "artemether+lumefantrine",
    "rh": "isoniazid+rifampicin",
    "rhze": "ethambutol+isoniazid+pyrazinamide+rifampicin",
    "4fdc": "ethambutol+isoniazid+pyrazinamide+rifampicin",
    "ors": "oral rehydration salts",
    "vitamin a": "retinol",
    "insulin human (soluble)": "insulin human",
}
_COMPONENT_ABBREVIATIONS = {
    "tdf": "tenofovir",
    "3tc": "lamivudine",
    "dtg": "dolutegravir",
    "efv": "efavirenz",
    "nvp": "nevirapine",
    "azt": "zidovudine",
    "abc": "abacavir",
    "ftc": "emtricitabine",
    "lpv": "lopinavir",
    "rtv": "ritonavir",
}
_SEPARATORS = re.compile(r"\s*(\+|/|,| and | with | & )\s*", re.I)
_PARENS = re.compile(r"\([^)]*\)")

_FORM_BASE = (
    ("inhal", "inhaler"),
    ("suspension", "suspension"),
    ("syrup", "syrup"),
    ("oral solution", "syrup"),
    ("powder for oral", "suspension"),
    ("dry syrup", "suspension"),
    ("injection", "injection"),
    ("injectable", "injection"),
    ("solution for inj", "injection"),
    ("powder for", "injection"),
    ("pre-filled pen", "injection"),
    ("pen", "injection"),
    ("vial", "injection"),
    ("ampoule", "injection"),
    ("capsule", "capsule"),
    ("caps", "capsule"),
    ("sachet", "sachet"),
    ("powder for oral solution", "sachet"),
    ("gel", "gel"),
    ("cream", "cream"),
    ("ointment", "ointment"),
    ("drops", "drops"),
    ("tab", "tablet"),
)


def normalise_inn(inn: str | None) -> str | None:
    if not inn:
        return None
    text = _PARENS.sub(" ", inn.lower())
    text = re.sub(r"\b\d+(\.\d+)?\s*(mg|mcg|g|ml|iu|%)\b", " ", text)
    parts = [p.strip() for p in _SEPARATORS.split(text) if p and p.strip()]
    parts = [p for p in parts if p not in ("+", "/", ",", "and", "with", "&")]
    out: list[str] = []
    for part in parts:
        part = _SYNONYMS.get(part.strip(), part)
        for sub in part.split("+"):
            words = [w for w in re.split(r"[\s\-]+", sub) if w]
            words = [w for w in words if w not in _SALTS and not w.isdigit()]
            cleaned = " ".join(words).strip()
            cleaned = _SYNONYMS.get(cleaned, cleaned)
            cleaned = _COMPONENT_ABBREVIATIONS.get(cleaned, cleaned)
            if cleaned:
                out.extend(c.strip() for c in cleaned.split("+"))
    return "+".join(sorted(set(out))) or None


def normalise_strength(strength: str | None) -> str | None:
    if not strength:
        return None
    s = strength.lower().replace("micrograms", "mcg").replace("µg", "mcg").replace("μg", "mcg")
    s = s.replace("i.u.", "iu").replace("units", "iu")
    s = re.sub(r"(\d)\s*(mg|mcg|g|ml|iu|%)", r"\1 \2", s)
    s = re.sub(r"\s*/\s*", "/", s)
    s = re.sub(r"\s+", " ", s).strip()
    # 0.5 g -> 500 mg, 1 g stays
    s = re.sub(r"\b0\.(\d+) g\b", lambda m: f"{int(round(float('0.' + m.group(1)) * 1000))} mg", s)
    return s or None


def normalise_form(form: str | None) -> str | None:
    if not form:
        return None
    f = form.lower()
    for needle, base in _FORM_BASE:
        if needle in f:
            return base
    return f.split(",")[0].strip() or None
