# design.md — EdgeTwin AI Design System

Status: **v0.1 PROVISIONAL.** Written before the reference website is received. When you send it, I will extract principles (layout, type, spacing, navigation, hierarchy, colour philosophy), record them in `memory.md`, and revise this file. Nothing will be copied: no branding, layout, text, images, components, CSS, or code.

## 1. Brand personality
Industrial · precise · calm · trustworthy · human-made. Reads like an instrument panel or a maintenance log, not a marketing site. Information first, decoration never. Numbers are the hero.

## 2. Anti-patterns (explicitly banned)
Neon blue/cyan glows · purple-to-blue AI gradients · glassmorphism · glowing/blurred card shadows · robot/brain/sparkle illustrations · gradient text · oversized hero blocks in the app · emoji as UI icons · decorative animation. Motion only communicates change (value update, state transition).

## 3. Colour
Light theme is the default (readable in a bright lab/expo); a dark "control room" theme is a token swap, not a redesign. Neutrals are warm graphite/paper, not blue-grey.

**Neutrals**
| Token | Light | Dark | Use |
|---|---|---|---|
| `--bg` | `#F2F0EB` | `#16181A` | page |
| `--surface` | `#FAF9F6` | `#1E2124` | panels |
| `--surface-2` | `#E8E5DE` | `#262A2E` | table stripes, wells |
| `--line` | `#CFCBC1` | `#3A3F44` | 1px rules |
| `--ink` | `#1C1F22` | `#ECEAE4` | primary text |
| `--ink-2` | `#565B60` | `#A6A9AC` | secondary text |

**Semantic (state colours carry meaning only; never decorative)**
| State | Token | Light | Dark | Notes |
|---|---|---|---|---|
| Healthy / normal | `--ok` | `#2E7D5B` | `#5DB58C` | verdigris green |
| Warning | `--warn` | `#B7791F` | `#E0A73E` | amber |
| Critical | `--crit` | `#B3372A` | `#E5685A` | brick red |
| Maintenance required | `--maint` | `#54628A` | `#8C9AC4` | desaturated indigo-slate, distinct from red/amber |
| Offline / stale | `--off` | `#7B8086` | `#8B9096` | grey, hatched fill |
| Simulated data badge | `--sim` | `#6B4E9B` | `#A88FD6` | only for the SIMULATED tag |

Rules: state is **never colour-only** (always paired with label + icon shape: ● healthy, ▲ warning, ■ critical, ◆ maintenance, ○ offline). Contrast ≥ 4.5:1 for text, ≥ 3:1 for graphics. Chart series use a fixed 5-colour, colour-blind-safe set separate from state colours so a blue line is never mistaken for a state. **[ASSUMPTION]** exact hex values to be contrast-checked in T-050.

## 4. Typography
IBM Plex Sans (UI) + IBM Plex Mono (values, IDs, timestamps) — open-source, industrial, excellent numerals. Fallbacks: `system-ui`, `ui-monospace`. Tabular numerals on all metrics so digits do not jitter on update.
Scale (px): 12 caption · 13 table · 14 body · 16 emphasis · 20 section title · 28 page title · 40 key metric. Weight 400/500/600 only. Sentence case; UPPERCASE only for state labels at 11–12 px with letter-spacing 0.04em.

## 5. Spacing and grid
4-px base unit; steps 4, 8, 12, 16, 24, 32, 48. 12-column grid, 24 px gutters, content max-width 1440 px. Panels separated by 1 px rules and whitespace, not shadows. Corner radius 2–4 px (instrument look). Density is a setting: Comfortable / Compact (Compact is default for tables).

## 6. Layout
Persistent left rail (64 px collapsed / 220 px expanded) with: Dashboard, Machines, Live Monitoring, Digital Twin, Predictions, Alerts, Maintenance, Analytics, Model/MLOps, Settings. Top bar: site/fleet selector, global connection indicator (broker + data freshness), data-provenance badge, user/role. Every page: title row → key-status strip → primary panel → secondary panels.
**Dashboard:** fleet status strip (counts by state) → machine table/cards sorted by severity → open alerts → model/pipeline health footer.
**Machine detail:** header (ID, type, state chip, sync chip, last update) → left: live signal charts; right: twin panel (state, risk, health, top factors, recommendation).

## 7. Components
- **Buttons:** primary (ink fill), secondary (outline), destructive (crit outline → fill on confirm). Height 32/40 px. Focus ring 2 px `--ink` offset 2 px.
- **Cards/panels:** flat surface, 1 px line, 16 px padding, title in caption caps + optional unit/freshness on the right.
- **Status chip:** shape icon + label + colour; the only place state colours fill a shape.
- **Metric tile:** label, value (Plex Mono, 28–40), unit, delta vs 5 min, freshness dot; limit markers shown as ticks on a thin range bar.
- **Tables:** 36 px rows (compact 28), sticky header, right-aligned numerics, sortable, row click → detail, state chip column first.
- **Alerts:** severity rail on the left edge, message, machine, time, top factor, actions (Acknowledge, Feedback: Confirmed / False alarm). Persist until resolved; toasts only for new CRITICAL.
- **Forms:** labels above inputs, inline validation messages, units shown in the field, no placeholder-as-label.
- **Navigation:** left rail + breadcrumbs; state preserved in URL.

## 8. Data visualisation rules
1. Time-series: shared x-axis across a machine's charts; limit lines (warn/alarm) dashed in state colours; shaded band for healthy envelope; injected-fault window annotated.
2. Always label unit and window; y-axis never truncated silently; no dual axes; no 3D, no pie/donut for state (use stacked bar or count strip).
3. Missing data shown as **gaps** (never interpolated to zero); STALE/OFFLINE periods hatched.
4. Risk shown as probability with band labels and the model version; SHAP factors as a sorted horizontal bar with sign (↑ raises risk / ↓ lowers) and the caption "statistical association, not cause".
5. Max 5 series per chart; direct labels preferred over legends.
6. Live charts update at ≤ 1 Hz visually, keep ≤ 300 points on screen; pause-on-hover.

## 9. Digital Twin view
2-D SVG schematic of the machine type (motor/pump/compressor/CNC/conveyor variants share one component set) with live-bound values placed at the relevant part (temperature at housing, vibration at bearing, RPM at shaft). Colour of a part follows its L1 sensor condition. A side panel lists the twin state object (reported / derived / maintenance / sync). No 3D model required.

## 10. Responsive behaviour
≥ 1280: full layout. 768–1279: rail collapses, twin panel stacks under charts. < 768: single column, fleet as cards, charts simplified (read-only), actions kept reachable. Expo target: 1080p projector at 125% zoom must remain legible.

## 11. Accessibility
WCAG 2.2 AA target; full keyboard navigation; visible focus; ARIA live region for new CRITICAL alerts (polite for others); `prefers-reduced-motion` respected; state never colour-only; minimum target size 24 px; charts have a data-table alternative.

## 12. Content and labelling rules
Show unit + freshness on every value. Recommendation text is prefixed "System recommendation:". Simulated sources always carry the purple SIMULATED badge in the top bar and on the machine header. Error and empty states say what happened and what to do.
