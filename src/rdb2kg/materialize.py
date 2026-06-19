from dataclasses import dataclass, field
from pathlib import Path
import re
import difflib
from urllib.parse import quote
import sqlalchemy as sa
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF

from .r2rml import R2RMLMapping, TriplesMap, ObjectMap


@dataclass
class JoinStats:
    child_col: str
    parent_col: str
    parent_map_id: str
    matched: int = 0
    unmatched: int = 0


@dataclass
class MapStats:
    map_id: str
    sql: str
    rows_read: int = 0
    subjects_created: int = 0
    null_subjects: int = 0
    triples_produced: int = 0
    join_stats: list[JoinStats] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class MaterializationReport:
    map_stats: list[MapStats] = field(default_factory=list)
    total_triples: int = 0
    output_path: str = ""


def expand_template(template: str, row: dict, for_iri: bool = True) -> str | None:
    parts = []
    last_end = 0
    for m in re.finditer(r'\{([^}]+)\}', template):
        col = m.group(1)
        val = row.get(col)
        if val is None:
            return None
        val_str = str(val)
        encoded = quote(val_str, safe='') if for_iri else val_str
        parts.append(template[last_end:m.start()])
        parts.append(encoded)
        last_end = m.end()
    parts.append(template[last_end:])
    return ''.join(parts)


def _col_suggestion(col: str, available: list[str]) -> str:
    matches = difflib.get_close_matches(col, available, n=3, cutoff=0.6)
    if matches:
        return f" (did you mean: {', '.join(matches)}?)"
    return ""


def materialize(
    db_url: str,
    mapping: R2RMLMapping,
    output_path: Path,
) -> tuple[Graph, MaterializationReport]:
    g = Graph()
    report = MaterializationReport(output_path=str(output_path))
    engine = sa.create_engine(db_url)

    parent_cache: dict[str, list[dict]] = {}

    def get_parent_rows(tm: TriplesMap) -> list[dict]:
        if tm.map_id not in parent_cache:
            with engine.connect() as conn:
                result = conn.execute(sa.text(tm.logical_table.get_sql()))
                parent_cache[tm.map_id] = [dict(r._mapping) for r in result]
        return parent_cache[tm.map_id]

    for map_id, tm in mapping.triples_maps.items():
        sql = tm.logical_table.get_sql()
        stats = MapStats(map_id=map_id, sql=sql)

        with engine.connect() as conn:
            try:
                result = conn.execute(sa.text(sql))
                rows = [dict(r._mapping) for r in result]
            except Exception as e:
                stats.warnings.append(f"SQL error: {e}")
                report.map_stats.append(stats)
                continue

        stats.rows_read = len(rows)

        for row in rows:
            if tm.subject_map.template:
                subject_str = expand_template(tm.subject_map.template, row)
            elif tm.subject_map.constant:
                subject_str = tm.subject_map.constant
            else:
                subject_str = None

            if subject_str is None:
                stats.null_subjects += 1
                continue

            subject = URIRef(subject_str)
            stats.subjects_created += 1

            for cls in tm.subject_map.classes:
                g.add((subject, RDF.type, URIRef(cls)))
                stats.triples_produced += 1

            for pom in tm.predicate_object_maps:
                pred = URIRef(pom.predicate)
                om = pom.object_map

                if om.parent_triples_map_id is not None:
                    parent_tm = mapping.triples_maps.get(om.parent_triples_map_id)
                    if parent_tm is None:
                        stats.warnings.append(
                            f"parentTriplesMap not found: {om.parent_triples_map_id}"
                        )
                        continue

                    js = next(
                        (j for j in stats.join_stats if j.parent_map_id == om.parent_triples_map_id),
                        None,
                    )
                    if js is None:
                        js = JoinStats(
                            child_col=om.join_child or "?",
                            parent_col=om.join_parent or "?",
                            parent_map_id=om.parent_triples_map_id,
                        )
                        stats.join_stats.append(js)

                    child_val = row.get(om.join_child) if om.join_child else None
                    if child_val is None:
                        js.unmatched += 1
                        continue

                    parent_rows = get_parent_rows(parent_tm)
                    parent_lookup = {
                        r.get(om.join_parent): r
                        for r in parent_rows
                        if r.get(om.join_parent) is not None
                    }

                    parent_row = parent_lookup.get(child_val)
                    if parent_row is None:
                        js.unmatched += 1
                        continue

                    js.matched += 1
                    if parent_tm.subject_map.template:
                        parent_subject_str = expand_template(
                            parent_tm.subject_map.template, parent_row
                        )
                        if parent_subject_str:
                            g.add((subject, pred, URIRef(parent_subject_str)))
                            stats.triples_produced += 1

                elif om.template is not None:
                    iri_str = expand_template(om.template, row, for_iri=True)
                    if iri_str is None:
                        continue
                    g.add((subject, pred, URIRef(iri_str)))
                    stats.triples_produced += 1

                elif om.column is not None:
                    if om.column not in row:
                        suggestion = _col_suggestion(om.column, list(row.keys()))
                        stats.warnings.append(
                            f"Column '{om.column}' not found in table{suggestion}"
                        )
                        continue

                    val = row[om.column]
                    if val is None:
                        continue

                    if om.datatype:
                        obj = Literal(str(val), datatype=URIRef(om.datatype))
                    elif om.language:
                        obj = Literal(str(val), lang=om.language)
                    else:
                        obj = Literal(str(val))

                    g.add((subject, pred, obj))
                    stats.triples_produced += 1

                elif om.constant is not None:
                    if str(om.constant).startswith("http"):
                        g.add((subject, pred, URIRef(om.constant)))
                    else:
                        g.add((subject, pred, Literal(om.constant)))
                    stats.triples_produced += 1

        if stats.null_subjects > 0:
            stats.warnings.append(
                f"{stats.null_subjects} row(s) produced null subjects and were skipped"
            )
        if stats.rows_read > 0 and stats.subjects_created == 0:
            stats.warnings.append("SQL returned rows but no subjects were created")
        if stats.rows_read == 0:
            stats.warnings.append("SQL returned no rows — triples map produced nothing")

        report.map_stats.append(stats)
        report.total_triples += stats.triples_produced

    engine.dispose()
    g.serialize(destination=str(output_path), format="turtle")
    return g, report


