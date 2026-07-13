#!/usr/bin/env python3
"""Generate an interactive Cytoscape.js view of the research metadata graph."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "docs/research-graph.html"

COLLECTION_KINDS = {
    "people": "person",
    "organisations": "organisation",
    "software": "software",
    "datasets": "dataset",
    "experiments": "experiment",
    "venues": "venue",
    "funding_projects": "funding-project",
    "configurations": "configuration",
    "results": "result",
}


def load(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def display_label(record: dict[str, Any]) -> str:
    return str(
        record.get("short_name")
        or record.get("name")
        or record.get("title")
        or record["id"]
    )


def add_node(
    nodes: dict[str, dict[str, Any]], record: dict[str, Any], kind: str
) -> None:
    identifier = record["id"]
    if identifier in nodes:
        raise ValueError(f"duplicate graph node: {identifier}")
    nodes[identifier] = {
        "data": {
            "id": identifier,
            "label": display_label(record),
            "kind": kind,
            "metadata": json.dumps(record, indent=2, ensure_ascii=False),
        }
    }


def build_elements() -> tuple[list[dict[str, Any]], list[str]]:
    catalogue = load(ROOT / "catalog.json")
    nodes: dict[str, dict[str, Any]] = {}

    for section, kind in (("papers", "paper"), ("artifacts", "artifact")):
        for reference in catalogue[section]:
            record = load(ROOT / reference["path"])
            add_node(nodes, record, kind)

    metadata_root = ROOT / "papers/profinfer/metadata"
    entities = load(metadata_root / "entities.json")
    provenance = load(metadata_root / "provenance.json")
    for document in (entities, provenance):
        for collection, kind in COLLECTION_KINDS.items():
            for record in document.get(collection, []):
                add_node(nodes, record, kind)

    relationships = load(metadata_root / "relationships.json")["relationships"]
    edges: list[dict[str, Any]] = []
    for number, relationship in enumerate(relationships, start=1):
        source = relationship["source"]
        target = relationship["target"]
        if source not in nodes or target not in nodes:
            raise ValueError(
                f"relationship endpoint is undefined: {source} -> {target}"
            )
        edges.append(
            {
                "data": {
                    "id": f"edge-{number:04d}",
                    "source": source,
                    "target": target,
                    "label": relationship["predicate"],
                    "kind": "relationship",
                    "metadata": json.dumps(
                        relationship, indent=2, ensure_ascii=False
                    ),
                }
            }
        )

    kinds = sorted({node["data"]["kind"] for node in nodes.values()})
    return [*nodes.values(), *edges], kinds


def render(elements: list[dict[str, Any]], kinds: list[str]) -> str:
    graph_json = json.dumps(elements, ensure_ascii=False).replace("</", "<\\/")
    options = '\n'.join(
        f'<option value="{html.escape(kind)}">{html.escape(kind)}</option>'
        for kind in kinds
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Research metadata graph</title>
  <style>
    :root {{ color-scheme: light; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: #f4f4f1; color: #111; }}
    header {{ height: 58px; display: flex; align-items: center; gap: 16px; padding: 0 18px; border-bottom: 2px solid #000; background: #fff; }}
    header h1 {{ margin: 0; font-size: 18px; }}
    header span {{ color: #555; font-size: 13px; }}
    main {{ height: calc(100vh - 58px); display: grid; grid-template-columns: 245px minmax(420px, 1fr) 330px; }}
    aside {{ background: #fff; padding: 16px; overflow: auto; }}
    #controls {{ border-right: 2px solid #000; }}
    #details {{ border-left: 2px solid #000; }}
    #cy {{ width: 100%; height: 100%; background: #fafaf8; }}
    label {{ display: block; margin: 0 0 6px; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: .05em; }}
    input, select, button {{ width: 100%; min-height: 36px; margin: 0 0 12px; padding: 7px 9px; color: #111; background: #fff; border: 2px solid #000; border-radius: 5px; font: inherit; }}
    button {{ cursor: pointer; font-weight: 700; }}
    button:hover {{ background: #111; color: #fff; }}
    .button-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }}
    .stats {{ margin: 4px 0 16px; padding: 9px; border: 2px solid #000; border-radius: 5px; font-size: 12px; background: #f4f4f1; }}
    .legend {{ display: grid; gap: 7px; margin-top: 16px; font-size: 12px; }}
    .legend-row {{ display: flex; align-items: center; gap: 8px; }}
    .swatch {{ width: 18px; height: 18px; flex: 0 0 18px; border: 2px solid #000; border-radius: 50%; }}
    #details h2 {{ margin: 0 0 4px; font-size: 16px; overflow-wrap: anywhere; }}
    #details .kind {{ margin: 0 0 14px; color: #555; font-size: 12px; text-transform: uppercase; }}
    #metadata {{ margin: 0; padding: 12px; overflow: auto; white-space: pre-wrap; overflow-wrap: anywhere; border: 2px solid #000; border-radius: 5px; background: #f4f4f1; font: 11px/1.45 ui-monospace, SFMono-Regular, Menlo, monospace; }}
    .hint {{ color: #555; font-size: 13px; line-height: 1.5; }}
    @media (max-width: 950px) {{
      main {{ grid-template-columns: 200px 1fr; }}
      #details {{ position: fixed; right: 0; bottom: 0; width: min(360px, 90vw); max-height: 45vh; border-top: 2px solid #000; box-shadow: -4px -4px 0 rgba(0,0,0,.12); }}
    }}
  </style>
  <script src="https://cdn.jsdelivr.net/npm/cytoscape@3.34.0/dist/cytoscape.min.js"></script>
</head>
<body>
  <header><h1>Research metadata graph</h1><span>Drag nodes · scroll to zoom · click for provenance</span></header>
  <main>
    <aside id="controls">
      <label for="search">Search</label>
      <input id="search" type="search" placeholder="ID, name, predicate…">
      <label for="kind-filter">Node type</label>
      <select id="kind-filter"><option value="all">All types</option>{options}</select>
      <div class="button-row"><button id="fit">Fit</button><button id="layout">Relayout</button></div>
      <button id="reset">Reset filters</button>
      <div id="stats" class="stats"></div>
      <strong>Legend</strong>
      <div id="legend" class="legend"></div>
    </aside>
    <section id="cy" aria-label="Interactive research metadata graph"></section>
    <aside id="details">
      <h2 id="detail-title">Select a node or edge</h2>
      <p id="detail-kind" class="kind">Details</p>
      <p id="detail-hint" class="hint">Click an element to inspect its identifier, metadata, relationship predicate, and evidence.</p>
      <pre id="metadata">No selection</pre>
    </aside>
  </main>
  <script>
    const elements = {graph_json};
    const colours = {{
      paper: '#ffcf56', artifact: '#ff8f70', person: '#9dd9f3', software: '#b8e986',
      dataset: '#d8b4fe', experiment: '#f9a8d4', configuration: '#fef08a', result: '#93c5fd',
      venue: '#cbd5e1', organisation: '#fdba74', 'funding-project': '#a7f3d0'
    }};

    if (typeof cytoscape === 'undefined') {{
      document.getElementById('cy').innerHTML = '<p style="padding:20px">Cytoscape.js could not load. Connect to the internet and reload this file.</p>';
      throw new Error('Cytoscape.js did not load');
    }}

    const cy = cytoscape({{
      container: document.getElementById('cy'),
      elements,
      wheelSensitivity: 0.18,
      minZoom: 0.08,
      maxZoom: 3,
      layout: {{ name: 'cose', animate: false, nodeRepulsion: 850000, idealEdgeLength: 115, gravity: 0.3, numIter: 1400 }},
      style: [
        {{ selector: 'node', style: {{
          'background-color': ele => colours[ele.data('kind')] || '#fff',
          'border-color': '#000', 'border-width': 2.5, 'width': 42, 'height': 42,
          'label': 'data(label)', 'font-size': 9, 'font-weight': 700, 'color': '#000',
          'text-wrap': 'wrap', 'text-max-width': 92, 'text-valign': 'bottom',
          'text-margin-y': 8, 'text-background-color': '#fff', 'text-background-opacity': 0.88,
          'text-background-padding': 2
        }} }},
        {{ selector: 'edge', style: {{
          'width': 1.7, 'line-color': '#000', 'target-arrow-color': '#000',
          'target-arrow-shape': 'triangle', 'curve-style': 'bezier',
          'label': 'data(label)', 'font-size': 7, 'color': '#111',
          'text-background-color': '#fff', 'text-background-opacity': 0.92,
          'text-background-padding': 2, 'text-rotation': 'autorotate'
        }} }},
        {{ selector: ':selected', style: {{ 'border-width': 5, 'border-color': '#000', 'line-color': '#ef4444', 'target-arrow-color': '#ef4444', 'z-index': 999 }} }},
        {{ selector: '.faded', style: {{ 'opacity': 0.09, 'text-opacity': 0 }} }},
        {{ selector: '.matched', style: {{ 'border-width': 6, 'border-color': '#000', 'background-color': '#fff' }} }}
      ]
    }});

    const search = document.getElementById('search');
    const kindFilter = document.getElementById('kind-filter');
    const stats = document.getElementById('stats');
    const title = document.getElementById('detail-title');
    const detailKind = document.getElementById('detail-kind');
    const metadata = document.getElementById('metadata');
    const hint = document.getElementById('detail-hint');

    function applyFilters() {{
      const query = search.value.trim().toLowerCase();
      const kind = kindFilter.value;
      cy.elements().removeClass('faded matched');
      let visibleNodes = cy.nodes();
      if (kind !== 'all') visibleNodes = visibleNodes.filter(n => n.data('kind') === kind);
      if (query) visibleNodes = visibleNodes.filter(n => `${{n.data('id')}} ${{n.data('label')}} ${{n.data('metadata')}}`.toLowerCase().includes(query));
      const visibleEdges = cy.edges().filter(e => visibleNodes.contains(e.source()) && visibleNodes.contains(e.target()));
      const visible = visibleNodes.union(visibleEdges);
      cy.elements().not(visible).addClass('faded');
      if (query) visibleNodes.addClass('matched');
      stats.textContent = `${{visibleNodes.length}} / ${{cy.nodes().length}} nodes · ${{visibleEdges.length}} / ${{cy.edges().length}} edges`;
    }}

    search.addEventListener('input', applyFilters);
    kindFilter.addEventListener('change', applyFilters);
    document.getElementById('fit').addEventListener('click', () => cy.fit(cy.elements().not('.faded'), 35));
    document.getElementById('layout').addEventListener('click', () => cy.layout({{ name: 'cose', animate: true, animationDuration: 500, nodeRepulsion: 850000, idealEdgeLength: 115, gravity: 0.3 }}).run());
    document.getElementById('reset').addEventListener('click', () => {{ search.value = ''; kindFilter.value = 'all'; applyFilters(); cy.fit(undefined, 35); }});

    cy.on('tap', 'node, edge', event => {{
      const element = event.target;
      title.textContent = element.isNode() ? element.data('label') : element.data('label');
      detailKind.textContent = element.isNode() ? `${{element.data('kind')}} · ${{element.data('id')}}` : `${{element.data('source')}} → ${{element.data('target')}}`;
      metadata.textContent = element.data('metadata');
      hint.hidden = true;
    }});
    cy.on('tap', event => {{ if (event.target === cy) cy.$(':selected').unselect(); }});
    cy.on('mouseover', 'node', event => {{ document.body.style.cursor = 'pointer'; event.target.connectedEdges().addClass('hover-edge'); }});
    cy.on('mouseout', 'node', () => {{ document.body.style.cursor = 'default'; }});

    const legend = document.getElementById('legend');
    [...new Set(cy.nodes().map(n => n.data('kind')))].sort().forEach(kind => {{
      const row = document.createElement('div'); row.className = 'legend-row';
      const swatch = document.createElement('span'); swatch.className = 'swatch'; swatch.style.background = colours[kind] || '#fff';
      const label = document.createElement('span'); label.textContent = kind;
      row.append(swatch, label); legend.append(row);
    }});
    applyFilters();
  </script>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"output HTML path (default: {DEFAULT_OUTPUT.relative_to(ROOT)})",
    )
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    elements, kinds = build_elements()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(elements, kinds), encoding="utf-8")
    node_count = sum("source" not in element["data"] for element in elements)
    edge_count = len(elements) - node_count
    print(f"wrote {output} ({node_count} nodes, {edge_count} edges)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

