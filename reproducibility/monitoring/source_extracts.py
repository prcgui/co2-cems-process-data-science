"""Deterministic, allowlisted extracts of public EPA plan responses.

Administrative user identifiers, contact fields, and free-text comments are not
needed for the audit and are not retained. Full-response hashes are recorded by
the caller. No hourly emission value is changed by these source extracts.
"""
from __future__ import annotations

import io
import json
import re
import zipfile
import xml.etree.ElementTree as ET

INTERVAL = ("beginDate", "beginHour", "endDate", "endHour")
GROUPS = {
    "monitoringMethodData": ("parameterCode", "monitoringMethodCode", "substituteDataCode", "bypassApproachCode"),
    "monitoringFormulaData": ("parameterCode", "formulaId", "formulaCode", "formulaText"),
    "monitoringSystemData": ("monitoringSystemId", "systemTypeCode", "systemDesignationCode", "fuelCode"),
    "componentData": ("componentId", "componentTypeCode", "sampleAcquisitionMethodCode", "basisCode", "manufacturer", "modelVersion", "serialNumber"),
    "monitoringSpanData": ("componentTypeCode", "spanScaleCode", "spanMethodCode", "mpcValue", "mpfValue", "spanValue", "fullScaleRange", "spanUnitsOfMeasureCode", "flowSpanValue", "flowFullScaleRange"),
    "monitoringSystemComponentData": ("componentId",),
    "analyzerRangeData": ("analyzerRangeCode", "dualRangeIndicator"),
}
CHILDREN = {"monitoringSystemData": "monitoringSystemComponentData", "componentData": "analyzerRangeData"}
PLAN_FIELDS = ("orisCode", "id", "version", "updateDate", "beginReportPeriodId", "endReportPeriodId")
LOCATION_FIELDS = ("id", "unitId", "stackPipeId")
CODE_FIELDS = {
    "list": ("code", "name"),
    "method-codes": ("methodCode", "methodDescription"),
    "substitute-data-codes": ("substituteDataCode", "substituteDataDescription"),
    "component-type-codes": ("componentTypeCode", "componentTypeDescription", "spanIndicator", "parameterCode"),
    "system-type-codes": ("systemTypeCode", "systemTypeDescription"),
    "acquisition-method-codes": ("acquisitionMethodCode", "acquisitionMethodDescription"),
    "parameter-codes": ("parameterCode", "parameterDescription"),
}


def normalized(key):
    return re.sub(r"[^a-z0-9]", "", str(key).lower())


def same_identifier(value, expected):
    return str(value).strip().upper().removesuffix(".0") == str(expected).strip().upper().removesuffix(".0")


