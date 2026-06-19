import tempfile
from pathlib import Path
from rdb2kg.r2rml import parse_mapping

SIMPLE_TTL = """\
@prefix rr: <http://www.w3.org/ns/r2rml#> .
@prefix ex: <http://example.org/> .

<#PersonMap>
    rr:logicalTable [ rr:tableName "Person" ] ;
    rr:subjectMap [
        rr:template "http://example.org/person/{PersonId}" ;
        rr:class ex:Person
    ] ;
    rr:predicateObjectMap [
        rr:predicate ex:name ;
        rr:objectMap [ rr:column "Name" ]
    ] .
"""

JOIN_TTL = """\
@prefix rr: <http://www.w3.org/ns/r2rml#> .
@prefix ex: <http://example.org/> .

<#AuthorMap>
    rr:logicalTable [ rr:tableName "Author" ] ;
    rr:subjectMap [
        rr:template "http://example.org/author/{AuthorId}" ;
        rr:class ex:Author
    ] .

<#BookMap>
    rr:logicalTable [ rr:tableName "Book" ] ;
    rr:subjectMap [
        rr:template "http://example.org/book/{BookId}" ;
        rr:class ex:Book
    ] ;
    rr:predicateObjectMap [
        rr:predicate ex:writtenBy ;
        rr:objectMap [
            rr:parentTriplesMap <#AuthorMap> ;
            rr:joinCondition [ rr:child "AuthorId" ; rr:parent "AuthorId" ]
        ]
    ] .
"""


def _write_ttl(content: str) -> Path:
    f = tempfile.NamedTemporaryFile(suffix=".ttl", mode="w", delete=False, encoding="utf-8")
    f.write(content)
    f.close()
    return Path(f.name)


def test_parse_table_name():
    path = _write_ttl(SIMPLE_TTL)
    try:
        mapping = parse_mapping(path)
        assert len(mapping.triples_maps) == 1
        tm = next(iter(mapping.triples_maps.values()))
        assert tm.logical_table.table_name == "Person"
        assert tm.logical_table.sql_query is None
    finally:
        path.unlink(missing_ok=True)


def test_parse_subject_template_and_class():
    path = _write_ttl(SIMPLE_TTL)
    try:
        mapping = parse_mapping(path)
        tm = next(iter(mapping.triples_maps.values()))
        assert tm.subject_map.template == "http://example.org/person/{PersonId}"
        assert "http://example.org/Person" in tm.subject_map.classes
    finally:
        path.unlink(missing_ok=True)


def test_parse_predicate_object_map():
    path = _write_ttl(SIMPLE_TTL)
    try:
        mapping = parse_mapping(path)
        tm = next(iter(mapping.triples_maps.values()))
        assert len(tm.predicate_object_maps) == 1
        pom = tm.predicate_object_maps[0]
        assert pom.predicate == "http://example.org/name"
        assert pom.object_map.column == "Name"
    finally:
        path.unlink(missing_ok=True)


def test_parse_join_condition():
    path = _write_ttl(JOIN_TTL)
    try:
        mapping = parse_mapping(path)
        book_map = next(tm for tm in mapping.triples_maps.values()
                        if tm.logical_table.table_name == "Book")
        assert len(book_map.predicate_object_maps) == 1
        om = book_map.predicate_object_maps[0].object_map
        assert om.parent_triples_map_id is not None
        assert om.join_child == "AuthorId"
        assert om.join_parent == "AuthorId"
    finally:
        path.unlink(missing_ok=True)
