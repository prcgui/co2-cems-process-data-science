#!/usr/bin/env python3
"""Collect minimal public EPA sources without retaining administrative metadata.

GET requests only. Existing snapshots are preserved. Raw-response hashes and
official URLs make each deterministic extract traceable to its source. Keys are
sent only in headers and are never stored or searched for in local files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from source_extracts import extract_configurations, extract_json_plan, extract_xml_plan_from_zip, extract_bulk_catalog, extract_code_table, json_bytes

BASE = Path(__file__).resolve().parent
API = "https://api.epa.gov/easey"
DOC = "https://www.epa.gov/system/files/documents/2024-12/ecmps_monitoring_plan_reporting_instructions-12202024.pdf"
TABLES = ("method-codes", "substitute-data-codes", "component-type-codes",
          "system-type-codes", "acquisition-method-codes", "parameter-codes")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def emissions_fields(data):
    full = json.loads(data)
    props = full["components"]["schemas"]["HourlyApportionedEmissionsDTO"]["properties"]
    return json_bytes({"schema": "HourlyApportionedEmissionsDTO",
                       "properties": {k: props[k] for k in ("co2Mass", "co2MassMeasureFlg", "opTime")}})


class Collector:
    def __init__(self, directory, key, max_requests, offline=False):
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)
        self.key, self.max_requests, self.offline = key, max_requests, offline
        self.requests, self.records = 0, []
        previous = directory / "source_provenance.json"
        self.previous = json.loads(previous.read_text()).get("sources", []) if previous.exists() else []

    def get(self, name, url, authenticated=False, transform=None, pdf=False):
        if urlparse(url).scheme != "https" or urlparse(url).hostname not in ("api.epa.gov", "www.epa.gov"):
            raise ValueError("Only declared official EPA HTTPS sources are allowed")
        path = self.directory / name
        cached = path.exists()
        if cached:
            safe = path.read_bytes()
            prior = next((r for r in self.previous if r.get("public_file") == name and r.get("source_url") == url), None)
            if prior is None or prior.get("public_sha256") != digest(safe):
                raise RuntimeError(f"Missing or inconsistent provenance for cached source {name}")
            record = dict(prior)
        else:
            if self.offline:
                raise RuntimeError(f"Required cached source absent: {name}")
            if self.requests >= self.max_requests:
                raise RuntimeError("Request budget reached; reuse the cache on a later run")
            headers = {"Accept": "application/pdf" if pdf else "application/json",
                       "User-Agent": "IatanUnit2MonitoringAudit/1.0"}
            if authenticated:
                if not self.key:
                    raise RuntimeError("Explicit --demo-key or --api-key-env required for data retrieval")
                headers["X-Api-Key"] = self.key
            self.requests += 1
            try:
                with urlopen(Request(url, headers=headers, method="GET"), timeout=60) as response:
                    if response.status != 200:
                        raise RuntimeError(f"Unexpected HTTP status {response.status} for {name}")
                    raw = response.read()
            except HTTPError as exc:
                raise RuntimeError(f"HTTP {exc.code} for {name}; stopped without retry") from None
            except (URLError, TimeoutError):
                raise RuntimeError(f"Network retrieval failed for {name}; stopped without retry") from None
            if pdf and not raw.startswith(b"%PDF"):
                raise RuntimeError(f"Unexpected PDF content for {name}")
            safe = transform(raw) if transform else raw
            if not pdf and path.suffix == ".json":
                json.loads(safe)
            record = {"public_file": name, "source_url": url, "raw_sha256": digest(raw),
                      "raw_bytes": len(raw), "public_sha256": digest(safe), "public_bytes": len(safe),
                      "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                      "transformation": "deterministic_allowlisted_extract" if transform else "unchanged_public_document"}
            with path.open("xb") as stream:
                stream.write(safe)
        self.records.append(record)
        return json.loads(safe) if path.suffix == ".json" else safe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=BASE / "sources")
    parser.add_argument("--facility", default="6065")
    parser.add_argument("--unit", default="2")
    auth = parser.add_mutually_exclusive_group()
    auth.add_argument("--demo-key", action="store_true")
    auth.add_argument("--api-key-env", help="Read only this explicitly named environment variable")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--max-requests", type=int, default=16)
    args = parser.parse_args()
    if not 0 <= args.max_requests <= 20:
        parser.error("--max-requests must be between 0 and 20")
    key = "DEMO_KEY" if args.demo_key else (os.environ.get(args.api_key_env) if args.api_key_env else None)
    collector = Collector(args.source_dir.resolve(), key, args.max_requests, args.offline)
    error = None
    try:
        configs = collector.get(f"current_configurations_{args.facility}.json", API + "/monitor-plan-mgmt/configurations?" + urlencode({"orisCodes": args.facility}), True,
                                lambda data: extract_configurations(data, args.facility, args.unit))
        plan_id = configs["items"][0]["id"]
        collector.get(f"current_plan_unit{args.unit}.json", API + "/monitor-plan-mgmt/plans/export?" + urlencode({"planId": plan_id}), True,
                      lambda data: extract_json_plan(data, args.facility, args.unit))
        catalog = collector.get(f"bulk_catalog_{args.facility}_monitoring.json", API + "/camd-services/bulk-files", True,
                                lambda data: extract_bulk_catalog(data, args.facility))
        bulk_path = catalog["items"][0]["s3Path"]
        collector.get(f"original_plan_unit{args.unit}.xml", API + "/bulk-files/" + bulk_path, True,
                      lambda data: extract_xml_plan_from_zip(data, args.facility, args.unit)[1])
        collector.get("mdm_code_list.json", API + "/master-data-mgmt/list", True, lambda data: extract_code_table(data, "list"))
        for table in TABLES:
            collector.get("mdm_" + table + ".json", API + "/master-data-mgmt/" + table, True, lambda data, table=table: extract_code_table(data, table))
        collector.get("emissions_fields.json", API + "/emissions-mgmt/swagger-json", transform=emissions_fields)
        collector.get("ecmps_monitoring_plan_reporting_instructions_2024-12-20.pdf", DOC, pdf=True)
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        error = str(exc)
        print("Source collection stopped: " + error, file=sys.stderr)
    # Preserve provenance of any previously cached source, including extracts
    # not needed before a failing request, so the next run can resume safely.
    by_name = {r["public_file"]: r for r in collector.previous}
    by_name.update({r["public_file"]: r for r in collector.records})
    provenance = {"extract_version": "1.0.0", "sources": list(by_name.values()),
                  "omitted": ["administrative user identifiers", "contact fields", "free-text plan comments", "unrelated unit and pollutant records"],
                  "note": "Full plan responses are not committed. Public technical extracts preserve all fields used by this audit; raw hashes and official URLs identify their sources."}
    (args.source_dir / "source_provenance.json").write_bytes(json_bytes(provenance))
    verification = {"completed_at_utc": datetime.now(timezone.utc).isoformat(), "verified_sources": len(collector.records),
                    "new_network_requests": collector.requests, "all_completed": error is None,
                    "method": "GET", "credentials_recorded": False}
    (args.source_dir / "fetch_verification.json").write_bytes(json_bytes(verification))
    print(f"Verified {len(collector.records)} sources; new network requests: {collector.requests}.")
    return int(error is not None)


if __name__ == "__main__":
    raise SystemExit(main())
