"""Tests for HL7 parser — VM100 CBC and Tutti Chemistry messages."""

import pytest

from scripts.vetflow_connect.hl7_parser import build_ack, parse_hl7

from .mock_messages import (
    TUTTI_CHEMISTRY,
    TUTTI_CHEMISTRY_ABNORMAL,
    VM100_CBC,
    VM100_CBC_ABNORMAL,
    VM100_WITH_IMAGE,
)


class TestVM100Parser:
    """Tests for VM100 CBC message parsing."""

    def test_device_detection(self):
        msg = parse_hl7(VM100_CBC)
        assert msg.device == "VM100"
        assert msg.device_type == "cbc"
        assert msg.hl7_version == "2.3.1"

    def test_message_id(self):
        msg = parse_hl7(VM100_CBC)
        assert msg.message_id == "MSG00001"

    def test_timestamp(self):
        msg = parse_hl7(VM100_CBC)
        assert msg.timestamp == "20260323143022"

    def test_patient_info(self):
        msg = parse_hl7(VM100_CBC)
        assert msg.patient.name == "Nelly"
        assert msg.patient.species == "CAT"
        assert msg.patient.sex == "F"
        assert msg.patient.birthday == "20220115"

    def test_patient_id_from_pv1(self):
        msg = parse_hl7(VM100_CBC)
        assert msg.patient.patient_id == "PAT-2024-001"

    def test_panel_name(self):
        msg = parse_hl7(VM100_CBC)
        assert msg.panel_name == "Complete Blood Count"

    def test_result_count(self):
        msg = parse_hl7(VM100_CBC)
        assert len(msg.results) == 25  # All CBC parameters

    def test_wbc_result(self):
        msg = parse_hl7(VM100_CBC)
        wbc = msg.results[0]
        assert wbc.abbreviation == "WBC"
        assert wbc.name == "White Blood Cells"
        assert wbc.value == "12.5"
        assert wbc.unit == "10^3/uL"
        assert wbc.reference_range == "5.5-19.5"
        assert wbc.value_type == "ST"
        assert wbc.sequence == 1

    def test_platelet_result(self):
        msg = parse_hl7(VM100_CBC)
        plt = next(r for r in msg.results if r.abbreviation == "PLT")
        assert plt.value == "285"
        assert plt.unit == "10^3/uL"
        assert plt.reference_range == "175-500"

    def test_abnormal_flags(self):
        msg = parse_hl7(VM100_CBC_ABNORMAL)
        wbc = msg.results[0]
        assert wbc.flag == "H"

        rbc = msg.results[1]
        assert rbc.flag == "L"

        plt = msg.results[3]
        assert plt.flag == "LL"

    def test_skip_ed_and_tx_types(self):
        msg = parse_hl7(VM100_WITH_IMAGE)
        # Should have only 2 results (WBC + RBC), not ED/TX
        assert len(msg.results) == 2
        types = {r.value_type for r in msg.results}
        assert "ED" not in types
        assert "TX" not in types


class TestTuttiParser:
    """Tests for Tutti Chemistry message parsing."""

    def test_device_detection(self):
        msg = parse_hl7(TUTTI_CHEMISTRY)
        assert msg.device == "Tutti"
        assert msg.device_type == "chemistry"
        assert msg.hl7_version == "2.8"

    def test_message_id(self):
        msg = parse_hl7(TUTTI_CHEMISTRY)
        assert msg.message_id == "TUTTI001"

    def test_patient_info(self):
        msg = parse_hl7(TUTTI_CHEMISTRY)
        assert msg.patient.name == "Mruczka"
        assert msg.patient.patient_id == "PAT-2024-004"
        assert msg.patient.sex == "F"
        assert msg.patient.age == "4 Y"

    def test_panel_name(self):
        msg = parse_hl7(TUTTI_CHEMISTRY)
        assert msg.panel_name == "Biochemistry Panel"

    def test_result_count(self):
        msg = parse_hl7(TUTTI_CHEMISTRY)
        assert len(msg.results) == 12

    def test_albumin_result(self):
        msg = parse_hl7(TUTTI_CHEMISTRY)
        alb = msg.results[0]
        assert alb.abbreviation == "ALB"
        assert alb.name == "Albumin"
        assert alb.value == "3.2"
        assert alb.unit == "g/dL"
        assert alb.reference_range == "2.3-3.5"
        assert alb.value_type == "NM"

    def test_glucose_result(self):
        msg = parse_hl7(TUTTI_CHEMISTRY)
        glu = next(r for r in msg.results if r.abbreviation == "GLU")
        assert glu.value == "98"
        assert glu.unit == "mg/dL"
        assert glu.reference_range == "74-143"

    def test_abnormal_chemistry(self):
        msg = parse_hl7(TUTTI_CHEMISTRY_ABNORMAL)
        bun = msg.results[0]
        assert bun.flag == "H"
        assert bun.value == "45"

        cre = msg.results[1]
        assert cre.flag == "HH"
        assert cre.value == "3.8"

        ca = msg.results[3]
        assert ca.flag == "L"


class TestACKBuilder:
    """Tests for ACK message generation."""

    def test_ack_for_vm100(self):
        ack = build_ack(VM100_CBC)
        assert "ACK^R01" in ack
        assert "MSA|AA|MSG00001" in ack
        assert ack.startswith("MSH|^~\\&|")

    def test_ack_for_tutti(self):
        ack = build_ack(TUTTI_CHEMISTRY)
        assert "ACK^R01" in ack
        assert "MSA|AA|TUTTI001" in ack

    def test_ack_version_preserved(self):
        ack = build_ack(TUTTI_CHEMISTRY)
        # ACK should use same HL7 version as original
        assert "|2.8" in ack

    def test_ack_empty_message(self):
        ack = build_ack("")
        assert ack == ""

    def test_ack_no_msh(self):
        ack = build_ack("PID|1||test||Name\r")
        assert ack == ""
