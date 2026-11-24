# Workflow and feasibility

Use for planning or executing a design-to-firmware project. Scale depth to risk, product constraints and requested scope.

## Feasibility contract

For each meaningful stage record: task, available / conditional / blocked / not tested, easy / medium / hard if executable, prerequisites, evidence, dependency, concrete next action. Availability means demonstrably available in this environment, not merely documented. A blocked task has no difficulty rating until its prerequisite exists. Explain the reason for the difficulty; reclassify on new evidence. Examples (not fixed promises):

| Stage | Typical difficulty if prerequisites exist | Evidence / limits |
|---|---|---|
| Inspect repository, tool versions and design brief | Easy | Commands and source files; dirty or missing checkout can complicate |
| Minimal LVGL sample and simulator | Medium | Version-matched target and display backend; build + actual render, not only compile |
| Stitch screen generation and UX review | Medium | Authorized tool access, brief and actual target-sized visual inspection; generation may fail or not match size |
| Design to schema-valid LVGL XML / C export | Hard | Exact editor/schema, verified export capability and license, assets, real tool logs; conversion is not automatic or pixel-perfect |
| State integration and error handling | Medium to hard | Event contracts, supported APIs, tests and ownership |
| Hardware timing, memory and stability | Hard | Actual board/probe/display, repeatable measurements and project budgets |
| Product release | Hard / conditional | Relevant target, requirements, test results and responsible owner's decision; no blanket compliance claim |

## Foundation baseline

1. Inspect existing application, topology, host/target, board display and input backend, available simulator and pinned SDK. Use a version-matched official sample where suitable; document assumptions. Do not overwrite existing application.
2. Build, run and inspect actual output and interaction when display access exists. Build-only is not a visual or runtime pass. If target is unavailable, report NOT TESTED.
3. Add a minimal state demo only when requested: button intent → pending → success/failure; mock response must be identifiable as mock. Keep it usable as a test of shared model and presentation.

## AI design to implementation

### Phase 1 — Human and device brief

For visual hierarchy, layout, typography, color, Stitch handoff and evidence-based critique, read [design-quality.md](design-quality.md).

Identify the intended user, environment, viewing distance, physical screen shape/resolution/orientation, touch/input, goals and relevant device states. Treat the user-provided dimensions as mandatory target artboard bounds; verify actual output dimensions or source, and distinguish pixel size from physical size on another monitor. Define hierarchy, readable text, safe layout areas, typography, accessibility targets, asset/license and embedded resource constraints. Record unknowns. Do not invent product features or assume the same board as a previous project.

**Missing information:** Ask the user whenever an unspecified product requirement or device behavior would materially change the design or simulation. Do not invent a timeout, state transition, display specification or sensor behavior. Do not proceed with the dependent design until answered, unless the user has explicitly delegated the decision. Continue only independent work within the current requested phase.

### Phase 2 — Alternatives and selection

Prepare 2–3 distinctly different visual directions for the same representative screen, using actual inspectable design artifacts, not only descriptions. Generate bounded prompts/operations separately enough to inspect, compare and refine each result. Show each option with strengths, constraints and key trade-offs; ask the user to select. Preserve all options and their IDs. User input is mandatory before proceeding with a selected direction unless the user explicitly provides a direction or asks for only one. Do not interpret silence as selection.

### Phase 3 — Complete the selected design

Refine only the screen or bounded step the user requested. Show the actual result and stop: wait for the user to review and provide their observations. Apply focused changes based on that feedback, and stop for review again. Do not autonomously generate remaining screens, run unrelated validation, export, or enter implementation merely because a direction was selected. Advance only on explicit user instruction. The user may choose to export HTML themselves; wait for their exported artifact or the next instruction. Use minimal tool calls and avoid unnecessary token expenditure. Review each requested image from a human user's perspective at target resolution and display shape: visual hierarchy, legibility, spacing, grouping, alignment, contrast, touch targets, no overlap/clipping, text wrapping and long translations, and distinguishable actionable and inactive elements. When the user requests each state, check the relevant boot, home, error/unavailable, recovery, idle and wake behavior; do not create them all automatically in one turn. Use real screenshots and state contracts. Keep design source, decisions, design-system references and review results. If target-specific screenshots are not available, mark that validation NOT TESTED. Make focused corrections and re-review. Obtain explicit user approval of the complete design before implementation; preserve all variants.

