from html import escape
from pathlib import Path
import json

from rdflib import Graph, URIRef
from rdflib.namespace import RDF, RDFS, OWL

from .workspace_service import read_questions, OUTPUT_DIR
from .sparql_service import query_sparql

_SYSTEM_PREFIXES = (
    "http://www.w3.org/2002/07/owl#",
    "http://www.w3.org/2000/01/rdf-schema#",
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "http://www.w3.org/2001/XMLSchema#",
    "http://www.w3.org/2004/02/skos/core#",
)

_CYTOSCAPE_CDN = "https://unpkg.com/cytoscape@3.28.1/dist/cytoscape.min.js"
_MAX_RESULT_ROWS = 5


def _local(uri: str) -> str:
    return uri.split("#")[-1] if "#" in uri else uri.rstrip("/").split("/")[-1]


def _is_system(uri: str) -> bool:
    return any(uri.startswith(p) for p in _SYSTEM_PREFIXES)


def _build_elements(ontology_path: Path) -> list[dict]:
    g = Graph()
    g.parse(str(ontology_path), format="turtle")

    # Collect every class URI mentioned anywhere in the ontology
    classes: dict[str, bool] = {}  # uri -> is_external

    def add_cls(u: object) -> None:
        if isinstance(u, URIRef):
            classes.setdefault(str(u), _is_system(str(u)))

    for s in g.subjects(RDF.type, OWL.Class):
        add_cls(s)
    for s, _, o in g.triples((None, RDFS.subClassOf, None)):
        add_cls(s)
        add_cls(o)
    for _, _, o in g.triples((None, RDFS.domain, None)):
        add_cls(o)
    for _, _, o in g.triples((None, RDFS.range, None)):
        add_cls(o)

    nodes = [
        {"data": {"id": u, "label": _local(u), "type": "external" if ext else "class"}}
        for u, ext in classes.items()
    ]

    edges = []
    eid = 0

    for prop in g.subjects(RDF.type, OWL.ObjectProperty):
        label = _local(str(prop))
        doms = [str(o) for o in g.objects(prop, RDFS.domain) if isinstance(o, URIRef)]
        rngs = [str(o) for o in g.objects(prop, RDFS.range) if isinstance(o, URIRef)]
        for d in doms:
            for r in rngs:
                if d in classes and r in classes:
                    edges.append({"data": {
                        "id": f"e{eid}", "source": d, "target": r,
                        "label": label, "type": "objectProperty",
                    }})
                    eid += 1

    for s, _, o in g.triples((None, RDFS.subClassOf, None)):
        if isinstance(s, URIRef) and isinstance(o, URIRef):
            sv, ov = str(s), str(o)
            if sv in classes and ov in classes:
                edges.append({"data": {
                    "id": f"e{eid}", "source": sv, "target": ov,
                    "label": "", "type": "subClassOf",
                }})
                eid += 1

    return nodes + edges


def _result_summary(graph_path: Path, sparql: str) -> str:
    try:
        result = query_sparql(graph_path, sparql)
        rows = result.rows
        if not rows:
            return "(no results)"
        shown = rows[:_MAX_RESULT_ROWS]
        cols = result.columns
        lines = [", ".join(f"{c}: {row.get(c, '')}" for c in cols) for row in shown]
        if len(rows) > _MAX_RESULT_ROWS:
            lines.append(f"… {len(rows) - _MAX_RESULT_ROWS} more row(s)")
        return "\n".join(lines)
    except Exception as exc:
        return f"(error: {exc})"


# Cytoscape style objects: built as Python dicts so json.dumps handles the
# braces — avoids wrestling with {{ }} escaping in a big f-string.
_CY_STYLE = [
    {
        "selector": 'node[type = "class"]',
        "style": {
            "shape": "rectangle",
            "background-color": "#4a90d9",
            "color": "#fff",
            "label": "data(label)",
            "text-valign": "center",
            "text-halign": "center",
            "padding": "10px",
            "font-size": "13px",
            "width": "label",
            "height": "label",
        },
    },
    {
        "selector": 'node[type = "external"]',
        "style": {
            "shape": "rectangle",
            "background-color": "#9a9a9a",
            "color": "#fff",
            "label": "data(label)",
            "text-valign": "center",
            "text-halign": "center",
            "padding": "10px",
            "font-size": "12px",
            "width": "label",
            "height": "label",
        },
    },
    {
        "selector": 'edge[type = "objectProperty"]',
        "style": {
            "label": "data(label)",
            "curve-style": "bezier",
            "target-arrow-shape": "triangle",
            "line-color": "#555",
            "target-arrow-color": "#555",
            "font-size": "11px",
            "color": "#333",
            "text-background-opacity": 1,
            "text-background-color": "#fff",
            "text-background-padding": "2px",
            "text-rotation": "autorotate",
        },
    },
    {
        "selector": 'edge[type = "subClassOf"]',
        "style": {
            "label": "subClassOf",
            "curve-style": "bezier",
            "target-arrow-shape": "triangle-hollow",
            "line-style": "dashed",
            "line-color": "#888",
            "target-arrow-color": "#888",
            "font-size": "10px",
            "color": "#666",
            "text-background-opacity": 1,
            "text-background-color": "#fff",
            "text-background-padding": "2px",
        },
    },
]

