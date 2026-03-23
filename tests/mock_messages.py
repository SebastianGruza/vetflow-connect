"""Mock HL7 messages for Skyla VM100 and Tutti analyzers.

Based on real HL7 spec from Skyla documentation.
"""

# VM100 CBC — Complete Blood Count (HL7 v2.3.1)
VM100_CBC = (
    "MSH|^~\\&|VM100|Intec Pet Hospital|||20260323143022||ORU^R01|MSG00001|P|2.3.1||||||UNICODE UTF-8\r"
    "PID|1||||||20220115|F|Nelly|CAT\r"
    "PV1|1|O|||PAT-2024-001\r"
    "OBR|1|||CBC^Complete Blood Count|R|20260323143022|20260323143022|20260323143022\r"
    "OBX|1|ST|WBC^White Blood Cells||12.5|10^3/uL|5.5-19.5||||F\r"
    "OBX|2|ST|NEU#^Neutrophils||7.8|10^3/uL|2.5-12.5||||F\r"
    "OBX|3|ST|LYM#^Lymphocytes||3.2|10^3/uL|1.5-7.0||||F\r"
    "OBX|4|ST|MON#^Monocytes||0.6|10^3/uL|0.0-0.8||||F\r"
    "OBX|5|ST|EOS#^Eosinophils||0.8|10^3/uL|0.0-1.5||||F\r"
    "OBX|6|ST|BAS#^Basophils||0.1|10^3/uL|0.0-0.2||||F\r"
    "OBX|7|ST|NEU%^Neutrophils %||62.4|%|||||F\r"
    "OBX|8|ST|LYM%^Lymphocytes %||25.6|%|||||F\r"
    "OBX|9|ST|MON%^Monocytes %||4.8|%|||||F\r"
    "OBX|10|ST|EOS%^Eosinophils %||6.4|%|||||F\r"
    "OBX|11|ST|BAS%^Basophils %||0.8|%|||||F\r"
    "OBX|12|ST|RBC^Red Blood Cells||8.92|10^6/uL|5.0-10.0||||F\r"
    "OBX|13|ST|HGB^Hemoglobin||13.8|g/dL|8.0-15.0||||F\r"
    "OBX|14|ST|HCT^Hematocrit||42.1|%|24.0-45.0||||F\r"
    "OBX|15|ST|MCV^Mean Corpuscular Volume||47.2|fL|39.0-55.0||||F\r"
    "OBX|16|ST|MCH^Mean Corpuscular Hemoglobin||15.5|pg|12.5-17.5||||F\r"
    "OBX|17|ST|MCHC^Mean Corpuscular Hgb Conc||32.8|g/dL|30.0-36.0||||F\r"
    "OBX|18|ST|RDW-CV^RDW Coefficient of Variation||16.2|%|14.0-18.0||||F\r"
    "OBX|19|ST|RDW-SD^RDW Standard Deviation||30.5|fL|||||F\r"
    "OBX|20|ST|PLT^Platelets||285|10^3/uL|175-500||||F\r"
    "OBX|21|ST|MPV^Mean Platelet Volume||8.1|fL|||||F\r"
    "OBX|22|ST|PDW^Platelet Distribution Width||16.8|%|||||F\r"
    "OBX|23|ST|PCT^Plateletcrit||0.23|%|||||F\r"
    "OBX|24|ST|RET#^Reticulocytes||45.2|10^3/uL|3.0-50.0||||F\r"
    "OBX|25|ST|RET%^Reticulocytes %||0.51|%|||||F\r"
)

# VM100 CBC with abnormal flags
VM100_CBC_ABNORMAL = (
    "MSH|^~\\&|VM100|Intec Pet Hospital|||20260323150000||ORU^R01|MSG00002|P|2.3.1||||||UNICODE UTF-8\r"
    "PID|1||||||20200310|M|Rex|DOG\r"
    "PV1|1|O|||PAT-2024-002\r"
    "OBR|1|||CBC^Complete Blood Count|R|20260323150000|20260323150000|20260323150000\r"
    "OBX|1|ST|WBC^White Blood Cells||28.5|10^3/uL|5.5-16.9|H|||F\r"
    "OBX|2|ST|RBC^Red Blood Cells||4.2|10^6/uL|5.5-8.5|L|||F\r"
    "OBX|3|ST|HGB^Hemoglobin||9.1|g/dL|12.0-18.0|L|||F\r"
    "OBX|4|ST|PLT^Platelets||48|10^3/uL|175-500|LL|||F\r"
)

