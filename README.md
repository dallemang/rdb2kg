# rdb2kg

A standards-based POC kit for turning relational databases into ontology-backed RDF knowledge graphs.

**Make the boring path boring.**

> **Getting started:** see [SETUP.md](SETUP.md) for a step-by-step Windows install
> and an end-to-end trial run against the bundled Chinook database.

## What is this?

`rdb2kg` is intended to make the standard relational-to-RDF path easy to demonstrate, test, and explain.

Given a relational database and an R2RML mapping, it should be easy to:

- inspect the database schema,
- generate or edit a mapping,
- materialize RDF triples,
- load them into a local RDF store,
- run SPARQL queries,
- compare expected results,
- and explain what happened.

The goal is not to invent a new graph model, a new query language, or a new mapping vocabulary.

The goal is to make the existing standards usable for ordinary proof-of-concept work.

## Why?

A company should be able to try a knowledge graph over an existing relational database without replacing the database, buying a platform, or hand-writing a one-off ETL pipeline.

The standards already exist:

- relational databases store the data,
- R2RML describes how relational data maps to RDF,
- RDF provides the graph data model,
- ontologies describe the meaning of the data,
- SPARQL queries the graph.

This project exists because that path should be easier than it usually is.

## Intended workflow

The intended workflow is:

```text
relational database
    + ontology
    + R2RML mapping
        ↓
materialized RDF triples
        ↓
local RDF store
        ↓
SPARQL queries
        ↓
explainable POC
