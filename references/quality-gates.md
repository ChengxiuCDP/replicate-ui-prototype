# Prototype quality gates

These gates distinguish what can be checked mechanically from what requires visual judgment.

## Replicate mode

- [ ] Target component, stylesheet/token source, and project instructions are named.
- [ ] The prototype uses real content names and a documented baseline.
- [ ] The structural change is visible at desktop and mobile widths.
- [ ] Existing color, typography, spacing, radius, and density values are preserved or marked as approximations.
- [ ] Hover, focus, selected, empty, and overflow states relevant to the request are represented.
- [ ] Local validation reports no missing assets or host-specific contracts.
- [ ] Screenshots were rendered when a supported browser was available.
- [ ] The implementation handoff maps DOM sections and measured CSS values back to components/tokens.

## Explore mode

- [ ] The absence of an existing UI baseline is explicit.
- [ ] Two or three directions differ in information architecture or content hierarchy, not only colors.
- [ ] All directions use the same content model so comparison is meaningful.
- [ ] Desktop and mobile composition are both considered.
- [ ] Typography, spacing, color, interaction, accessibility, and motion principles are stated.
- [ ] Any invented content, asset, or behavior is labeled as a decision or assumption.
- [ ] The recommendation explains what should be implemented first and what remains uncertain.

## Delivery rules

- A local path or loopback URL is always provided when an artifact exists.
- A missing browser makes screenshot verification `not run`, never an implied pass.
- A visual comparison is evidence for iteration, not proof of mathematical pixel equality.
- Production code changes begin only after the user selects a direction.