### Simulation checkpoint — on user request

After the user reviews the relevant design and explicitly requests the simulation phase, use the current Stitch session when available to create a bounded interactive prototype. Set the embedded device viewport to the requested resolution and orientation, adapting content to fit rather than assuming the outer canvas is the display. Define each allowed transition, trigger, timeout, reset and recovery before building; the simulator controls are separate from the device UI. Preserve the user-selected design, mock sensor values and real-vs-simulated labels. For an idle-dimming request, model the actual timeout and timer reset on activity, and allow touch to wake; do not make a normal tap arbitrarily dim or falsely recover a sensor error. An accelerated demo timer may be optional only if clearly labelled; do not substitute it for the specified behavior. Specify how time, unavailable data and transitions behave when unknown.

When a simulation is requested, consider a compact test-only panel distinct from the device UI: current state, elapsed inactivity, last triggering event and a short event timeline. Offer explicit test controls for sensor failure/recovery and, when the user agrees, clearly labeled time advancement to check just before and at the idle threshold. Preserve real timing in normal mode. An active touch resets idle and remains active; a dimmed touch wakes and resets idle; a sensor error remains until an explicit simulated recovery. Tailor these defaults to the actual agreed requirements rather than inventing extra features.

Include animation in the interactive simulation to demonstrate the requested transitions (for example boot to home and dim to wake), plus restrained feedback where meaningful. Specify and show the trigger, duration/easing if agreed, final state, and behavior during repeated inputs; ask the user when required motion details are missing. Provide a way to replay or step through transitions when feasible. Review legibility, reduced-motion needs, perceived responsiveness and realistic LVGL/device cost; avoid assuming web CSS blur or effects will be available on hardware. Animated brightness is only a visual mock unless actual backlight control is tested. Do not replace the requested idle timeout with an unlabeled accelerated demo.

Make the Stitch prompt explicitly request a functioning animated prototype with replay controls, not just static state screenshots or a description of motion. If alternatives are appropriate, let the user compare and choose before implementation. On authorized motion handoff, inspect the actual prototype's CSS and execution code or the user's export: record each animated target, trigger, start/end values, duration, delay, easing, order and final state. Note defaults versus user-adjusted values and differences between written descriptions and actual code. Recreate supported motion in LVGL XML or application code according to the version-matched toolchain; preview and obtain review before exporting or flashing when that is the agreed phase boundary. Record approximations, and validate on target hardware separately. Do not claim web code automatically becomes LVGL or infer device performance from a web preview.

Audit AI-generated copy and behavior against the actual brief: remove invented hardware models, sensor claims, thresholds and unsupported status messages; label mocks clearly. Keep a short list of outstanding issues when the user accepts a design direction. Acceptance of a direction is not proof that those issues are fixed, that the simulation ran successfully, or that implementation and hardware are approved. Do not silently remove or resolve an issue without evidence.

Inspect actual source or run the prototype if accessible; compare each behavior with the contract and report PASS / FAIL / NOT TESTED. Seek user review and stop at the current phase. Do not download or export files if the user prefers to export them. A web preview demonstrates interaction only, not actual hardware power consumption, sensor data, timing precision or LVGL rendering.

### Phase 4 — Architecture and implementation

After design approval, create a small project-defined IR if helpful: stable IDs, layout, tokens, assets, strings, event and state contracts, navigation and deviations. It is not an LVGL standard. Check actual LVGL version, editor/CLI, version-matched XML schema, export support, platform and entitlement. If absent, stop the dependent XML steps and report the blocker, while progressing independent work; never fabricate XML syntax or tool output. An alternative C implementation needs agreement and is not an XML pipeline pass.

