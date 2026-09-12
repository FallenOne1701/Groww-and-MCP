---
name: Groww Weekly Pulse
colors:
  surface: '#f9f9ff'
  surface-dim: '#d7dae6'
  surface-bright: '#f9f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f1f3ff'
  surface-container: '#ebedfa'
  surface-container-high: '#e5e8f4'
  surface-container-highest: '#dfe2ef'
  on-surface: '#181c24'
  on-surface-variant: '#3c4a43'
  inverse-surface: '#2c303a'
  inverse-on-surface: '#eef0fd'
  outline: '#6c7a73'
  outline-variant: '#bbcac1'
  surface-tint: '#006c4f'
  primary: '#006c4f'
  on-primary: '#ffffff'
  primary-container: '#00b386'
  on-primary-container: '#003d2c'
  inverse-primary: '#50ddad'
  secondary: '#5d5e64'
  on-secondary: '#ffffff'
  secondary-container: '#dfdfe6'
  on-secondary-container: '#616269'
  tertiary: '#904d00'
  on-tertiary: '#ffffff'
  tertiary-container: '#ea841b'
  on-tertiary-container: '#542a00'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#71fac8'
  primary-fixed-dim: '#50ddad'
  on-primary-fixed: '#002116'
  on-primary-fixed-variant: '#00513b'
  secondary-fixed: '#e2e2e9'
  secondary-fixed-dim: '#c6c6cd'
  on-secondary-fixed: '#1a1b21'
  on-secondary-fixed-variant: '#45474d'
  tertiary-fixed: '#ffdcc3'
  tertiary-fixed-dim: '#ffb77d'
  on-tertiary-fixed: '#2f1500'
  on-tertiary-fixed-variant: '#6e3900'
  background: '#f9f9ff'
  on-background: '#181c24'
  surface-variant: '#dfe2ef'
typography:
  headline-xl:
    fontFamily: Inter
    fontSize: 30px
    fontWeight: '700'
    lineHeight: 38px
    letterSpacing: -0.025em
  headline-lg:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.015em
  headline-sm:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 14px
    letterSpacing: 0.04em
  code-num:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 18px
    letterSpacing: -0.01em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1rem
  margin: 1.5rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2rem
---

## Brand & Style
The design system powers an internal operational intelligence platform for leadership, product managers, and customer success teams. It translates massive volumes of user sentiment, app store reviews, support tickets, and performance metrics into a calm, authoritative executive brief. 

The aesthetic blends high-density corporate fintech precision with the clean, airy discipline of a printed periodical. It eliminates decorative noise—no gradients, no 3D elements, and no decorative imagery—relying entirely on sharp typography, hairline borders, and intentional emerald accents to direct focus. The emotional response is one of clarity, rigor, and immediate legibility under high-stakes operational reviews.

## Colors
The palette uses a deliberate dual-foundation structure: a deep obsidian sidebar anchor contrasted against a cool, sterile canvas and crisp white cards.

- **Primary Brand Mint (`#00B386`)**: Serves as the operational pulse. Used for primary CTAs, active tab underlines, positive metric deltas, and focal quote anchors.
- **Mint Tint Layers (`#E6F7F2`, `#D1F2E8`)**: Used for non-disruptive semantic chips, hover fills, and sentiment callout backgrounds.
- **Sidebar Obsidian (`#0B0D12`)**: A commanding, dark container that anchors navigation hierarchy away from analytical review areas.
- **Surface Foundations**: Global canvas uses `#F6F7F9` (cool gray wash) to create separation without heavy shadows, while `#FFFFFF` defines active analytical cards and top command headers.
- **Alert & Sentiment Hierarchy**:
  - Critical / 1–2 Star Drop: `#E05656` paired with `#FDE8E8` surface.
  - Caution / Latency Warning: `#D97706` paired with `#FEF3C7` surface.
  - Positive / 4–5 Star Pulse: `#00B386` paired with `#E6F7F2` surface.
- **Text & Borders**:
  - Primary Headers: `#1E222B`
  - Body & Analytics: `#44475B`
  - Muted Metadata & Sub-labels: `#7C7E8C`
  - Structural Boundaries: `#F0F0F2` 1px hairline rules throughout.

## Typography
Typographic rhythm mirrors high-standard financial reports: compact vertical spacing, negative letter-spacing on headlines, and tabular numbers across all quantitative columns. 

- Use `font-variant-numeric: tabular-nums` across all ratings, latency scores, and volume deltas.
- Section overlines and column headers must utilize `label-sm` in uppercase with subtle letter-spacing (`0.04em`) and `#7C7E8C` to establish an unambiguous reading order.
- Quotes, app review verbatims, and ticket snippets use `body-md` in `#1E222B` with left-accent borders to differentiate qualitative human feedback from machine metrics.

