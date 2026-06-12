# Manifesto

In 2026, a team should be able to do a knowledge graph proof of concept over an existing relational database in an afternoon.

They should not need to replace their database.

They should not need to buy a graph platform.

They should not need to invent a proprietary graph model.

They should not need to hand-code a one-off ETL pipeline.

They should not need to become Semantic Web experts before seeing one useful result.

They should be able to:

- inspect the relational schema,
- draft or provide an ontology,
- generate or edit an R2RML mapping,
- materialize RDF,
- load it into a standards-based RDF store,
- run SPARQL,
- and iterate.

This project exists to make that path obvious.

## Make the boring path boring

Relational databases are everywhere. Ontologies are how we say what things mean. RDF is a standard graph data model. R2RML is a standard way to describe mappings from relational databases to RDF. SPARQL is a standard query language for RDF graphs.

None of that should be exotic.

The base case is simple:

- tables contain rows,
- rows describe things,
- primary keys identify things,
- columns give values,
- foreign keys create links,
- mappings say how those things become RDF,
- ontologies say what those things mean.

There are real subtleties. There always are. But the first useful result should not require heroic effort.

The boring path should be boring.

## Standards should feel practical

The RDF and ontology ecosystem already has much of what companies need:

- a standard graph model,
- a standard query language,
- standard ontology languages,
- standard mapping languages,
- mature RDF stores,
- portable data,
- reusable vocabularies,
- and decades of modeling experience.

But the on-ramp has often been too steep.

A person asked to “try knowledge graphs” over an existing database should not have to navigate a maze of academic tools, mysterious configuration files, fragile demos, unclear error messages, and silent failures before they can show anything useful.

This project is not trying to invent a new graph model, a new query language, or a new mapping vocabulary.

The standards already exist.

This project exists to make them easy to try.

## A proof of concept is a social object

A POC is not just code.

A good POC gives people something they can look at, question, improve, and explain:

- Here is the relational schema.
- Here is the ontology.
- Here is the mapping.
- Here are the triples.
- Here are the queries.
- Here are the answers.
- Here is how we know it worked.

That is the point.

A knowledge graph POC should help a team understand the relationship between the data they already have and the concepts they care about.

It should make the approach concrete.

It should make the standards visible.

It should make the next step obvious.

## Direct first, semantic next

There is value in a direct relational-to-RDF mapping:

- one table becomes one class,
- one row becomes one resource,
- one column becomes one property,
- one foreign key becomes one relationship.

That is not the end of the story, but it is a good beginning.

The more important step is the semantic one:

- ugly database structures mapped to meaningful domain concepts,
- implementation details separated from business meaning,
- relational joins turned into graph relationships,
- local schemas connected to shared vocabularies,
- data made usable through an ontology.

This project should support both.

First, get triples.

Then, make them meaningful.

## Error messages should teach

A tool that produces no triples and gives no explanation is not a tool for adoption.

This project should explain itself.

When a mapping fails, the user should know why.

When a join condition references a missing column, the user should see the table, the column, and likely alternatives.

When a triples map produces no output, the user should see whether the SQL returned no rows, the subject map produced nulls, or the object maps were suppressed.

When datatypes, IRIs, blank nodes, or language tags behave unexpectedly, the tool should make the behavior visible.

The tool should not merely execute mappings.

It should help people understand them.

## This is infrastructure, not a platform

The goal is not to create a new closed ecosystem.

The goal is to support the existing open one.

A successful outcome is that more people use:

- RDF,
- OWL,
- RDFS,
- SHACL,
- SPARQL,
- R2RML,
- standard RDF stores,
- and ordinary relational databases together.

A successful outcome is that an internal champion can say:

> We do not need to replace everything. We can map what we have, use standards, and learn from there.

A successful outcome is that a consultant, student, architect, or developer can demonstrate the standards-based path without spending days wiring together fragile pieces.

## The promise

You have a relational database.

You have, or want, an ontology.

You want a knowledge graph POC.

This should be easy.

This project exists to make it easy.
