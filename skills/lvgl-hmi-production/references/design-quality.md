# Human-centered visual design for embedded HMI

Use when creating, refining or reviewing an HMI design, including before writing a Stitch prompt. Adapted from the user's UI/UX Design Agent reference package; the guidance is a set of decision heuristics, not a guarantee of design quality or a claim of standards compliance.

## Choose the right scope

- A localized fix: inspect the actual component, retain the existing visual system and correct only the problem. Do not require a new brief or options.
- A screen or flow: understand its main task, related states and adjacent screens before proposing changes.
- A new design or authorized redesign: investigate the user and context, propose meaningfully different options when requested or when the direction is open, and honor the user's chosen review checkpoints.
- A review: identify evidence, impact and proposed correction; don't make product changes merely because a review was requested.

Use existing design tokens and brand decisions before adding new ones. Ask the user for missing information that materially affects a design or behavior; do not manufacture device capabilities or product requirements.

## From user task to visual direction

Identify what a person needs to perceive or do first, their viewing distance, lighting, reading needs and physical input. Rank real information and actions before decoration. Build hierarchy through layout, size, weight, contrast and spacing; don't make all content equally prominent. Group labels with their values, distinguish unrelated groups, and maintain stable locations for frequently read or safety-relevant information. A single clear screen may be better than multiple boxes; use cards, borders, effects and animation only when they have a purpose.

Translate subjective descriptors into observable design decisions suited to the product. For example, “calm” may mean restrained contrast hierarchy and limited movement, not necessarily a pastel palette. Describe important trade-offs and keep selected brand/direction. Use meaningful structural differences for alternatives, not only different colors. For the selected direction choose a small set of role-based color, type and spacing tokens; avoid forcing a complete design system for a minor task.

## Fit and legibility on the actual device

Use the user's specified pixel resolution, orientation, physical display size, view distance and input. Map visual hierarchy and content into that viewport; a large Stitch canvas or a 1:1 pixel view on another monitor is not proof of physical readability. Check actual target-size views where available, then validate on hardware. Plan long labels, locale, font glyphs and fallback, units, negative/large values, unavailable data and limited memory. Choose practical type sizes and touch areas for the actual hardware and test them; do not treat web CSS pixel or WCAG web thresholds as automatic native-display requirements.

Inspect foreground/background color pairs in their actual context, including disabled and dim states. Color alone must not be the only cue for meaningful status. Do not say a contrast check or screenshot proves overall accessibility; identify what was measured and what remains untested. For applicable web simulation accessibility guidance, consult the relevant WCAG success criteria and exceptions, and distinguish CSS pixels from device pixels.

## Behavior and motion

Specify only relevant states and transitions: what the user requests, what is pending, what the device has confirmed, failure and recovery. Preserve information when appropriate; do not create successful outcomes or comfort thresholds without a source. Motion must explain feedback or a state transition, remain interruptible where appropriate, and have a reduced-motion alternative when appropriate. Test rapid repeated input and the final state. Choose timing according to user-approved behavior and device feasibility; web-only blur, transitions or CSS timing do not establish an LVGL equivalent or real hardware performance.

## Comparing Stitch with an LVGL render

Before treating a translation as review-ready, compare the actual LVGL preview with the approved design at the target viewport. Note font family, weight, baseline, group relationships, spacing, alignment, colors, overflow and any omitted decoration. Ask for the user's LVGL preview when direct access is unavailable; do not treat syntactically valid XML or font-width estimates as a verified render. Preserve the prior screen while making a focused revision. When a web font is substituted, state the substitute and confirm its license; measure or inspect representative long values and glyphs, then verify them in the actual renderer. Any unsupported effects and actual hardware legibility remain explicit open items.

## Stitch handoff

For the current requested phase only, create a bounded prompt containing: screen purpose and user question; exact physical resolution/orientation and safe regions; primary and secondary content in hierarchy; user actions and state contract; approved art direction and token roles; typography and legibility requirements; target-platform limitations; and acceptance checks (no clipping or overlap, no unsupported claims). Ask for meaningful visual options only when the direction is open or the user requests them. Retain screen IDs and user-selected direction. Review and refine one requested phase, show the user the actual result, then wait for feedback as required by SKILL.md. Don't invent assets, data, labels, interactions or measurements.

## Review as a designer and an engineer

For each material finding, explain: observed location and evidence → likely user impact → possible cause → smallest targeted correction → how to verify it. Distinguish observed, inferred and not tested; don't invent issues to fill a quota. Fix task-blocking or misleading behavior and readability before decorative polish; preserve approved work. Validate actual target-sized render and interaction when accessible, and explicitly mark missing evidence. A polished concept, a valid XML file or one screenshot is not proof of hardware usability or production readiness.

References: W3C WCAG 2.2 https://www.w3.org/TR/WCAG22/ and target-size scope https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html ; LVGL docs https://docs.lvgl.io/ . Consult version- and platform-specific primary sources before making a standards or capability claim.
