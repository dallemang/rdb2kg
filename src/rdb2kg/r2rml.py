from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from rdflib import Graph, Namespace, URIRef, Literal, BNode
from rdflib.namespace import RDF

RR = Namespace("http://www.w3.org/ns/r2rml#")


@dataclass
class LogicalTable:
    table_name: str | None = None
    sql_query: str | None = None

    def get_sql(self) -> str:
        if self.table_name:
            return f'SELECT * FROM "{self.table_name}"'
        if self.sql_query:
            return self.sql_query
        raise ValueError("LogicalTable has neither tableName nor sqlQuery")


@dataclass
class ObjectMap:
    column: str | None = None
    datatype: str | None = None
    language: str | None = None
    constant: Any = None
    parent_triples_map_id: str | None = None
    join_child: str | None = None
    join_parent: str | None = None
    template: str | None = None


@dataclass
class PredicateObjectMap:
    predicate: str
    object_map: ObjectMap


@dataclass
class SubjectMap:
    template: str | None = None
    classes: list[str] = field(default_factory=list)
    constant: str | None = None


@dataclass
class TriplesMap:
    map_id: str
    logical_table: LogicalTable
    subject_map: SubjectMap
    predicate_object_maps: list[PredicateObjectMap] = field(default_factory=list)


@dataclass
class R2RMLMapping:
    triples_maps: dict[str, TriplesMap] = field(default_factory=dict)


def _get_one(g: Graph, s, p):
    return next(iter(g.objects(s, p)), None)


def _str(node) -> str | None:
    if node is None:
        return None
    return str(node)


def parse_mapping(path: Path) -> R2RMLMapping:
    g = Graph()
    g.parse(str(path), format="turtle")

    mapping = R2RMLMapping()

    for tm_node in g.subjects(RR.subjectMap, None):
        map_id = str(tm_node)

        lt_node = _get_one(g, tm_node, RR.logicalTable)
        if lt_node is None:
            continue
        table_name = _str(_get_one(g, lt_node, RR.tableName))
        sql_query = _str(_get_one(g, lt_node, RR.sqlQuery))
        logical_table = LogicalTable(table_name=table_name, sql_query=sql_query)

        sm_node = _get_one(g, tm_node, RR.subjectMap)
        template = _str(_get_one(g, sm_node, RR.template))
        constant = _str(_get_one(g, sm_node, RR.constant))
        classes = [str(c) for c in g.objects(sm_node, RR["class"])]
        subject_map = SubjectMap(template=template, classes=classes, constant=constant)

        pom_list = []
        for pom_node in g.objects(tm_node, RR.predicateObjectMap):
            pred = _str(_get_one(g, pom_node, RR.predicate))
            if pred is None:
                pm_node = _get_one(g, pom_node, RR.predicateMap)
                if pm_node:
                    pred = _str(_get_one(g, pm_node, RR.constant))
            if pred is None:
                continue

            om_node = _get_one(g, pom_node, RR.objectMap)
            if om_node is None:
                constant_val = _str(_get_one(g, pom_node, RR.object))
                om = ObjectMap(constant=constant_val)
            else:
                column = _str(_get_one(g, om_node, RR.column))
                datatype = _str(_get_one(g, om_node, RR.datatype))
                language = _str(_get_one(g, om_node, RR.language))
                constant_val = _str(_get_one(g, om_node, RR.constant))
                parent_tm = _str(_get_one(g, om_node, RR.parentTriplesMap))

                join_child = None
                join_parent = None
                jc_node = _get_one(g, om_node, RR.joinCondition)
                if jc_node is not None:
                    join_child = _str(_get_one(g, jc_node, RR.child))
                    join_parent = _str(_get_one(g, jc_node, RR.parent))

                obj_template = _str(_get_one(g, om_node, RR.template))

                om = ObjectMap(
                    column=column,
                    datatype=datatype,
                    language=language,
                    constant=constant_val,
                    parent_triples_map_id=parent_tm,
                    join_child=join_child,
                    join_parent=join_parent,
                    template=obj_template,
                )

            pom_list.append(PredicateObjectMap(predicate=pred, object_map=om))

        mapping.triples_maps[map_id] = TriplesMap(
            map_id=map_id,
            logical_table=logical_table,
            subject_map=subject_map,
            predicate_object_maps=pom_list,
        )

    return mapping
