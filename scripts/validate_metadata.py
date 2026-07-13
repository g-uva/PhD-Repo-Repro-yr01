#!/usr/bin/env python3
"""Validate the research catalogue without requiring a project framework."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ID_RE = re.compile(r"^[a-z][a-z0-9-]*:[a-z0-9][a-z0-9.-]*$")
SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")

VOCABULARY = {
    "research_functions": {
        "measurement-telemetry", "workload-characterisation", "performance-modelling",
        "prediction-inference", "optimisation", "scheduling-resource-management",
        "runtime-systems", "benchmarking-evaluation", "reproducibility", "methodology",
        "survey", "vision",
    },
    "technical_categories": {
        "measurement-and-telemetry", "workload-characterisation", "ai-serving-and-inference",
        "ai-training", "gpu-and-accelerator-systems", "cluster-scheduling", "energy-and-carbon",
        "scientific-workflows", "reproducibility-and-artifacts", "virtualisation-and-cloud-native",
        "distributed-and-federated-systems", "performance-modelling", "benchmarking",
    },
    "system_layers": {
        "application", "model", "framework", "runtime", "operator", "library",
        "accelerator-kernel", "accelerator", "device-driver", "os-kernel", "process-thread",
        "container", "virtual-machine", "node", "cluster", "data-centre", "federation",
        "cloud-edge-continuum",
    },
    "resource_types": {"cpu", "gpu", "accelerator", "memory", "storage", "network", "io", "energy", "power", "carbon", "time", "cost"},
    "workload_types": {"ai-training", "ai-inference", "llm-serving", "batch", "interactive", "scientific-workflow", "data-processing", "microservice", "benchmark", "synthetic"},
    "infrastructure_contexts": {"bare-metal", "containerised", "virtualised", "cloud", "edge", "hpc", "data-centre", "distributed", "federated", "multi-tenant", "heterogeneous"},
    "telemetry_sources": {"hardware-counter", "software-instrumentation", "application-log", "system-call", "ebpf", "cupti", "dcgm", "nvml", "perf", "prometheus", "rapl", "scaphandre", "custom-profiler"},
    "methodologies": {"controlled-experiment", "benchmark", "trace-driven", "simulation", "testbed", "production-deployment", "case-study", "ablation", "sensitivity-analysis", "comparative-evaluation", "statistical-analysis"},
    "sustainability_dimensions": {"energy-efficiency", "power-efficiency", "carbon-efficiency", "resource-efficiency", "hardware-utilisation", "environmental-impact"},
}
EXPERIMENT_STATUSES = {"draft", "working", "validated", "archived", "published"}


def load(path: Path, errors: list[str]) -> Any:
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"cannot load {path.relative_to(ROOT)}: {exc}")
        return None


def check_path(path: Path, label: str, errors: list[str]) -> None:
    if not path.exists():
        errors.append(f"missing path referenced by {label}: {path}")


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    catalogue_path = ROOT / "catalog.json"
    schema_path = ROOT / "schemas/research-catalogue.schema.json"
    catalogue = load(catalogue_path, errors)
    schema = load(schema_path, errors)
    if catalogue is None or schema is None:
        return report(errors, warnings)

    try:
        import jsonschema
    except ImportError:
        warnings.append("jsonschema is unavailable; using built-in root structural checks")
        required = {"$schema", "catalogue_version", "project", "papers", "artifacts"}
        missing = required - set(catalogue)
        if missing:
            errors.append(f"catalog.json lacks required fields: {sorted(missing)}")
        if not SEMVER_RE.fullmatch(str(catalogue.get("catalogue_version", ""))):
            errors.append("catalogue_version is not semantic x.y.z form")
    else:
        try:
            jsonschema.Draft202012Validator.check_schema(schema)
            jsonschema.validate(catalogue, schema)
        except jsonschema.exceptions.SchemaError as exc:
            errors.append(f"invalid JSON Schema: {exc.message}")
        except jsonschema.exceptions.ValidationError as exc:
            errors.append(f"catalog.json schema failure at {list(exc.path)}: {exc.message}")

    references = catalogue.get("papers", []) + catalogue.get("artifacts", [])
    reference_ids = [ref.get("id") for ref in references]
    for value, count in Counter(reference_ids).items():
        if count > 1:
            errors.append(f"duplicate root catalogue ID: {value}")

    documents: dict[str, Any] = {}
    document_paths: dict[str, Path] = {}
    for ref in references:
        ref_id, relpath = ref.get("id"), ref.get("path")
        if not ID_RE.fullmatch(str(ref_id)):
            errors.append(f"invalid namespaced ID: {ref_id}")
        path = ROOT / str(relpath)
        check_path(path, f"catalogue entry {ref_id}", errors)
        doc = load(path, errors) if path.exists() else None
        if doc is not None:
            documents[ref_id] = doc
            document_paths[ref_id] = path
            if doc.get("id") != ref_id:
                errors.append(f"{relpath} ID does not match catalogue reference {ref_id}")

    profinfer_meta = ROOT / "papers/profinfer/metadata"
    entities_path = profinfer_meta / "entities.json"
    entities = load(entities_path, errors) or {}
    entity_records: list[dict[str, Any]] = []
    for collection in ("people", "organisations", "software", "datasets", "experiments", "venues", "funding_projects"):
        entity_records.extend(entities.get(collection, []))

    definition_ids = list(documents) + [record.get("id") for record in entity_records]
    for value, count in Counter(definition_ids).items():
        if count > 1:
            errors.append(f"duplicate defined entity ID: {value}")
        if not ID_RE.fullmatch(str(value)):
            errors.append(f"invalid defined entity ID: {value}")

    for record in entities.get("experiments", []):
        relpath = record.get("metadata_path")
        if relpath:
            check_path((entities_path.parent / relpath).resolve(), f"experiment {record.get('id')}", errors)

    paper = documents.get("paper:profinfer", {})
    for axis, allowed in VOCABULARY.items():
        values = paper.get("classification", {}).get(axis, [])
        invalid = sorted(set(values) - allowed)
        if invalid:
            errors.append(f"invalid classification values for {axis}: {invalid}")

    for doc_id, doc in documents.items():
        base = document_paths[doc_id].parent
        source_path = doc.get("source_path")
        if source_path:
            check_path((base / source_path).resolve(), f"{doc_id}.source_path", errors)
        for component in doc.get("components", []):
            if component.get("path"):
                check_path((base / component["path"]).resolve(), f"component {component.get('name')}", errors)

    index_path = ROOT / "papers/profinfer/artifact/experiments/index.json"
    index = load(index_path, errors) or {}
    experiment_ids = [entry.get("id") for entry in index.get("experiments", [])]
    for value, count in Counter(experiment_ids).items():
        if count > 1:
            errors.append(f"duplicate experiment ID: {value}")
    issued_numbers: list[int] = []
    for entry in index.get("experiments", []):
        match = re.fullmatch(r"exp-([0-9]{4})", str(entry.get("id")))
        if not match:
            errors.append(f"invalid experiment ID: {entry.get('id')}")
            continue
        issued_numbers.append(int(match.group(1)))
        metadata_path = index_path.parent / str(entry.get("path"))
        check_path(metadata_path, f"experiment index entry {entry.get('id')}", errors)
        metadata = load(metadata_path, errors) if metadata_path.exists() else None
        if metadata:
            if metadata.get("id") != entry.get("id"):
                errors.append(f"experiment metadata ID mismatch in {metadata_path}")
            if metadata.get("status") not in EXPERIMENT_STATUSES:
                errors.append(f"invalid status for {entry.get('id')}: {metadata.get('status')}")
            parent = metadata.get("parent")
            if parent is not None and parent not in experiment_ids:
                errors.append(f"unresolved parent for {entry.get('id')}: {parent}")
    next_number = index.get("next_experiment_number")
    if issued_numbers and (not isinstance(next_number, int) or next_number <= max(issued_numbers)):
        errors.append("next_experiment_number must exceed every issued experiment number")

    relationships = load(profinfer_meta / "relationships.json", errors) or {}
    known_ids = set(definition_ids)
    allowed_predicates = {
        "has-artifact", "supports-paper", "authored-by", "affiliated-with", "uses-software",
        "uses-dataset", "produces-dataset", "defines-experiment", "evaluates-with",
        "implements-method", "extends-paper", "compares-against", "funded-by", "published-at",
        "addresses-research-question", "classified-as", "produces-result",
    }
    for rel in relationships.get("relationships", []):
        if rel.get("predicate") not in allowed_predicates:
            errors.append(f"unsupported predicate: {rel.get('predicate')}")
        for endpoint in ("source", "target"):
            if rel.get(endpoint) not in known_ids:
                errors.append(f"unresolved relationship {endpoint}: {rel.get(endpoint)}")

    return report(errors, warnings)


def report(errors: list[str], warnings: list[str]) -> int:
    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    if errors:
        print(f"metadata validation failed with {len(errors)} error(s)", file=sys.stderr)
        return 1
    print("metadata validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

