# Metadata model

## Purpose

`catalog.json` is the repository-level index. It points to evidence-based metadata for papers and artifacts without duplicating it. Artifact-level experiment indexes record scientific intent and lineage; Git remains authoritative for source history.

## Entities and identifiers

Entity collections cover people, organisations, software, datasets/model artifacts, experiments, venues, and funding projects. IDs are stable, lowercase, namespaced values such as `paper:profinfer`, `artifact:profinfer`, `person:bohua-zou`, `software:llama-cpp`, and `experiment:profinfer-exp-0001`. An ID must not be changed merely because a path changes, and experiment numbers are never reused.

Artifact experiments have two immutable identifiers: a readable sequential ID such as `exp-0001`, and an eight-character lowercase hexadecimal `uid`. The UID is deterministically derived from the first eight SHA-256 characters of `<artifact-id>/<experiment-id>`, is unique within the artifact, and serves only as a compact alias. Relationships and lineage continue to use stable namespaced or sequential IDs rather than the short UID.

## Relationships

Relationships are directed records with `source`, `predicate`, `target`, and evidence. Predicates describe explicit facts such as `has-artifact`, `supports-paper`, `authored-by`, `uses-software`, `uses-dataset`, and `defines-experiment`. Every endpoint must resolve to an entity defined in the catalogue metadata.

## Classification

Paper classification is multi-label across independent axes: research function, technical category, system layer, resource type, workload type, infrastructure context, telemetry source, evaluation methodology, and sustainability dimension. Values use the controlled vocabulary enforced by `scripts/validate_metadata.py`; empty lists are preferable to unsupported inference.

## Adding a paper

1. Create `papers/<slug>/paper`, `papers/<slug>/artifact`, and `papers/<slug>/metadata`.
2. Put manuscript material under `paper/` without changing its scientific content.
3. Keep artifact internals intact and put `README.md` plus installation/reproduction guidance at the artifact root.
4. Add paper, artifact, entity, and relationship metadata using unused stable IDs.
5. Catalogue existing experiments with immutable `exp-####` identifiers and their deterministically derived eight-character hexadecimal UIDs; do not commit datasets, weights, or generated results.
6. Reference the paper and artifact from `catalog.json`, update the root table, and run the validator.

## Future interoperability

The current JSON can later map to JSON-LD by assigning contexts to IDs and predicates. Paper, software, dataset, execution, and result entities can also become RO-Crate contextual and data entities. Those mappings should be additive and must retain the stable IDs already issued here.

## Evidence and uncertainty

Titles, authors, versions, repository URLs, affiliations, licences, hardware, commands, datasets, and results must come from a manuscript, repository file, Git metadata, or observed output. Unknown values remain `null` or empty, and unresolved questions belong in `metadata_gaps`. A plausible value is not evidence.
