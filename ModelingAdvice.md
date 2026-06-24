# Modeling Advice

Hard-won ontology-modeling guidance that the assistant **must consult** when
designing an ontology and its R2RML mapping (Steps 2–3 of the workspace
workflow).

This file is **authoritative**: where it conflicts with the general conventions
in `workspace/CLAUDE.md`, the guidance here wins. Treat each entry as a rule,
not a suggestion, unless it says otherwise.

> Status: being filled in. Entries are added as the maintainer provides them.
> Each entry should be a discrete, self-contained rule phrased as "do X (because
> Y)" rather than a vague principle. Add a short worked example where it helps.

---

## Naming

### The sentence rule: a property name should read as the verb in "Subject verbs Object"

Name every property so that `subject property object` reads like a grammatical
sentence, with the property playing the role of the verb. Read the triple aloud
to check it.

- Good: `Customer purchases Product`, `Customer owns Product` — the property
  (`purchases`, `owns`) is a real verb phrase and the sentence reads naturally.
- Bad: `Customer product Product` — the property is just the object noun repeated;
  it isn't a verb and says nothing about the relationship.
- Still bad: `Customer hasProduct Product` — `has`-prefixing a noun is the most
  common novice reflex. It technically parses, but it's vague: it hides what the
  relationship actually *is*. Prefer the specific verb (`purchases`, `owns`,
  `rents`, `returns`) that says how the subject relates to the object.

Why it matters: the verb carries the meaning of the edge. A precise verb makes the
ontology self-documenting and forces you to decide what the relationship really is;
a `has`/noun placeholder defers that decision and usually papers over a modelling
gap. Reserve a bare `has...` only when no more specific verb genuinely exists.

## Classes vs. properties

_(to be filled)_

## Reuse and external vocabularies

### Things, not strings

When a field's allowed values form a fixed list — an enumeration, a code list, a
lookup/reference table, a `CHECK (... IN (...))` constraint — do **not** model the
value as a datatype property carrying the raw string (or number). Model each
allowed value as a **thing**: an individual of a minted class that represents the
code list.

For each such field:

- Mint a class for the code list itself (e.g. `OrderStatus`, `Currency`,
  `LifecycleStage`). Declare it `rdfs:subClassOf skos:Concept`. Do **not** create a
  `skos:ConceptScheme`.
- Make each allowed value an individual of that class.
- On each individual, use SKOS to carry the value's data:
  - `skos:notation` — the identifying string/number from the schema (the literal
    that appears in the column).
  - `skos:prefLabel` — the main human-readable label. If the schema or background
    docs supply one, use it. Only if none is available, derive one by title-casing
    the notation (`out_of_service` → `Out Of Service`).
  - `skos:definition`, `skos:altLabel`, etc. — any further descriptive data the
    schema or background docs provide.
