"""Convert parsed HL7 message to VetFlow XML format (<wynik>)."""

from __future__ import annotations

from datetime import datetime
from xml.etree import ElementTree as ET

try:
    from .hl7_parser import HL7Message
except ImportError:
    from hl7_parser import HL7Message

# Map HL7 sex codes to Polish
SEX_MAP = {
    "M": "samiec",
    "F": "samica",
    "MN": "samiec kastrowany",
    "FS": "samica sterylizowana",
    "U": "",
}

# Map species codes to Polish
SPECIES_MAP = {
    "DOG": "Pies",
    "CAT": "Kot",
    "CANINE": "Pies",
    "FELINE": "Kot",
}

# Device type → sample type
SAMPLE_TYPE_MAP = {
    "cbc": "krew EDTA",
    "chemistry": "surowica",
}

# Device → lab name
LAB_NAME_MAP = {
    "VM100": "Skyla VM100 (CBC)",
    "Tutti": "Skyla Tutti (Chemistry)",
}


def _format_timestamp(ts: str) -> str:
    """Convert HL7 timestamp (YYYYMMDDHHMMSS) to ISO format."""
    ts = ts.strip()
    if not ts:
        return datetime.now().isoformat()

    # Try various HL7 timestamp lengths
    for fmt, length in [
        ("%Y%m%d%H%M%S", 14),
        ("%Y%m%d%H%M", 12),
        ("%Y%m%d", 8),
    ]:
        if len(ts) >= length:
            try:
                return datetime.strptime(ts[:length], fmt).isoformat()
            except ValueError:
                continue

    return datetime.now().isoformat()


def _normalize_sex(sex: str) -> str:
    """Normalize HL7 sex code to Polish."""
    return SEX_MAP.get(sex.upper().strip(), sex)


def _normalize_species(species: str) -> str:
    """Normalize species code to Polish."""
    upper = species.upper().strip()
    return SPECIES_MAP.get(upper, species)


def _normalize_ref_range(ref_range: str) -> str:
    """Normalize HL7 reference range (e.g., '5.5-19.5' or '5.5 TO 19.5')."""
    return ref_range.replace(" TO ", "-").replace(" to ", "-")


def hl7_to_vetflow_xml(msg: HL7Message) -> str:
    """Convert parsed HL7Message to VetFlow-compatible XML string.

    The output XML follows the <wynik> format expected by
    VetFlow's /api/clinic/lab-results/import endpoint.

    Args:
        msg: Parsed HL7 message.

    Returns:
        XML string with <?xml?> declaration.
    """
    root = ET.Element("wynik")

    # <dostawca> — lab/device info
    ET.SubElement(
        root,
        "dostawca",
        nazwa=LAB_NAME_MAP.get(msg.device, f"Skyla {msg.device}"),
    )

    # <nr_badania> — message ID as order number
    nr = ET.SubElement(root, "nr_badania")
    nr.text = msg.message_id or f"{msg.device}-{msg.timestamp}"

    # <data_badania> — test timestamp
    data = ET.SubElement(root, "data_badania")
    data.text = _format_timestamp(msg.timestamp)

    # <rodzaj_probki> — sample type based on device
    probka = ET.SubElement(root, "rodzaj_probki")
    probka.text = SAMPLE_TYPE_MAP.get(msg.device_type, "")

    # <pacjent> — patient info
    patient_attrs = {"imie": msg.patient.name}
    if msg.patient.species:
        patient_attrs["gatunek"] = _normalize_species(msg.patient.species)
    if msg.patient.sex:
        patient_attrs["plec"] = _normalize_sex(msg.patient.sex)
    if msg.patient.birthday:
        patient_attrs["data_urodzenia"] = msg.patient.birthday
    if msg.patient.patient_id:
        patient_attrs["id"] = msg.patient.patient_id
    patient_attrs["mikrochip"] = ""  # HL7 doesn't carry microchip
    ET.SubElement(root, "pacjent", **patient_attrs)

    # <badanie> — test panel with parameters
    badanie = ET.SubElement(root, "badanie", nazwa=msg.panel_name or "HL7 Results")

    for r in msg.results:
        param_attrs = {
            "nazwa": r.name or r.abbreviation,
            "jednostka": r.unit,
            "norma": _normalize_ref_range(r.reference_range),
            "uwagi": _flag_to_note(r.flag),
        }
        param_el = ET.SubElement(badanie, "parametr", **param_attrs)
        param_el.text = r.value

    # Build XML string
    ET.indent(root, space="  ")
    xml_str = ET.tostring(root, encoding="unicode", xml_declaration=False)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_str}'


def _flag_to_note(flag: str) -> str:
    """Convert HL7 abnormal flag to human-readable note."""
    flag_map = {
        "H": "powyżej normy",
        "L": "poniżej normy",
        "HH": "krytycznie wysoki",
        "LL": "krytycznie niski",
        "A": "nieprawidłowy",
    }
    return flag_map.get(flag.upper().strip(), "")
