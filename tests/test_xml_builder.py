"""Tests for HL7 → VetFlow XML conversion."""

from xml.etree import ElementTree as ET

from scripts.vetflow_connect.hl7_parser import parse_hl7
from scripts.vetflow_connect.xml_builder import hl7_to_vetflow_xml

from .mock_messages import (
    TUTTI_CHEMISTRY,
    TUTTI_CHEMISTRY_ABNORMAL,
    VM100_CBC,
    VM100_CBC_ABNORMAL,
)


def _parse_xml(xml_str: str) -> ET.Element:
    """Parse XML string and return root element."""
    return ET.fromstring(xml_str)


class TestVM100XMLBuilder:
    """Tests for VM100 CBC → XML conversion."""

    def test_root_element(self):
        msg = parse_hl7(VM100_CBC)
        xml = hl7_to_vetflow_xml(msg)
        root = _parse_xml(xml)
        assert root.tag == "wynik"

    def test_xml_declaration(self):
        msg = parse_hl7(VM100_CBC)
        xml = hl7_to_vetflow_xml(msg)
        assert xml.startswith('<?xml version="1.0" encoding="UTF-8"?>')

    def test_dostawca(self):
        msg = parse_hl7(VM100_CBC)
        xml = hl7_to_vetflow_xml(msg)
        root = _parse_xml(xml)
        dostawca = root.find("dostawca")
        assert dostawca is not None
        assert "VM100" in dostawca.attrib["nazwa"]

    def test_nr_badania(self):
        msg = parse_hl7(VM100_CBC)
        xml = hl7_to_vetflow_xml(msg)
        root = _parse_xml(xml)
        nr = root.find("nr_badania")
        assert nr is not None
        assert nr.text == "MSG00001"

    def test_data_badania(self):
        msg = parse_hl7(VM100_CBC)
        xml = hl7_to_vetflow_xml(msg)
        root = _parse_xml(xml)
        data = root.find("data_badania")
        assert data is not None
        assert "2026-03-23" in data.text

    def test_rodzaj_probki(self):
        msg = parse_hl7(VM100_CBC)
        xml = hl7_to_vetflow_xml(msg)
        root = _parse_xml(xml)
        probka = root.find("rodzaj_probki")
        assert probka is not None
        assert probka.text == "krew EDTA"

    def test_pacjent(self):
        msg = parse_hl7(VM100_CBC)
        xml = hl7_to_vetflow_xml(msg)
        root = _parse_xml(xml)
        pacjent = root.find("pacjent")
        assert pacjent is not None
        assert pacjent.attrib["imie"] == "Nelly"
        assert pacjent.attrib["gatunek"] == "Kot"
        assert pacjent.attrib["plec"] == "samica"

    def test_badanie_parameters(self):
        msg = parse_hl7(VM100_CBC)
        xml = hl7_to_vetflow_xml(msg)
        root = _parse_xml(xml)
        badanie = root.find("badanie")
        assert badanie is not None
        assert badanie.attrib["nazwa"] == "Complete Blood Count"
        params = badanie.findall("parametr")
        assert len(params) == 25

    def test_parameter_details(self):
        msg = parse_hl7(VM100_CBC)
        xml = hl7_to_vetflow_xml(msg)
        root = _parse_xml(xml)
        params = root.find("badanie").findall("parametr")
        wbc = params[0]
        assert wbc.attrib["nazwa"] == "White Blood Cells"
        assert wbc.text == "12.5"
        assert wbc.attrib["jednostka"] == "10^3/uL"
        assert wbc.attrib["norma"] == "5.5-19.5"

    def test_abnormal_flags_in_uwagi(self):
        msg = parse_hl7(VM100_CBC_ABNORMAL)
        xml = hl7_to_vetflow_xml(msg)
        root = _parse_xml(xml)
        params = root.find("badanie").findall("parametr")

        wbc = params[0]
        assert "normy" in wbc.attrib["uwagi"]  # "powyżej normy"

        plt = params[3]
        assert "krytycznie" in plt.attrib["uwagi"]  # "krytycznie niski"


