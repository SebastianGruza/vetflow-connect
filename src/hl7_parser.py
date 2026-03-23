"""HL7 ORU^R01 parser for Skyla VM100 (CBC) and Tutti (Chemistry)."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("vetflow_connect")


@dataclass
class HL7Result:
    """Single test result parameter from OBX segment."""

    sequence: int
    value_type: str  # ST, NM, ED, TX
    abbreviation: str
    name: str
    value: str
    unit: str
    reference_range: str
    flag: str  # H, L, HH, LL, empty


@dataclass
class HL7Patient:
    """Patient info from PID segment."""

    patient_id: str = ""
    name: str = ""
    species: str = ""
    sex: str = ""
    birthday: str = ""
    age: str = ""


@dataclass
class HL7Message:
    """Parsed HL7 ORU^R01 message."""

    device: str = ""  # "VM100" or "Tutti"
    device_type: str = ""  # "cbc" or "chemistry"
    hl7_version: str = ""
    message_id: str = ""
    timestamp: str = ""
    patient: HL7Patient = field(default_factory=HL7Patient)
    panel_name: str = ""
    results: list[HL7Result] = field(default_factory=list)


def _split_field(field_value: str, separator: str = "^") -> list[str]:
    """Split HL7 field by component separator."""
    return field_value.split(separator)


def _get_field(fields: list[str], index: int) -> str:
    """Safely get field by index (1-based HL7 convention)."""
    if index < len(fields):
        return fields[index]
    return ""


def _parse_msh(fields: list[str]) -> dict:
    """Parse MSH (Message Header) segment."""
    sending_app = _get_field(fields, 2)  # MSH.3
    timestamp = _get_field(fields, 6)  # MSH.7
    message_type = _get_field(fields, 8)  # MSH.9
    message_id = _get_field(fields, 9)  # MSH.10
    version = _get_field(fields, 11)  # MSH.12

    # Detect device from MSH.3
    sending_app_lower = sending_app.lower()
    if "vm100" in sending_app_lower:
        device = "VM100"
        device_type = "cbc"
    elif "tutti" in sending_app_lower or "skyla" in sending_app_lower:
        device = "Tutti"
        device_type = "chemistry"
    else:
        device = sending_app
        device_type = "unknown"

    return {
        "device": device,
        "device_type": device_type,
        "hl7_version": version,
        "message_id": message_id,
        "timestamp": timestamp,
    }


def _parse_pid_vm100(fields: list[str]) -> HL7Patient:
    """Parse PID for VM100 format.

    PID|1||||||birthday|sex|pet_name|species
    """
    birthday = _get_field(fields, 7)
    sex = _get_field(fields, 8)
    name = _get_field(fields, 9)
    species = _get_field(fields, 10)
    return HL7Patient(
        name=name,
        species=species,
        sex=sex,
        birthday=birthday,
    )


def _parse_pid_tutti(fields: list[str]) -> HL7Patient:
    """Parse PID for Tutti format.

    PID|1||patient_id||pet_name||^age_qty^age_unit|sex
    """
    patient_id = _get_field(fields, 3)
    name = _get_field(fields, 5)
    age_parts = _split_field(_get_field(fields, 7))
    age = f"{age_parts[1]} {age_parts[2]}" if len(age_parts) >= 3 else ""
    sex = _get_field(fields, 8)
    return HL7Patient(
        patient_id=patient_id,
        name=name,
        sex=sex,
        age=age.strip(),
    )


def _parse_pv1(fields: list[str]) -> str:
    """Parse PV1 — extract patient_id from PV1.5 (VM100)."""
    return _get_field(fields, 5)


def _parse_obr(fields: list[str]) -> str:
    """Parse OBR — extract panel name from OBR.4."""
    panel_field = _get_field(fields, 4)
    parts = _split_field(panel_field)
    # Return full name if available, otherwise abbreviation
    return parts[1] if len(parts) > 1 else parts[0]


def _parse_obx(fields: list[str]) -> HL7Result | None:
    """Parse OBX (Observation) segment.

    VM100: OBX|seq|ST|param_abbrev^param_name||value|unit|ref_range|flag|||F
    Tutti: OBX|seq|NM|param_abbrev||value|unit|ref_range|flag|||F|||||operator|serial|specimen|timestamp
    """
    sequence = _get_field(fields, 1)
    value_type = _get_field(fields, 2)

    # Capture image (ED) segments — log full content for analysis
    if value_type == "ED":
        raw_data = _get_field(fields, 5)
        data_preview = raw_data[:200] if raw_data else "(empty)"
        logger.info(
            "📸 IMAGE OBX detected! seq=%s, data_length=%d, preview=%s",
            sequence, len(raw_data) if raw_data else 0, data_preview,
        )
        # Save raw ED segment to file for analysis
        try:
            import os
            img_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "captured_images")
            os.makedirs(img_dir, exist_ok=True)
            with open(os.path.join(img_dir, f"ed_segment_{sequence}.txt"), "w") as f:
                f.write("|".join(fields))
            logger.info("📸 Raw ED segment saved to captured_images/ed_segment_%s.txt", sequence)
        except Exception as e:
            logger.warning("Could not save ED segment: %s", e)
        return None

    # Skip diagnostic text for now
    if value_type == "TX":
        logger.debug("Skipping OBX type TX (seq %s)", sequence)
        return None

    param_parts = _split_field(_get_field(fields, 3))
    abbreviation = param_parts[0] if param_parts else ""
    name = param_parts[1] if len(param_parts) > 1 else abbreviation

    value = _get_field(fields, 5)
    unit = _get_field(fields, 6)
    reference_range = _get_field(fields, 7)
    flag = _get_field(fields, 8)

    try:
        seq_num = int(sequence)
    except ValueError:
        seq_num = 0

    return HL7Result(
        sequence=seq_num,
        value_type=value_type,
        abbreviation=abbreviation,
        name=name,
        value=value,
        unit=unit,
        reference_range=reference_range,
        flag=flag,
    )


def parse_hl7(message: str) -> HL7Message:
    """Parse HL7 ORU^R01 message from Skyla VM100 or Tutti.

    Args:
        message: Raw HL7 message string (without MLLP framing).

    Returns:
        Parsed HL7Message with device info, patient, panel, and results.
    """
    result = HL7Message()

    # Split into segments by CR, LF, or CR+LF
    segments = re.split(r"\r\n|\r|\n", message.strip())

    device_detected = False

    for segment in segments:
        if not segment.strip():
            continue

        # MSH uses | as field separator, but MSH.1 IS the separator itself
        # So for MSH, the first field after "MSH" is the separator character
        if segment.startswith("MSH"):
            # MSH|^~\&|... — the | after MSH is the field separator (MSH.1)
            # We split by | but need to account for MSH.1 being the separator
            fields = segment.split("|")
            # fields[0] = "MSH", fields[1] = "^~\\&" (encoding chars = MSH.2)
            # fields[2] = sending app (MSH.3), etc.
            msh = _parse_msh(fields)
            result.device = msh["device"]
            result.device_type = msh["device_type"]
            result.hl7_version = msh["hl7_version"]
            result.message_id = msh["message_id"]
            result.timestamp = msh["timestamp"]
            device_detected = True

        elif segment.startswith("PID"):
            fields = segment.split("|")
            if result.device == "Tutti":
                result.patient = _parse_pid_tutti(fields)
            else:
                result.patient = _parse_pid_vm100(fields)

        elif segment.startswith("PV1"):
            fields = segment.split("|")
            patient_id = _parse_pv1(fields)
            if patient_id and not result.patient.patient_id:
                result.patient.patient_id = patient_id

        elif segment.startswith("OBR"):
            fields = segment.split("|")
            result.panel_name = _parse_obr(fields)

        elif segment.startswith("OBX"):
            fields = segment.split("|")
            obx = _parse_obx(fields)
            if obx is not None:
                result.results.append(obx)

    if not device_detected:
        logger.warning("No MSH segment found in message")

    logger.info(
        "Parsed %s %s: patient=%s, panel=%s, %d results",
        result.device,
        result.device_type,
        result.patient.name,
        result.panel_name,
        len(result.results),
    )

    return result


def build_ack(message: str) -> str:
    """Build ACK^R01 response for a received ORU^R01 message.

    Args:
        message: Original HL7 message string.

    Returns:
        ACK message string.
    """
    segments = re.split(r"\r\n|\r|\n", message.strip())
    msh_line = ""
    for seg in segments:
        if seg.startswith("MSH"):
            msh_line = seg
            break

    if not msh_line:
        return ""

    fields = msh_line.split("|")
    # Swap sending/receiving app and facility
    sending_app = _get_field(fields, 2)
    sending_facility = _get_field(fields, 3)
    receiving_app = _get_field(fields, 4)
    receiving_facility = _get_field(fields, 5)
    message_id = _get_field(fields, 9)
    version = _get_field(fields, 11)

    now = datetime.now().strftime("%Y%m%d%H%M%S")

    ack_msh = (
        f"MSH|^~\\&|{receiving_app or 'VetFlow'}|{receiving_facility}|"
        f"{sending_app}|{sending_facility}|{now}||ACK^R01|{now}|P|{version}"
    )
    ack_msa = f"MSA|AA|{message_id}"

    return f"{ack_msh}\r{ack_msa}\r"
