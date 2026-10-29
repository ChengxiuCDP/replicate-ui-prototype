# Framework adapters

The core workflow is framework-agnostic. Use the adapter that matches evidence found by project inspection; never translate everything into Tailwind by habit.

## Tailwind

- Read the target component and the actual `@theme`, `:root`, or CSS variable source.
- Preserve utility values when moving them to standalone CSS: spacing, font size/line height, radius, color opacity, and breakpoints.
- Prefer the project's semantic variables over copied hex values.
- Record arbitrary values and responsive variants in the handoff map.

## Plain CSS and CSS Modules

- Read the stylesheet imported by the target component and its custom property definitions.
- Preserve cascade order, selector specificity, media queries, and custom property names.
- Do not introduce a framework reset or utility class system into the prototype unless the project already uses one.

## CSS-in-JS and styled systems

- Read the style declaration and the theme/provider source together.
- Extract resolved values only when the theme token cannot be referenced directly in standalone HTML.
- Note any runtime-only state or prop interpolation that the static prototype cannot express.

## React, Vue, Svelte, and Astro

- Treat component markup, slot/prop boundaries, and conditional branches as structural evidence.
- Use the host framework only for source inspection and final translation; the prototype itself should be a standalone HTML artifact.
- Keep stable content names from the source. Do not replace them with `item-1` placeholders.

## Static HTML

- Inspect the document, stylesheet links, local assets, and existing viewport rules.
- Preserve semantic landmarks and existing anchor targets.
- Use a media query for responsive changes before introducing JavaScript.

## Unknown systems

If the system cannot be identified, report what was inspected, use measured CSS values in the prototype, and mark each approximated value. Ask for the target component when a reliable baseline is missing.