class TestTuttiXMLBuilder:
    """Tests for Tutti Chemistry → XML conversion."""

    def test_dostawca_tutti(self):
        msg = parse_hl7(TUTTI_CHEMISTRY)
        xml = hl7_to_vetflow_xml(msg)
        root = _parse_xml(xml)
        dostawca = root.find("dostawca")
        assert "Tutti" in dostawca.attrib["nazwa"]

    def test_rodzaj_probki_chemistry(self):
        msg = parse_hl7(TUTTI_CHEMISTRY)
        xml = hl7_to_vetflow_xml(msg)
        root = _parse_xml(xml)
        probka = root.find("rodzaj_probki")
        assert probka.text == "surowica"

    def test_pacjent_tutti(self):
        msg = parse_hl7(TUTTI_CHEMISTRY)
        xml = hl7_to_vetflow_xml(msg)
        root = _parse_xml(xml)
        pacjent = root.find("pacjent")
        assert pacjent.attrib["imie"] == "Mruczka"
        assert pacjent.attrib["plec"] == "samica"
        assert pacjent.attrib["id"] == "PAT-2024-004"

    def test_chemistry_parameters(self):
        msg = parse_hl7(TUTTI_CHEMISTRY)
        xml = hl7_to_vetflow_xml(msg)
        root = _parse_xml(xml)
        params = root.find("badanie").findall("parametr")
        assert len(params) == 12

        # Check albumin
        alb = params[0]
        assert alb.attrib["nazwa"] == "Albumin"
        assert alb.text == "3.2"
        assert alb.attrib["jednostka"] == "g/dL"
        assert alb.attrib["norma"] == "2.3-3.5"


class TestXMLCompatibility:
    """Test that generated XML is compatible with VetFlow's parse_lab_xml."""

    def test_vm100_xml_parseable(self):
        """Ensure VM100 XML can be parsed by VetFlow's existing parser."""
        from vetflow.services.lab_result_parser import parse_lab_xml

        msg = parse_hl7(VM100_CBC)
        xml = hl7_to_vetflow_xml(msg)
        parsed = parse_lab_xml(xml)

        assert parsed["patient"]["name"] == "Nelly"
        assert parsed["order_number"] == "MSG00001"
        assert "2026-03-23" in parsed["test_date"]
        assert parsed["sample_type"] == "krew EDTA"
        assert len(parsed["tests"]) == 1
        assert len(parsed["tests"][0]["parameters"]) == 25
        assert parsed["lab"]["name"] == "Skyla VM100 (CBC)"

    def test_tutti_xml_parseable(self):
        """Ensure Tutti XML can be parsed by VetFlow's existing parser."""
        from vetflow.services.lab_result_parser import parse_lab_xml

        msg = parse_hl7(TUTTI_CHEMISTRY)
        xml = hl7_to_vetflow_xml(msg)
        parsed = parse_lab_xml(xml)

        assert parsed["patient"]["name"] == "Mruczka"
        assert parsed["order_number"] == "TUTTI001"
        assert parsed["sample_type"] == "surowica"
        assert len(parsed["tests"]) == 1
        assert len(parsed["tests"][0]["parameters"]) == 12
        assert parsed["lab"]["name"] == "Skyla Tutti (Chemistry)"

    def test_abnormal_vm100_parseable(self):
        """Ensure abnormal VM100 results parse correctly."""
        from vetflow.services.lab_result_parser import parse_lab_xml

        msg = parse_hl7(VM100_CBC_ABNORMAL)
        xml = hl7_to_vetflow_xml(msg)
        parsed = parse_lab_xml(xml)

        assert parsed["patient"]["name"] == "Rex"
        params = parsed["tests"][0]["parameters"]
        # WBC should have "powyżej normy" in notes
        wbc = params[0]
        assert wbc["name"] == "White Blood Cells"
        assert "normy" in wbc["notes"]
