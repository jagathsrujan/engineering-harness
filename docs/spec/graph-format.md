# Specification: graph format

Normative. Numbered rules are requirements.

## 1. Node kinds

| Kind | Contents |
| ---- | -------- |
| Parameter | Name, symbol, unit, value or interval, provenance, owning component. |
| Relation | A set of parameters, one or more equations, a validity domain, a source reference, a review status. |
| Constraint | A Boolean condition over parameters, with severity. |
| Requirement | A constraint with an owner and a rationale, separated into assumed and required. |
| Decision | A choice among discrete options, with alternatives considered and the reason; the choice activates or deactivates relations. |
| Unknown | A placeholder for something not yet known; blocks verified status until resolved. |
| Component | A grouping with typed ports. |
| Test result | A measured value linked to a parameter; can recalibrate assumptions. |

## 2. Identifiers

2.1 Ids are stable and never reused. A deleted id is retired, not recycled.

2.2 Id forms:

| Kind | Form |
| ---- | ---- |
| Component | `cmp.<dash-path>` |
| Parameter | `cmp.<dash-path>#<name>` |
| Relation | `rl.<slug>` |
| Constraint | `cs.<slug>` |
| Requirement | `rq.<slug>` |
| Decision | `dc.<slug>` |
| Unknown | `uk.<slug>` |
| Test result | `tr.<slug>` |

2.3 A slug is lowercase alphanumerics and dashes. A dash-path is a slug-joined
hierarchy of component names.

## 3. Serialization

3.1 Serialization is plain text, YAML, one file per component, under
`projects/<project>/components/`. It is designed for git diffs (P10).

3.2 The project index is `main.yaml`: the project id, name, component list and
settings.

3.3 A component file contains:

- the component header: id, name, description, and typed ports with role
  `potential` or `flow` per the Modelica convention;
- the component's parameters: id, symbol, unit, value, provenance;
- the relations, constraints, requirements, decisions, unknowns and
  test results declared by that component.

3.4 A relation references parameters of any component by qualified id and
lives in exactly one component file: its declarer.

3.5 Files must remain plain-text and diffable. A graph diff shows the
engineering change and nothing else: no gratuitous key reordering, reformatting,
encoding or line-ending churn.

## 4. Example component file

```yaml
component:
  id: cmp.gearbox-shaft
  name: Gearbox shaft
  ports:
    - { id: cmp.gearbox-shaft#p-out-torque, role: flow, unit: "N*m" }
parameters:
  - id: cmp.gearbox-shaft#d
    symbol: d_shaft
    unit: mm
    value: 25
    provenance: { tag: assumed, note: first cut }
relations:
  - id: rl.shaft-bending-stress
    equations:
      - "sigma_a = 32*M_b / (pi*d**3)"
    params: [cmp.gearbox-shaft#M_b, cmp.gearbox-shaft#d, cmp.gearbox-shaft#sigma_a]
    valid_domain:
      cmp.gearbox-shaft#d: [5, 200]
    source: { kind: pack-entry, ref: mechanical.shaft.bending }
    review: { status: unreviewed }
```

## 5. Relations

5.1 A relation is declared, not directed (P7): it names a set of parameters and
one or more equations, and its direction is a solver decision.

5.2 Every relation carries a validity domain, a source reference, and a review
status. A relation is rejected if it is dimensionally inconsistent (R2).

5.3 A relation's source reference is one of a pack entry, a cited external
source, or a user statement.

5.4 An equation is a single `=` expression between the relation's declared
parameters, using pure numeric factors only (see `docs/spec/solver.md` 4.4-4.5).

## 6. Symbols and values

6.1 A parameter symbol is a globally unique, valid sympy symbol name within a
project; equations reference parameters by symbol.

6.2 In format v0 a value is a plain number. Intervals arrive in a later
revision; the schema will grow without breaking the id scheme.

6.3 A project id starts with `prj.` followed by a slug.
