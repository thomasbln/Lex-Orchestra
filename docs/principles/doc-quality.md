# Doc Quality Principle

Generated documents must only contain content backed by scan evidence or graph data.
No section, checklist item, or placeholder should appear unless a signal, node, or
configured value justifies its presence.

---

## Rules

1. **Signal-driven sections** — render only when `has_signal()` returns true for the
   relevant category. Example: LLM embedding controls only when `ai_llm` signal present.

2. **No static checklists** — `- [ ]` items the user must fill in manually are gap
   markers, not document content. Use gap_analyzer instead: identify the gap, name the
   missing input, link to where to provide it.

3. **No hardcoded legal facts** — dates, article numbers, threshold values belong in
   Law-Nodes in the graph. Templates read them via context variables passed by
   `document_architect.py`. Graph = single source of truth for legal facts.

4. **Placeholder text is a gap** — `(ausfüllen)`, `________`, `[Name]` signals missing
   data. Prefer: omit the field and surface the gap, or use the `?`-marker macro.

5. **Every rendered section has a source** — if you cannot point to a graph node, scan
   signal, or `project_config` field that justifies a section, it must not render.

6. **Tool-derived values are marked, not hidden** — when a value is inferred by the tool
   rather than evidenced for the specific service/activity (e.g. a processing purpose
   derived from the service *category*, a generic retention period), render it with the
   `≈` inferred-marker (`_marker.md.j2`: `inferred_mark` + `inferred_legend`) so a reader
   never mistakes a suggestion for an established fact. The legend is **conditional** —
   render it once per table, only when at least one cell carries the marker (an unused
   legend is itself tool-noise). The marker is **reusable**: the same mechanism applies to
   future derived fields (§ 7 retention periods, AI-Act-Manifest justifications) — do not
   invent a second marking vocabulary for them.

---

## Legal Grounding

This principle is not just a design preference — evidence-based generation is legally
safer than the "complete-with-placeholders" alternative.

### GDPR Art. 28 (DPA)
A DPA with placeholders like "☐ Processor" is not a valid DPA. Art. 28(3) requires
concrete content — missing mandatory fields make the contract contestable, not merely
"incomplete". A DPA that names only verified processing activities is legally safer than
one that pretends to cover everything.

### GDPR Art. 30 (RoPA)
The Record of Processing Activities must document *actual* processing. Art. 30(5) even
provides exemptions for small companies. Fictitious entries (placeholders for services
that might be in use) can be classified by supervisory authorities as faulty
documentation — which is worse than a shorter but correct RoPA.

### GDPR Art. 35 (DPIA)
A DPIA with unfilled risk fields is not a DPIA. It does not satisfy the threshold review
per Art. 35(3). Correct approach: signal clearly "DPIA required, data still missing"
via gap hint — rather than a form that looks like a DPIA but is not one.

### EU AI Act Art. 11 (Technical Documentation)
Art. 11 in conjunction with Annex IV defines minimum content requirements. Empty fields
in technical documentation are not neutral during a market surveillance review — they
can be used as evidence of non-compliance. Correct partial data + explicit "still open"
marking is better than a complete form with false entries.

### EU AI Act Art. 13 (Transparency)
Transparency means correctness, not completeness at any cost. An AI Act Manifest that
contains only verified information and marks missing data as "not determined" fulfills
the transparency principle better than one with phantom entries.

---

## Correct vs. Placeholder Comparison

| Approach | Legally | Practically |
|---|---|---|
| Complete with placeholders | ❌ Pseudo-fulfillment, contestable | ❌ User cannot see what is missing |
| Reduced + correct + gap hints | ✅ Demonstrably correct | ✅ User sees exactly what is missing |

---

## Constraint: Legally Required Fields

Where a field is legally mandatory under GDPR/EU AI Act (e.g., DPA Art. 28(3)(a) —
subject matter of processing), the gap hint must clearly signal this field is
**legally required**, not merely recommended. Gap hints must distinguish between:

- `REQUIRED` — missing field violates a specific article (blocks document validity)
- `RECOMMENDED` — missing field reduces document quality but does not block validity

Gap-analyzer priority levels are a tracked follow-up.

---

## Application

- **New templates:** start empty, add sections only as signals are defined
- **Template review:** for each section, ask "what signal/node activates this?"
- **Gap hints:** use `gap_analyzer.py` — name the gap, cite the article, link to workspace

## Where these rules live in code

| Mechanism | Implementation |
|---|---|
| Three-layer evidence markers (✓ / ? / ⊘) | `src/templates/_marker.md.j2` |
| Signal-driven DSFA sections | `src/documents/builders/dsfa_builder.py` |
| Gap hints — next steps + hint layer | `src/scanner/gap_analyzer.py` |

## Language doctrine

UI chrome is English-only; generated documents follow `doc_language`.
(Graph property *values* like `title_de` and legal document content are data, not chrome.)

---

> **Disclaimer:** This document is not legal advice. For final documents submitted to
> regulators or signed as contracts, review by a qualified lawyer is required.