_HTML_HEAD = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>rdb2kg Ontology Report</title>
  <style>
    body { font-family: sans-serif; margin: 2em; color: #222; }
    h1 { border-bottom: 2px solid #4a90d9; padding-bottom: .3em; }
    h2 { color: #4a90d9; margin-top: 1.8em; }
    #cy { width: 100%; height: 600px; border: 1px solid #ccc; border-radius: 4px;
          margin-bottom: 1em; background: #fafafa; }
    .legend { font-size: .85em; color: #555; margin-bottom: 1.5em; }
    table { border-collapse: collapse; width: 100%; margin-top: 1em; }
    th { background: #4a90d9; color: #fff; padding: .6em 1em; text-align: left; }
    td { border: 1px solid #ddd; padding: .6em 1em; vertical-align: top; }
    tr:nth-child(even) td { background: #f8f8f8; }
    pre, code { margin: 0; white-space: pre-wrap; font-size: .82em; font-family: monospace; }
  </style>
</head>
<body>
  <h1>rdb2kg Ontology Report</h1>

  <h2>Ontology Graph</h2>
  <p class="legend">
    <span style="background:#4a90d9;color:#fff;padding:2px 6px;border-radius:2px">blue box</span> ontology class &nbsp;
    <span style="background:#9a9a9a;color:#fff;padding:2px 6px;border-radius:2px">grey box</span> external class &nbsp;
    &#8594; solid arrow: object property &nbsp;
    &#8674; dashed arrow: subClassOf
  </p>
  <div id="cy"></div>

  <h2>Competency Questions</h2>
  <table>
    <thead>
      <tr>
        <th style="width:25%">Question</th>
        <th style="width:45%">SPARQL</th>
        <th style="width:30%">Result summary</th>
      </tr>
    </thead>
    <tbody>
"""

_HTML_TAIL_TMPL = """\
    </tbody>
  </table>

  <script src="{cdn}"></script>
  <script>
    cytoscape({{
      container: document.getElementById('cy'),
      elements: {elements},
      style: {style},
      layout: {{ name: 'cose', padding: 40, nodeRepulsion: 8000,
                idealEdgeLength: 120, animate: false }}
    }});
  </script>
</body>
</html>
"""


def generate_html_report(workspace_dir: Path) -> str:
    workspace_dir = Path(workspace_dir)
    ont_path = workspace_dir / OUTPUT_DIR / "ontology.ttl"
    mat_path = workspace_dir / OUTPUT_DIR / "materialized.ttl"

    elements: list[dict] = []
    if ont_path.exists():
        try:
            elements = _build_elements(ont_path)
        except Exception:
            pass

    rows_html = []
    for q in read_questions(workspace_dir):
        sparql_cell = f"<pre><code>{escape(q.sparql or '(none)')}</code></pre>"
        if q.sparql and mat_path.exists():
            summary = _result_summary(mat_path, q.sparql)
        elif q.sparql:
            summary = "(graph not yet materialized)"
        else:
            summary = "(no SPARQL written)"
        rows_html.append(
            f"      <tr>"
            f"<td>{escape(q.question)}</td>"
            f"<td>{sparql_cell}</td>"
            f"<td><pre>{escape(summary)}</pre></td>"
            f"</tr>\n"
        )

    tail = _HTML_TAIL_TMPL.format(
        cdn=_CYTOSCAPE_CDN,
        elements=json.dumps(elements),
        style=json.dumps(_CY_STYLE),
    )

    return _HTML_HEAD + "".join(rows_html) + tail