def json_bytes(document):
    return (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def extract_code_table(data, table):
    doc = json.loads(data)
    rows = doc.get("items", []) if isinstance(doc, dict) else doc
    return json_bytes({"items": [{k: row.get(k) for k in CODE_FIELDS[table]} for row in rows]})


def extract_configurations(data, facility="6065", unit="2"):
    doc = json.loads(data)
    items = doc.get("items", []) if isinstance(doc, dict) else doc
    selected = []
    for record in items:
        locations = [loc for loc in record.get("monitoringLocationData", [])
                     if same_identifier(loc.get("unitId"), unit) and not loc.get("stackPipeId")]
        if same_identifier(record.get("orisCode"), facility) and locations:
            safe = {k: record.get(k) for k in PLAN_FIELDS}
            safe["monitoringLocationData"] = [{k: loc.get(k) for k in LOCATION_FIELDS + ("unitRecordId",)} for loc in locations]
            selected.append(safe)
    if len(selected) != 1:
        raise ValueError("Expected exactly one configuration for the direct target unit")
    return json_bytes({"items": selected})


def extract_json_plan(data, facility="6065", unit="2"):
    doc = json.loads(data)
    plans = doc if isinstance(doc, list) else doc.get("items", [doc])
    selected = []
    for plan in plans:
        if not same_identifier(plan.get("orisCode"), facility):
            continue
        for location in plan.get("monitoringLocationData", []):
            if not same_identifier(location.get("unitId"), unit) or location.get("stackPipeId"):
                continue
            safe_plan = {k: plan.get(k) for k in PLAN_FIELDS}
            safe_location = {k: location.get(k) for k in LOCATION_FIELDS}
            systems = [row for row in location.get("monitoringSystemData", []) if row.get("systemTypeCode") in ("CO2", "FLOW")]
            component_ids = {str(row.get("componentId")) for system in systems for row in system.get("monitoringSystemComponentData", [])}
            for group in ("monitoringMethodData", "monitoringFormulaData", "monitoringSystemData", "componentData", "monitoringSpanData"):
                safe_location[group] = []
                for row in location.get(group, []):
                    if group in ("monitoringMethodData", "monitoringFormulaData") and not str(row.get("parameterCode", "")).startswith("CO2"):
                        continue
                    if group == "monitoringSystemData" and row.get("systemTypeCode") not in ("CO2", "FLOW"):
                        continue
                    if group == "componentData" and str(row.get("componentId")) not in component_ids:
                        continue
                    if group == "monitoringSpanData" and row.get("componentTypeCode") not in ("CO2", "FLOW"):
                        continue
                    fields = GROUPS[group] + (() if group == "componentData" else INTERVAL)
                    safe_row = {k: row.get(k) for k in fields}
                    if group in CHILDREN:
                        child = CHILDREN[group]
                        safe_row[child] = [{k: sub.get(k) for k in GROUPS[child] + INTERVAL} for sub in row.get(child, [])]
                    safe_location[group].append(safe_row)
            safe_plan["monitoringLocationData"] = [safe_location]
            selected.append(safe_plan)
    if len(selected) != 1:
        raise ValueError("Expected exactly one direct target-unit plan")
    return json_bytes(selected[0])


def extract_xml_plan_from_zip(data, facility="6065", unit="2"):
    selected = []
    def tag(element):
        return normalized(element.tag.split("}")[-1])
    def scalar(parent, field):
        found = next((c for c in parent if tag(c) == normalized(field)), None)
        return found.text if found is not None else None
    def copy_scalar(parent, source, field):
        found = next((c for c in source if tag(c) == normalized(field)), None)
        if found is not None:
            ET.SubElement(parent, found.tag.split("}")[-1]).text = found.text
    def copy_group(parent, source, group):
        safe = ET.SubElement(parent, source.tag.split("}")[-1])
        fields = GROUPS[group] + (() if group == "componentData" else INTERVAL)
        for field in fields:
            copy_scalar(safe, source, field)
        if group in CHILDREN:
            child_name = CHILDREN[group]
            for child in source:
                if tag(child) == normalized(child_name):
                    copy_group(safe, child, child_name)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for member in sorted(archive.namelist()):
            if not member.lower().endswith(".xml"):
                continue
            original = ET.fromstring(archive.read(member))
            if not same_identifier(scalar(original, "ORISCode"), facility):
                continue
            for location in original:
                if tag(location) != "monitoringlocationdata":
                    continue
                if not same_identifier(scalar(location, "UnitID"), unit) or scalar(location, "StackPipeID"):
                    continue
                safe = ET.Element("MonitoringPlan")
                copy_scalar(safe, original, "ORISCode")
                copy_scalar(safe, original, "Version")
                safe_location = ET.SubElement(safe, "MonitoringLocationData")
                copy_scalar(safe_location, location, "UnitID")
                unit_data = next((c for c in location if tag(c) == "unitdata"), None)
                if unit_data is None:
                    raise ValueError("The legacy XML target location has no UnitData section")
                safe_unit = ET.SubElement(safe_location, "UnitData")
                systems = [r for r in unit_data if tag(r) == "monitoringsystemdata" and scalar(r, "systemTypeCode") in ("CO2", "FLOW")]
                component_ids = {scalar(c, "componentId") for s in systems for c in s if tag(c) == "monitoringsystemcomponentdata"}
                for group in ("monitoringMethodData", "monitoringFormulaData", "monitoringSystemData", "componentData", "monitoringSpanData"):
                    for record in unit_data:
                        if tag(record) == normalized(group):
                            if group in ("monitoringMethodData", "monitoringFormulaData") and not str(scalar(record, "parameterCode") or "").startswith("CO2"):
                                continue
                            if group == "monitoringSystemData" and scalar(record, "systemTypeCode") not in ("CO2", "FLOW"):
                                continue
                            if group == "componentData" and scalar(record, "componentId") not in component_ids:
                                continue
                            if group == "monitoringSpanData" and scalar(record, "componentTypeCode") not in ("CO2", "FLOW"):
                                continue
                            copy_group(safe_unit, record, group)
                ET.indent(safe, space="  ")
                selected.append((member, ET.tostring(safe, encoding="utf-8", xml_declaration=True) + b"\n"))
    if len(selected) != 1:
        raise ValueError("Expected exactly one direct target-unit XML plan in the ZIP")
    return selected[0]


def extract_bulk_catalog(data, facility="6065"):
    doc = json.loads(data)
    items = doc.get("items", []) if isinstance(doc, dict) else doc
    filename = f"{int(facility):06d}_MP.zip"
    selected = [r for r in items if r.get("filename") == filename]
    if len(selected) != 1:
        raise ValueError("The official bulk catalog did not identify exactly one target monitoring ZIP")
    fields = ("filename", "s3Path", "bytes", "kiloBytes", "megaBytes", "gigaBytes", "lastUpdated")
    safe = [{k: r.get(k) for k in fields} for r in selected]
    for target, source in zip(safe, selected):
        target["metadata"] = {k: source.get("metadata", {}).get(k) for k in ("dataType", "description", "stateCode", "dataSubType")}
    return json_bytes({"items": safe})