# VM100 with ED (image) and TX (diagnostic text) — should be skipped
VM100_WITH_IMAGE = (
    "MSH|^~\\&|VM100|Intec Pet Hospital|||20260323151500||ORU^R01|MSG00003|P|2.3.1||||||UNICODE UTF-8\r"
    "PID|1||||||20210501|F|Luna|DOG\r"
    "PV1|1|O|||PAT-2024-003\r"
    "OBR|1|||CBC^Complete Blood Count|R|20260323151500|20260323151500|20260323151500\r"
    "OBX|1|ST|WBC^White Blood Cells||10.2|10^3/uL|5.5-16.9||||F\r"
    "OBX|2|ED|IMG^Scatter Plot||base64encodeddata|||||F\r"
    "OBX|3|TX|DIAG^Diagnosis||Normal blood count|||||F\r"
    "OBX|4|ST|RBC^Red Blood Cells||7.5|10^6/uL|5.5-8.5||||F\r"
)

# Tutti Chemistry (HL7 v2.8)
TUTTI_CHEMISTRY = (
    "MSH|^~\\&|skyla Tutti^ESV199||||20260323144500||ORU^R01^ORU_R01|TUTTI001|P|2.8|||AL|NE\r"
    "PID|1||PAT-2024-004||Mruczka||^4^Y|F\r"
    "OBR|1|||Biochemistry Panel||||||||||||||||||BC01\r"
    "OBX|1|NM|ALB^Albumin||3.2|g/dL|2.3-3.5||||F|||||Dr.Kowalski|ESV199-001|serum|20260323144500\r"
    "OBX|2|NM|ALP^Alkaline Phosphatase||85|U/L|23-212||||F|||||Dr.Kowalski|ESV199-001|serum|20260323144500\r"
    "OBX|3|NM|ALT^Alanine Aminotransferase||52|U/L|12-130||||F|||||Dr.Kowalski|ESV199-001|serum|20260323144500\r"
    "OBX|4|NM|AMY^Amylase||1250|U/L|500-1500||||F|||||Dr.Kowalski|ESV199-001|serum|20260323144500\r"
    "OBX|5|NM|AST^Aspartate Aminotransferase||28|U/L|0-48||||F|||||Dr.Kowalski|ESV199-001|serum|20260323144500\r"
    "OBX|6|NM|BUN^Blood Urea Nitrogen||22|mg/dL|7-27||||F|||||Dr.Kowalski|ESV199-001|serum|20260323144500\r"
    "OBX|7|NM|CA^Calcium||10.1|mg/dL|7.8-11.3||||F|||||Dr.Kowalski|ESV199-001|serum|20260323144500\r"
    "OBX|8|NM|CHO^Cholesterol||195|mg/dL|110-320||||F|||||Dr.Kowalski|ESV199-001|serum|20260323144500\r"
    "OBX|9|NM|CRE^Creatinine||1.4|mg/dL|0.5-1.8||||F|||||Dr.Kowalski|ESV199-001|serum|20260323144500\r"
    "OBX|10|NM|GLU^Glucose||98|mg/dL|74-143||||F|||||Dr.Kowalski|ESV199-001|serum|20260323144500\r"
    "OBX|11|NM|TP^Total Protein||6.8|g/dL|5.7-8.9||||F|||||Dr.Kowalski|ESV199-001|serum|20260323144500\r"
    "OBX|12|NM|TBIL^Total Bilirubin||0.3|mg/dL|0.0-0.9||||F|||||Dr.Kowalski|ESV199-001|serum|20260323144500\r"
)

# Tutti with abnormal results
TUTTI_CHEMISTRY_ABNORMAL = (
    "MSH|^~\\&|skyla Tutti^ESV199||||20260323160000||ORU^R01^ORU_R01|TUTTI002|P|2.8|||AL|NE\r"
    "PID|1||PAT-2024-005||Burek||^8^Y|M\r"
    "OBR|1|||Kidney Panel||||||||||||||||||KP01\r"
    "OBX|1|NM|BUN^Blood Urea Nitrogen||45|mg/dL|7-27|H|||F|||||Dr.Nowak|ESV199-001|serum|20260323160000\r"
    "OBX|2|NM|CRE^Creatinine||3.8|mg/dL|0.5-1.8|HH|||F|||||Dr.Nowak|ESV199-001|serum|20260323160000\r"
    "OBX|3|NM|IP^Phosphorus||8.2|mg/dL|2.6-6.8|H|||F|||||Dr.Nowak|ESV199-001|serum|20260323160000\r"
    "OBX|4|NM|CA^Calcium||6.5|mg/dL|7.8-11.3|L|||F|||||Dr.Nowak|ESV199-001|serum|20260323160000\r"
    "OBX|5|NM|K^Potassium||5.8|mmol/L|3.5-5.8||||F|||||Dr.Nowak|ESV199-001|serum|20260323160000\r"
)
