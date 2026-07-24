/**
 * Language selection for graph node properties.
 *
 * The graph carries some fields in both languages (title_en / title_de) and
 * some in German only: label_de, note_de and duration_de have no English
 * sibling at all. English wins wherever it exists. A German-only field stays
 * visible, because hiding it would drop the information rather than translate
 * it.
 *
 * Shared by the schema Inspector (app/schema/page.tsx) and the ego-graph side
 * panel (components/EgoGraph.tsx). Both used to pick the language themselves,
 * and the panel had the order inverted, so a node with a perfectly good
 * title_en was displayed in German.
 */

type NodeProps = Record<string, unknown>

function firstFilled(...values: unknown[]): unknown {
  for (const v of values) {
    if (v !== undefined && v !== null && v !== '') return v
  }
  return undefined
}

/**
 * Value of `base` in the display language: `<base>_en`, else `<base>_de`, else
 * the unsuffixed property. The unsuffixed one comes last on purpose — on Law
 * nodes `title` holds the German wording while `title_en` holds the English.
 */
export function pickLang(props: NodeProps, base: string): unknown {
  return firstFilled(props[`${base}_en`], props[`${base}_de`], props[base])
}

/** Same, coerced to a string for direct rendering. */
export function pickLangString(props: NodeProps, base: string): string {
  const v = pickLang(props, base)
  return v === undefined ? '' : String(v)
}

/**
 * True when a `*_de` property merely repeats an English sibling that is already
 * on screen, so a property table can drop it.
 *
 * Returns false for German-only fields: they are the sole carrier of that
 * information until the graph gains an English variant, and blanking them would
 * be a loss, not a cleanup.
 */
export function isRedundantGermanProp(key: string, props: NodeProps): boolean {
  if (!key.endsWith('_de')) return false
  const en = props[`${key.slice(0, -3)}_en`]
  return en !== undefined && en !== null && en !== ''
}