## Layout & Spacing
The layout implements a rigid 8px spatial grid with an anchored 240px dark navigation rail and a dynamic 12-column analytical canvas. 

- **Desktop (1280px+)**: Multi-column executive grid. Metrics overview sits in 4-column cards; detailed feedback threads and distribution tables span 8 and 4 columns respectively. Section margin is `1.5rem` (24px) with `1rem` (16px) gutters.
- **Tablet / Laptop (1024px–1279px)**: Sidebar condenses to an icon-and-label compact state (64px rail). Grid columns reflow to 6-column pairings.
- **Card Spacing**: Internal card padding strictly enforces `space-lg` (24px) for major KPI blocks and `space-md` (16px) for nested lists or table cells.

## Elevation & Depth
Depth is created through structural contrast rather than heavy multi-layer shadow stacks:

- **Flat Plain Cards**: Pure `#FFFFFF` resting on `#F6F7F9` background, bound by a crisp hairline border (`1px solid #F0F0F2`) and an ultra-diffused elevation shadow: `0 1px 3px 0 rgba(0, 0, 0, 0.04)`.
- **Top Command Bar**: Fixed pure `#FFFFFF` bar with a bottom hairline border (`1px solid #F0F0F2`) without shadow, maintaining baseline coplanarity with content.
- **Popovers, Tooltips & Dropdowns**: Elevated with `0 4px 12px 0 rgba(11, 13, 18, 0.08)` and bounded by `#F0F0F2`.
- **Interactive Focus States**: Zero outline offset; instead, a solid `0 0 0 2px #D1F2E8` halo paired with an inner border of `#00B386`.

## Shapes
Geometry is utilitarian and strictly controlled. Standard analytics cards and content wells use a 12px (`0.75rem`) border radius, striking a balance between modern product UI and rigorous data density. 

- **Cards & Data Panels**: 12px radius.
- **Interactive Controls (Buttons, Form Inputs, Segmented Controls)**: 8px (`rounded-md`).
- **Tags, Pills, PII Badges & Sentiment Chips**: Fully rounded pill shapes (`9999px`) to immediately distinguish small status metadata from square or rectangular actionable buttons.

## Components

### Buttons
- **Primary**: Solid `#00B386` background, `#FFFFFF` text, `font-weight: 600`, 8px border radius, 0 1px 2px rgba(0,0,0,0.05). Hover: `#009E76`. Active: `#008A67`.
- **Secondary**: `#FFFFFF` background, `1px solid #F0F0F2`, `#1E222B` text. Hover: `#F6F7F9` background and `#D1D3D8` border.
- **Ghost / Action**: Transparent background, `#44475B` text, 6px padding. Hover: `#E6F7F2` background, `#00B386` text.

### Status Chips & Badges
- **Anonymous PII-Scrubbed Tag**: Background `#F6F7F9`, border `1px solid #F0F0F2`, text `#7C7E8C`, `font-size: 11px`, monospaced user hash (e.g., `USR-8492-X`).
- **Positive Sentiment**: Background `#E6F7F2`, text `#00B386`, `font-weight: 600`.
- **Negative / 1-Star Alert**: Background `#FDE8E8`, text `#E05656`, `font-weight: 600`.
- **Warning / Investigation**: Background `#FEF3C7`, text `#D97706`, `font-weight: 600`.

### Cards & Pulse Review Units
- Surface: `#FFFFFF`. Border: `1px solid #F0F0F2`. Radius: 12px.
- Review / Ticket Verbatim Card: Incorporates a 3px vertical accent indicator on the inner left border: `#00B386` for praise/promoters, `#E05656` for detractor tickets.
- Header row inside cards includes title, timestamp (`#7C7E8C`), and the scrubbed PII chip pinned to the right.

### Input Fields & Selectors
- Background `#FFFFFF`, border `1px solid #F0F0F2`, text `#1E222B`.
- Height: 36px for dense dashboard filtering. Radius: 8px.
- Placeholder text: `#7C7E8C`.
- Focus state: Border `#00B386`, ring `2px solid #D1F2E8`.

### Checkboxes & Radio Controls
- Base: 16px square (checkbox) or circle (radio), border `1.5px solid #D1D3D8`, background `#FFFFFF`.
- Checked: Background `#00B386`, border `#00B386`, white checkmark or center pip.

### Lists & Data Rows
- Table rows: Height 48px, horizontal borders `1px solid #F0F0F2`, zero vertical borders. Hover state: `#F6F7F9`.
- Column header styling: `label-sm` uppercase, `#7C7E8C`, tracking `0.04em`.