- Point the owning entity at the individual with an object property. The owning
  entity is the **subject** (the property's `rdfs:domain`) and the code-list thing
  is the **object** (its `rdfs:range`). Name the property by
  [the sentence rule](#the-sentence-rule-a-property-name-should-read-as-the-verb-in-subject-verbs-object).
  Never a datatype property holding the string.

**Worked example.** A `HardwareAsset` table has a `lifecycle` column with allowed
values `onboarding`, `operating`, `deprecated`, `out_of_service`:

```turtle
:LifecycleStage rdfs:subClassOf skos:Concept .

:inLifecycleState a owl:ObjectProperty ;
    rdfs:domain :HardwareAsset ;
    rdfs:range  :LifecycleStage .

# one individual per allowed value, e.g.:
:lifecycle/out_of_service a :LifecycleStage ;
    skos:notation "out_of_service" ;
    skos:prefLabel "Out Of Service" .   # title-cased only because no label was given
```

So `:asset/42 :inLifecycleState :lifecycle/out_of_service` — subject is the
`HardwareAsset`, object is the thing, never the bare string `"out_of_service"`.

**Mapping mechanics.** These code-list classes do not get an ordinary
per-row TriplesMap over a data table. Instead, build the individuals' IRIs with an
`rr:template` keyed on the notation value, so every reference to the same value
resolves to the same IRI. The object property on the owning table uses the same
template against its (string/number) column, which is how the join to the thing is
made without a FK. (`examples/chinook/mapping.ttl` shows this pattern for country
codes via a SQL `CASE` that normalises the column to the notation used in the
template.)

This is the payoff hinted at under "Concepts aren't tables → a concept has no
table at all": the code list is a real concept whose individuals are identified by
notation and minted by template, not stored as rows to be walked.

## Modeling patterns

### Concepts aren't tables

Do not assume one table = one class. The relational schema reflects storage and
normalization decisions, not the conceptual model. A class may map to a table, to
part of a table, to several tables joined, or to no table at all. Decide what the
*concept* is first (driven by the competency questions), then find where its data
lives. Common cases:

- **One table → one class.** The straightforward case. Still confirm the table
  really represents a single coherent concept, not several bundled together.

- **A concept is part of a table (a filtered subset).** A `type`/`status`/
  `category` discriminator column often means the table holds several concepts.
  `Account` rows with `type = 'savings'` vs `'checking'` may be distinct classes
  (`SavingsAccount`, `CheckingAccount`); `Party` with `type = 'person'` vs
  `'organization'` almost certainly are. Map these with an R2RML `rr:sqlQuery`
  (or a view) that filters on the discriminator, one TriplesMap per class.

- **A concept spans several joined tables.** When essential information is split
  across tables by normalization, the concept is the *join*, not any single
  table. E.g. a `Customer` concept whose address lives in a separate `Address`
  table, or an `Order` that only makes sense joined with `OrderStatus`. Use an
  `rr:sqlQuery` that joins them as the logical table for the class.

- **A concept is hidden in a join/junction table.** A pure many-to-many junction
  (just two FKs) usually encodes a *relationship*, so it becomes an object
  property, not a class. But if the junction carries attributes that are part of
  *what the relationship is*, it has become a concept in its own right (an
  "associative entity") and deserves a class — e.g. `Enrollment` with a grade, or
  `OrderLine` with quantity and price.

  Be careful what counts as a defining attribute. Provenance and temporal
  bookkeeping columns — `created_at`, `updated_by`, `source_system`, `valid_from`,
  a soft-delete flag — do **not** by themselves promote a junction to a class.
  Almost every table has those, and they describe the *record*, not the
  relationship. Promote only when the extra columns carry domain meaning the
  competency questions actually ask about (a grade, a price, a quantity), not
  generic audit metadata.

- **A concept is several columns of one row (an embedded value).** Repeated
  column groups like `ship_street, ship_city, ship_zip` (and a parallel
  `bill_*` set) are an `Address` concept embedded in the row. Lift it into its
  own class with its own subject IRI rather than flattening the columns onto the
  owner.

- **One column encodes several concepts (overloaded columns and key/value
  tables).** Sometimes one relational slot is carrying meaning that should be
  several properties or classes. Two common shapes:
  - An *overloaded column* packs distinct meanings into one field — a `notes`
    column that sometimes holds a phone number, a `code` whose prefix encodes a
    category.
  - An *EAV table* (entity-attribute-value) is a generic key/value design: rows
    like `(entity_id, attribute_name, value)` instead of real columns, so one
    physical table stands in for many logical properties. (E.g. a `product_attrs`
    table with rows `(42, 'color', 'red')`, `(42, 'weight', '3kg')`.)

  In both cases, unpack the hidden structure into proper named properties (and
  classes where warranted) instead of mirroring the storage trick. Be guided by
  the competency questions — only model the distinctions a question actually needs.

- **A concept has no table at all.** Not every class needs a TriplesMap with a
  local logical table. Some concepts come from the domain (background docs,
  external standards) rather than from stored rows. The most important case —
  turning a string-valued lookup column (a country name, a currency code) into a
  link to a real individual — is covered by the
  [Things, not strings](#things-not-strings) rule.

The throughline: let the competency questions and the domain define the concepts,
then map each concept to whatever relational shape (whole table, filtered subset,
join, column group, or external IRI) actually holds its data.

### No orphan classes: the ontology must be connected

Every class must connect to the rest of the ontology through at least one object
property — one whose `rdfs:domain` or `rdfs:range` is that class and whose other
end is another class in the ontology. In graph-theory terms, take the *class
graph* (classes as nodes, object properties as edges between their domain and
range): it must form a **single connected component**. No class may sit off on its
own, reachable from nothing and reaching nothing.

A class with only datatype properties (it just hangs literals off itself) is the
typical offender: it's an island. If you've minted such a class, that's a signal
to ask how it actually relates to the rest of the model and to add the object
property that expresses that relationship.

- Bad: a `Department` class with only `name` and `budget` datatype properties,
  connected to nothing — even though every department obviously *employs*
  employees and *belongs to* an organization.
- Good: `Employee worksIn Department`, `Department partOf Organization` — now
  `Department` is woven into the graph.

Check this before finalising the ontology: if the class graph has more than one
component, the model is telling you a relationship is missing (or that a stray
class shouldn't exist at all). The code-list classes from
[Things, not strings](#things-not-strings) satisfy this automatically — each is
the range of the object property that links it to its owning entity.

### Commonality and variability: use subclass (or subproperty) to share structure while preserving differences

When several things share a common structure but differ in ways that matter to
the domain, model the shared part as a superclass and the distinct variants as
subclasses. This is the **Commonality and Variability (C&V)** pattern. The
superclass captures what all variants have in common; each subclass adds only
what makes that variant different.

The most common implementation is `rdfs:subClassOf`. Use `rdfs:subPropertyOf`
the same way when the varying thing is a relationship rather than an entity.

**When to reach for it.** Look for it whenever:
- A discriminator column (`type`, `category`, `kind`) splits rows into groups
  that share most properties but differ on a meaningful subset.
- Two or more things "have a mechanism" (or a process, or a role) but each gets
  that mechanism from a different source or with different constraints.
- You find yourself writing the same property twice with slightly different
  range restrictions — that's often a sign a superclass is missing.

**Worked example — Fraud cases in a government-funding domain.**
Both *financial fraud* (receiving money you don't deserve) and *non-financial
fraud* (gaining preferential treatment, protected-class advantage, etc.) share
a `mechanism`: the means by which the fraud is carried out. But the mechanism
for financial fraud must involve a means of collecting money; non-financial
fraud has no such requirement.

Model this as:

```turtle
:FraudCase a owl:Class .

# shared structure — every fraud case has a mechanism
:hasMechanism a owl:ObjectProperty ;
    rdfs:domain :FraudCase ;
    rdfs:range  :FraudMechanism .

# variant 1: financial fraud adds a money-collection mechanism
:FinancialFraudCase rdfs:subClassOf :FraudCase .

:hasMoneyCollectionMechanism a owl:ObjectProperty ;
    rdfs:subPropertyOf :hasMechanism ;
    rdfs:domain :FinancialFraudCase ;
    rdfs:range  :MoneyCollectionMechanism .

# variant 2: non-financial fraud — inherits hasMechanism, adds nothing new
:NonFinancialFraudCase rdfs:subClassOf :FraudCase .
```

`FinancialFraudCase` and `NonFinancialFraudCase` both inherit `hasMechanism`
from `FraudCase`. Only `FinancialFraudCase` additionally requires a
`hasMoneyCollectionMechanism`, which is itself declared a `subPropertyOf
hasMechanism` — so it satisfies the shared constraint while carrying the
tighter range restriction. A query over all fraud cases can ask for
`hasMechanism` universally, while a financial-fraud query asks for
`hasMoneyCollectionMechanism` specifically.

**Mapping mechanics.** In R2RML, the discriminator column drives this:
use one TriplesMap per subclass, each with an `rr:sqlQuery` (or view) that
filters on the discriminator value. The superclass properties are declared once
in the ontology and inherited; only the subclass-specific properties need
additional TriplesMaps. (This is the same filter-on-discriminator shape
described in [Concepts aren't tables](#concepts-arent-tables).)

**Don't overdo it.** Subclass only when the variants differ in a way the
competency questions actually ask about — when different queries, constraints,
or properties apply to one variant and not others. If the only difference is a
label or a code value, a [code-list individual](#things-not-strings) is enough;
you don't need a subclass per value.

## Anti-patterns to avoid

_(to be filled)_

## Provenance and documentation

### Cite your sources: use rdfs:comment and rdfs:seeAlso to record where classes and properties come from

When a class or property is drawn from — or aligned with — an external standard,
regulation, specification, or reference model, record that provenance directly on
the term. Do not rely on the mapping file, commit messages, or tribal knowledge to
carry this information; put it in the ontology itself so any consumer of the graph
can see it.

Use these two annotations:

- **`rdfs:comment`** — a human-readable note explaining the source and, if
  useful, how the term relates to it. Write it as a sentence or short paragraph.
  Include the source name, version or date if known, and any deviation from the
  source definition.

- **`rdfs:seeAlso`** — a URI pointing directly at the authoritative definition:
  a spec section, a regulation paragraph, a published ontology term, a schema.org
  page, etc. Prefer the most stable, resolvable URI you can find. Multiple
  `rdfs:seeAlso` triples are fine when more than one source applies.

```turtle
:FinancialFraudCase a owl:Class ;
    rdfs:subClassOf :FraudCase ;
    rdfs:comment "Fraud involving improper receipt of government funds. Defined in "
                 "accordance with OMB Circular A-123, Appendix C, §3.1." ;
    rdfs:seeAlso <https://www.whitehouse.gov/omb/management/office-federal-financial-management/> .

:hasMechanism a owl:ObjectProperty ;
    rdfs:domain :FraudCase ;
    rdfs:range  :FraudMechanism ;
    rdfs:comment "The means by which the fraud was carried out. Concept adapted from "
                 "the ACFE Fraud Tree taxonomy." ;
    rdfs:seeAlso <https://www.acfe.com/fraud-resources/fraud-tree> .
```

**When the term is reused verbatim.** If you are minting a local IRI for a
concept that is already defined in a published ontology (rather than importing
the external IRI directly), use both annotations: `rdfs:comment` to say it is
equivalent to the external term, and `rdfs:seeAlso` to point at it. Consider
also adding an `owl:equivalentClass` or `owl:equivalentProperty` triple if
alignment matters for reasoning.

**When you deviate from a source.** If your definition narrows, broadens, or
otherwise differs from the cited source, say so explicitly in `rdfs:comment`.
"Adapted from X — restricted here to cases involving federal funds" is more
useful than a bare citation that implies exact alignment.

**Minimum bar.** If you know a term was inspired by or matches something
external, add at least an `rdfs:comment` naming the source even if you cannot
find a stable URI for `rdfs:seeAlso`. A prose citation is better than silence.
