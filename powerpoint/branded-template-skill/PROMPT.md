# Template-to-Skill Builder Prompt

Paste the text below into a new, local file-capable coding-agent session with an approved `.pptx` template and the original approved logo file attached or available in the workspace.

```text
Turn the PowerPoint template I provide into one complete, portable presentation skill that can create new editable presentations in the same branded visual system. Use the host agent's native reusable-skill format when one exists; otherwise create the equivalent portable skill folder and instructions for that host.

The finished product is the brand-specific skill folder, not merely an audit, report, rewritten template, or one-time deck. Perform the detailed slide audits internally and save them as skill references. Do not require me to paste a separate audit prompt for every slide.

The goal is a reliable first draft: preserve approved source-slide patterns, replace only documented content slots, render and verify every output, and leave final story judgment and visual approval with the user.

## Required Capabilities

Before doing substantive work, confirm that this session can:

- read the supplied PowerPoint file and its package/OOXML;
- inspect slide, master, layout, theme, relationship, font, and media information;
- render every slide;
- create persistent files in a writable workspace;
- copy the source template and extract embedded assets;
- create a complete skill folder and run the available skill validator; and
- create and inspect an editable PowerPoint test deck.

If any required capability is unavailable, stop and state exactly what is unavailable. Do not simulate inspection, estimate geometry, or claim that a skill was created.

## Source and Privacy Contract

- Treat the supplied presentation as read-only evidence. Work from a copy and never overwrite it.
- Record the source filename and SHA-256 checksum before inspection. Confirm the source checksum again at the end.
- Keep all work private unless the user explicitly authorizes sharing.
- Never execute macros or VBA.
- Do not include confidential notes, comments, customer data, personal data, machine-specific paths, or unrelated sample content in the finished skill.
- Bundle the complete source template only when the user has explicitly authorized that strategy. Otherwise require an approved sanitized or selected-slide template copy.
- **Canonical logo is a required user input.** Ask the user to provide the original approved logo file before building the skill. Prefer the original vector artwork; otherwise use the highest-resolution approved PNG. If the user has not supplied it, stop and ask for it. Do not extract an embedded, downloaded, screen-captured, or internet-found logo as a substitute for the canonical asset.
- Treat the separately supplied logo as the authoritative reusable asset. Compare it with any logo visible in the PowerPoint only to confirm visual identity and placement treatment; record checksums and any difference as evidence.
- Do not recreate, redraw, recolor, downsample, or approximate the canonical logo or another authoritative brand asset.
- Do not package font files without explicit redistribution permission. Record required fonts and any user-approved fallbacks.

## Evidence Contract

Use these labels consistently:

- Exact PowerPoint property — directly inspected native PowerPoint or stored OOXML/package value.
- Effective inherited property — resolved from a theme, master, or layout.
- Visual observation — visible conclusion that is not stored as one directly inspected property.
- Uncertain — unavailable, ambiguous, or conflicting. Never estimate.

Treat the saved PowerPoint package as the source of truth for stored properties. Rendered slides are visual evidence, not exact geometry evidence.

- Preserve raw OOXML geometry in EMU when available.
- Convert EMU using exactly 12,700 EMU per point.
- Convert OOXML text `sz` values from hundredths of a point.
- Use exactly 72 points per inch.
- Do not convert screenshot pixels, rendered pixels, CSS values, or visual estimates into PowerPoint points.
- Identify the coordinate origin as the slide's top-left corner.

## Phase 1 — Inventory the Entire Deck

Inspect every source slide. Create a durable inventory containing:

- exact slide count, order, native slide size, orientation, hidden state, section, transition, and timing when available;
- one rendered reference image per slide and a contact sheet;
- functional slide-type label for every slide;
- master, layout, background, and inherited visible elements;
- render-visible and full stored slide-local object counts;
- fonts, themes, embedded and linked assets, charts, tables, SmartArt, groups, media, notes, comments, macros, and other portability risks;
- likely duplicate layouts and materially different variants; and
- a recommended set of reusable slide types.

Deep-audit every materially distinct reusable layout. Slides may share one slide-type specification only when their object structure, geometry, styling, master/layout relationship, and intended content-slot pattern genuinely match. Treat meaningful variants as separate slide types.

Recommend no more than six supported layouts by default. If the deck contains six or fewer distinct reusable layouts and the user has authorized the supplied template for bundling, proceed with all distinct layouts unless the user instructed otherwise. If more than six are needed, stop once and ask the user to approve the supported set.

Propose a short lowercase skill name using only letters, numbers, and hyphens. Use it when the name is unambiguous; ask only if there is a material naming conflict.

## Phase 2 — Deep-Audit Each Selected Slide Type

Process one representative source slide at a time. Save one durable reference file per supported type before moving to the next. Do not attempt to hold every slide's detailed audit in one chat response.

For every supported slide type, record:

### Identity and Usage

- stable slide-type ID, source slide number, functional name, master, layout, background, and reference-render path;
- when to use the layout, when not to use it, and the narrative jobs it supports;
- whether the runtime skill must duplicate the source slide, preserve it without edits, or use it only as evidence.

### Complete Structure

- exact render-visible object count and one inventory row per visible slide-local object in back-to-front order;
- full stored structural inventory, including hidden, nonrendering, fully occluded, and group-container objects;
- separate inherited master/layout contributions; and
- a completeness check proving that each inventory count matches its rows and records.

For every stored object, capture all directly inspectable reconstruction properties that apply, including:

- stable object ID, PowerPoint name/ID, type, placeholder type, visibility, editability, group relationship, and z-order;
- left, top, width, height, rotation, flip, aspect lock, anchor, alignment, distribution, spacing, overlap, and group transforms;
- fill, outline, color, theme source, tint/shade, transparency, gradients, patterns, line weight/style, shadow, glow, reflection, bevel, 3-D properties, and other effects;
- font family and provenance, size, weight, emphasis, color, alignment, direction, columns, wrapping, autofit, overflow, margins, indentation, bullets, tabs, and paragraph/line spacing;
- image identity, native dimensions, crop, mask, aspect lock, scaling, transparency, corrections, recolor, compression, and effects;
- shape geometry, adjustment values, connector endpoints, line caps/joins, and dash patterns;
- table, chart, SmartArt, equation, animation, transition, and media properties when present; and
- every unavailable or conflicting value as Uncertain rather than guessed.

### Content Semantics

Classify every text, picture, chart, table, or other editable object as exactly one of:

- fixed brand element — preserve exactly;
- replaceable content slot — replace content while preserving documented structure and styling;
- conditional element — keep, remove, or vary only under a stated rule;
- source sample content — replace; its particular wording is not a brand rule; or
- unresolved — requires user confirmation before the skill is finalized.

Treat dates, page numbers, section numbers, document titles, confidentiality labels, presenter names, version labels, and similar metadata as content semantics rather than fixed brand wording. Preserve their typography, geometry, and formatting as brand rules, but classify their values as replaceable or conditional unless the source or user proves that the wording must never change. When the source uses manually typed page numbers, the runtime skill must update them to the output deck's actual order or intentionally remove them under an approved rule; it must not preserve the source slide's old number merely because the number is stored in a branded text box.

Capture exact source wording only as private audit evidence when needed to identify an object, prove formatting, preserve line/paragraph structure, or evaluate content capacity. In the runtime slide-type reference, retain fixed brand wording, but replace ordinary sample wording with semantic slot names, examples of allowed content shape, and capacity guidance.

For each replaceable slot, record:

- stable target object ID;
- semantic role;
- allowed content type;
- practical line, character, item, row, or column capacity supported by the source;
- formatting and geometry that must remain fixed;
- what to do when content does not fit; and
- whether the object may be deleted, duplicated, or replaced.

If content does not fit at runtime, shorten it, select another supported layout, or split the content across another slide. Do not silently shrink typography, move protected objects, or overlay a new layout on top of the template.

## Phase 3 — Extract the Cross-Slide Design System and Assets

Create a design-system reference containing only repeated, source-supported rules:

- slide size and orientation;
- master/layout hierarchy;
- used colors, theme references, tints, shades, and transparency;
- used fonts and typography hierarchy;
- recurring backgrounds, logos, headers, footers, page markers, section labels, decorative elements, and protected zones;
- recurring grids, margins, alignment anchors, spacing rhythm, and layering rules;
- supported slide types and selection guidance;
- content-density and capacity guidance; and
- remaining uncertainties.

Do not promote a one-time content decision into a global brand rule.

Store the user-supplied canonical logo as the skill's reusable logo asset. Preserve its original format when practical, retain vector artwork as vector artwork, record its checksum, and never replace it with a lower-resolution image extracted from the PowerPoint. Use the PowerPoint only to document the logo's approved frame, position, size, crop/mask behavior, aspect lock, layering, and prohibited transformations. Extract and deduplicate other reusable assets with checksums. Record all asset paths relative to the finished skill.

## Phase 4 — Build the Portable Skill

Create a new skill folder with this minimum structure:

<skill-name>/
├── SKILL.md
├── agents/
│   └── openai.yaml when supported
├── references/
│   ├── design-system.md
│   ├── slide-catalog.md
│   ├── assets.md
│   ├── workflow.md
│   ├── validation-contract.md
│   └── slide-types/
│       └── one file per supported type
├── manifests/
│   ├── source-deck.json
│   └── one machine-readable object manifest per supported type
├── assets/
│   ├── source-template.pptx or the approved sanitized template
│   └── canonical reusable assets
├── scripts/
│   └── deterministic validators that materially improve reliability
└── examples/
    └── reference-renders/
        └── one render per supported type

Keep SKILL.md lean. It must explain:

- when the skill applies;
- required user inputs;
- supported slide types and how to select them;
- the source-slide duplication strategy;
- how to replace documented content slots by stable object ID;
- what must never change;
- how to handle overflow or unsupported layouts;
- required render, structural, editability, and PowerPoint checks; and
- the relevant reference files to read for the current request.

Put detailed geometry and object records in the slide-type references and manifests, not in SKILL.md.

The runtime skill must use this sequence:

1. Understand the audience, purpose, source material, and desired outcome.
2. Develop or confirm the narrative and slide-level plan.
3. Map each output slide to one supported source-slide type.
4. Duplicate the approved source slide using a relationship-preserving method.
5. Replace only documented content slots by stable object ID.
6. Preserve masters, layouts, themes, relationships, fonts, crops, grouping, animations, notes, and protected brand elements.
7. Render and inspect every output slide.
8. Run deterministic structural and brand-invariant checks.
9. Open or otherwise validate the final result in PowerPoint when that capability is available.
10. Report remaining limitations honestly.

Do not rebuild a supported slide from prose, palette values, coordinates, screenshots, or visual resemblance when the approved source slide can be duplicated safely.

## Phase 5 — Deterministic Validation

Create validation scripts only for checks that can be performed reliably. At minimum, validate:

- required skill files and references;
- source checksum and source-template preservation;
- slide size;
- supported source-slide identities;
- required fixed-object IDs, types, counts, geometry, styling, and asset relationships;
- allowed editable-slot IDs;
- missing fonts or assets;
- unexpected new or deleted protected objects;
- unresolved or empty structural placeholders;
- text overflow, clipping, and collisions when tooling supports those checks; and
- object counts under the documented convention.

When comparing a generated slide with its reference, ignore or mask the intentionally changed content inside documented replaceable slots. Compare protected regions and fixed objects directly.

Run the official skill validator. A passing structural validator proves package structure only; it does not prove that the skill makes good slide decisions.

## Phase 6 — Build-Time Proof

Before declaring the skill complete:

1. Reproduce one supported source slide using its original content or by duplicating it unchanged and confirm the golden baseline.
2. Create at least one slot-substitution example using fictional replacement content.
3. Test at least one longer-content case.
4. Test one unsupported-layout request and confirm that the skill declines, asks for a supported alternative, or requires a new approved slide type rather than inventing a layout.
5. Create one reordered or repeated-layout test in which the output order differs from the source deck. Confirm that dynamic page numbers, section markers, dates, and other metadata reflect the output deck rather than the representative source slide.
6. Render and inspect every test slide.
7. Confirm fixed brand objects remain unchanged.
8. Confirm changed content appears only in documented editable or conditional slots.
9. Confirm the PPTX remains editable.
10. Record every pass, failure, limitation, and pending PowerPoint-only check in a build report.

Do not claim perfect replication, complete corporate-template coverage, or final brand approval. State exactly which slide types passed and which checks remain pending.

## Required Final Output

Return:

- the complete portable skill folder;
- the build report and evidence ledger;
- the source checksum verification;
- the list of supported slide types;
- the skill-validator result;
- the paths to all reference renders and test decks;
- every unresolved property or decision; and
- concise instructions for installing and using the skill in a fresh local-agent session.

Do not stop after producing an audit. Do not claim completion unless the complete skill exists on disk and the build-time proof has been performed.
```
