Translate a natural-language question into SPARQL and run it against the materialised knowledge graph in this workspace.

**Question:** $ARGUMENTS

---

## Steps

### 1. Read the ontology

Read `output/ontology.ttl`. Note:
- The base namespace IRI (the `@base` or the prefix declared for the local terms)
- Every `owl:Class` local name
- Every `owl:ObjectProperty` and `owl:DatatypeProperty` local name, plus its `rdfs:domain` and `rdfs:range`

You must use these URIs **exactly** in the SPARQL — a single character difference returns nothing.

### 2. Check the graph exists

If `output/materialized.ttl` does not exist, stop and tell the user to complete
Step 4 of the workflow (run validation) to materialise the graph first.

### 3. Write the SPARQL

Translate the question into a SPARQL SELECT query:
- Add a `PREFIX` declaration for every namespace you reference
- Choose variable names that match the thing they represent (`?artist`, `?album`, not `?x`)
- If the question asks for "all X", use a simple `WHERE { ?x a :X }` pattern
- If the question involves a relationship, trace it through the object properties

Show the SPARQL to the user before running it.

### 4. Run the SPARQL

```python
import sys; sys.path.insert(0, '..')
from pathlib import Path
from rdb2kg.sparql_service import query_sparql
result = query_sparql(Path('output/materialized.ttl'), """
PASTE_YOUR_SPARQL_HERE
""")
print(f"{len(result.rows)} row(s)  columns: {result.columns}")
for row in result.rows[:20]:
    print(row)
```

### 5. Present the results

- Show up to 15 rows in a readable format (a markdown table if the columns are few)
- If there are more rows, state the total and elide the rest: "… 42 more rows"
- If the query returns **no rows**, diagnose before giving up:
  1. Print the distinct classes present in the graph to confirm the data was loaded:
     `SELECT DISTINCT ?type WHERE { [] a ?type }` — do the classes match what you wrote?
  2. Check that PREFIX declarations resolve to the same namespace as the ontology URIs
  3. Suggest the corrected query and re-run it