Generate a limited screen, validate, capture an actual LVGL render and compare to the approved design; use focused repairs and rerun real checks. Isolate generated code and record the tool version and reproduction command. Integrate the model/controller, presentation, services and platform adapters; follow pinned LVGL threading and lifecycle rules, validate inputs, distinguish pending from confirmed state and keep safety outside the HMI alone. Then test simulator and target hardware against the agreed gates.

### AI translation from Stitch HTML to LVGL XML

Use only after the relevant design is approved and the user requests this phase. HTML is a reference, not input guaranteed to convert automatically. Work on the requested screen or bounded motion first; preserve existing XML, assets and user edits.

1. **Inspect the real reference.** Identify the target display viewport inside the larger Stitch canvas, the approved screen and relevant state, then extract visible strings, coordinates and grouping, sizes, spacing, colors, borders, radii, font family/weight/size, icons/assets and motion. Inspect computed styles or run the reference when possible: CSS frameworks, external fonts, JavaScript and dynamic state can make raw HTML misleading. Record unknown or missing assets and external dependencies rather than inventing them.
2. **Make a conversion map before changing XML.** Map each visible element and motion to a supported LVGL object, style, font/asset or timeline. Identify browser-only effects, font and glyph licensing/availability, and necessary substitutes; flag any visual or behavior differences for review. Use existing project styles and assets, inspect version-matched schemas and examples, and preserve hierarchy and layout at the target resolution rather than generating a generic approximation. Make a small mapping in the response or project notes when helpful; do not force a new artifact for a minor edit.
3. **Ask AI for bounded, schema-grounded XML.** Supply the approved reference and extracted map, project/version, fixed resolution, existing tokens/assets and exact screen scope. Require supported syntax, target names and animation timing; request no fabricated bindings, states or hardware behavior, and a list of unsupported effects or assumptions. AI output is a draft: inspect its diff and preserve the existing screen rather than overwriting unrelated work. Do not claim XML is valid merely because it is well-formed.
4. **Validate and visually compare.** Use the available version-matched LVGL Pro validator/editor and inspect its errors; if unavailable, state NOT TESTED. Open the actual rendered XML at target resolution, compare it with the approved Stitch screen for fonts, baseline, hierarchy, geometry, spacing, colors, clipping, assets and representative values, and request a screenshot from the user if direct preview is unavailable. Iterate on concrete differences and obtain user review at the agreed checkpoint; code generation is not visual validation.
5. **Check animation playback separately.** A timeline declaration does not start itself or switch screens. Preview each timeline and its end state, including initial visibility during delays, then check triggers and lifecycle. A boot-to-home sequence, screen transition, wake logic or backlight behavior may require separate application code; identify precisely what is present and what is not. Treat easing substitutions and timing differences as approximations until reviewed.
6. **Export and integrate only when directed.** The user may choose to generate C in LVGL Pro. Inspect actual generated APIs and changed files, update the Zephyr snapshot deliberately including file lists and assets, and keep handwritten logic separate from generated files. Build and test the requested simulator or hardware phase; verify screen output and motion on device separately from successful build/flash. Do not assume a CLI, license, generated API, or test result exists without evidence.

## Gates

For each criterion define target, acceptance threshold, method, input/version and evidence before claiming PASS. Typical relevant criteria: UI geometry/no clipping for inspected states and languages; navigability and touch; state transition and failure recovery; clean build; actual simulator execution; repeated actions, screen lifetime and resource behavior; target display/input and hardware fault handling; measured RAM/flash, latency, frame time, boot and endurance against agreed budgets. Distinguish observed / inferred / not tested and simulator / hardware. A missing criterion or absent tool is NOT TESTED, not pass. Record relevant issues and scope of test, and do not assert production readiness without all agreed gates and responsible sign-off.

## Sources and version cautions

Use version-matched official LVGL and Zephyr docs. LVGL's XML engine left open core at v9.5 and runtime XML can have different licensing; verify current terms, editor/CLI access and export. References: https://lvgl.io/blog/announcement-lv_xml-removal-from-v9-5 and https://lvgl.io/docs/pro/integration/using-exported-c-code . Don't assert runtime XML is needed for C export. Evaluate version/feature support and licenses each time.
