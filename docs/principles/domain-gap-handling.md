# Domain Gap Handling Principle

When a Lex-Orchestra subagent encounters knowledge it does not have — regulatory facts,
juristic judgments, missing source PDFs, undocumented architectural decisions — it does
not improvise. It writes a gap notice and stops.

This is the third human gate in Lex's agent workflow (alongside Plan-Approval and
PR-Review). It exists because Lex's core value proposition is "Trust in Code" — and
trust is destroyed the moment an agent fabricates a compliance fact from training data.

---

## Rules

1. **Stop on domain gap, do not improvise.** When an agent encounters a regulatory,
   juristic, or domain-specific question it cannot answer from the graph, ADRs, or
   `docs/sources/`, it stops. It does not "use best judgment". It does not "make a
   reasonable assumption". It writes a gap notice.

2. **Gap notices are decision requests, not bug reports.** A gap notice describes
   what was attempted, where the knowledge ends, what would be needed to continue, and
   who is the appropriate decider (Thomas, an external expert, or "needs research").

3. **Every gap notice has an owner and a resolution path.** A gap notice without
   "wer entscheidet" and "wie weiter" is not a gap notice — it is a graveyard entry.

4. **The cure for a gap is decision, not invention.** Resolution paths are: source
   acquisition (PDF in `docs/sources/`), ADR writing (decision recorded), scope
   shrinking (feature deferred), or external consultation (legal expert).

5. **Resolved gaps move to `done/`.** Gap files remain visible during resolution.
   Once resolved (source acquired, ADR written, scope cut), they move to
   `docs/gaps/done/` with a brief resolution note appended.

---

## When to write a gap notice

Write a gap notice when **any** of these is true mid-task:

- A regulatory citation (Art., §, Section) cannot be verified against
  `docs/sources/` or existing ADRs
- A compliance assertion ("this control is sufficient for...") requires juristic
  judgment beyond what is in the graph
- A node type, relationship, or property referenced by the user does not exist in
  the schema and is not on a planned roadmap
- A service classification (country, category, AVV/SCC requirement) is needed but
  not in the graph and not in a source PDF
- An architectural decision must be made that no existing ADR covers (this is
  Pauls' "undocumented architectural fork" — same mechanism)
- A source the agent should rely on is missing from `docs/sources/` or out of date

Do **not** write a gap notice for:

- Genuine bugs (use issue tracker)
- User-experience improvements (use plan files or ADRs)
- Minor implementation choices the SWE can decide (variable names, function
  signatures, internal structure)
- Information that is in the graph but the agent didn't query yet (verify first)

---

## Gap notice format

File path: `docs/gaps/YYYY-MM-DD-<topic>-<short-description>.md`

Example: `docs/gaps/2026-06-15-avv-section-x-no-source.md`

Structure:

```markdown
# Gap: <Short Title>

**Date:** 2026-MM-DD
**Status:** Open | In Resolution | Resolved
**Surfaced by:** <agent name or "Thomas">
**Decider:** <Thomas | external expert | research needed>
**Blocks:** <Task ID or "none">

---

## What was attempted

<1-3 sentences: what task, what step, what was being built>

## Where the knowledge ends

<Concrete description of the gap. What specifically is missing? Be precise —
"GDPR Art. 28 requirements for AI-specific processors" is better than "AVV
unclear">

## What would be needed to continue

<Possible resolution paths. Examples:
- Source PDF: "DSK Kurzpapier 13 (AVV)" in `docs/sources/`
- ADR: "How to handle AI-specific sub-processors in AVV templates"
- External: "Need legal review of clause X from a DSGVO-qualified lawyer"
- Scope cut: "Feature can ship without this section if marked as gap-hint">

## Why this is a gap, not a guess

<1-2 sentences: why improvisation here would damage the product's trust
proposition. Connects back to the source-of-truth rule>

---

## Resolution (appended after decision)

**Resolved:** 2026-MM-DD
**Decision:** <one-line summary>
**Action taken:** <source acquired / ADR written / scope cut / external consulted>
**Reference:** <link to source PDF, ADR file, or external document>
```

---

## Who decides what

Different gap types route to different deciders:

| Gap Type | Decider | Typical Resolution |
|---|---|---|
| Missing source PDF | Thomas | Acquire and add to `docs/sources/` |
| Architectural decision | Thomas | Write ADR |
| Juristic judgment | External legal expert | Consult, document advice, update graph |
| Schema extension | Thomas + cypher-expert | New node-type via plan-file + Cypher seed |
| Feature scope | Thomas | Defer to post-release backlog or cut |
| Conflicting ADRs | Thomas | Supersede old ADR, write new one |

---

## What this principle is NOT

- **Not a way to avoid difficult work.** A gap notice that says "this is hard,
  someone else figure it out" is rejected. The point is documented stopping with
  a clear path forward.

- **Not bureaucracy.** A gap notice should take 5-10 minutes to write. If it's
  taking longer, the gap is bigger than expected and probably needs to be split.

- **Not a way to bypass the source-of-truth rule.** Writing "gap: no source for
  X, but I'll fill it in anyway" defeats the purpose. The rule is stop, then
  resolve, then continue.

- **Not for every uncertainty.** Implementation choices (variable names, internal
  structure) are not gaps. Domain knowledge, regulatory facts, and architectural
  forks are gaps.

---

## Connection to other principles

- **[Doc quality](doc-quality.md)** — gap notices are the operational mechanism
  for "no hardcoded legal facts" and "every section has a source"
- **Review gates** — gap notices are the third human gate
  (alongside plan approval and PR review)
- **Approval protocol** — gap resolution requires an explicit maintainer decision
  before continuing, same discipline as plan approval

---

## File lifecycle

```
docs/gaps/                          # active gaps
├── 2026-06-15-avv-no-dsk-source.md
├── 2026-06-18-ai-act-gpai-boundary.md
└── done/                           # resolved gaps
    └── 2026-05-30-stripe-country-property.md
```

Active gaps in `docs/gaps/` block their related tasks. Resolved gaps in
`docs/gaps/done/` are historical record — useful for understanding what
decisions were made and why.

---

## Why this principle matters

Lex-Orchestra's positioning depends on **deterministic, evidence-based outputs**.
A single fabricated compliance claim, traced back to "the agent guessed", destroys
the credibility of every other output.

The competitive landscape is full of LLM-wrapper tools that confidently produce
plausible-sounding compliance content. Lex differentiates by stopping when it
doesn't know — and making that stopping visible and resolvable.

Gap notices are the mechanism that makes this discipline operational, not
aspirational.
