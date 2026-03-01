# Sentinel Design System & Style Guide

> For: AI coding agent implementation
> Project: Sentinel -- AI-Powered Prediction Market Surveillance Dashboard
> Stack: React + Tailwind CSS (or Next.js)
> Aesthetic: Dark cyber-surveillance terminal meets modern data visualization

---

## 1. Design Philosophy

Sentinel is a surveillance intelligence tool. The design must feel like you are sitting inside a SCIF (Sensitive Compartmented Information Facility) looking at a classified monitoring terminal. Think Bloomberg Terminal meets a cybersecurity SOC (Security Operations Center), wrapped in the visual language of the Framer "Cipher" template: deep blacks, electric accent colors, ASCII-art texture layers, and interactive particle grids that make the interface feel alive and watching.

Three design pillars:

1. **Ambient Intelligence** -- The UI should feel like it's always scanning, always processing. Subtle background animations (ASCII flow trails, pulsing dot grids) communicate that the system is alive without demanding attention.
2. **Information Density with Clarity** -- This is a data dashboard. Prioritize legibility and scanability. Dense information presented through clean hierarchy, not decoration.
3. **Controlled Tension** -- Use color and motion sparingly to create urgency only where it matters. A red alert should feel alarming BECAUSE the rest of the interface is calm.

---

## 2. Color System

### Base Palette

```css
:root {
  /* Backgrounds -- deep, layered blacks */
  --bg-primary:      #050508;    /* Near-black, main canvas */
  --bg-secondary:    #0A0A0F;    /* Card/panel backgrounds */
  --bg-tertiary:     #0F0F18;    /* Elevated surfaces, modals */
  --bg-hover:        #141420;    /* Hover states on cards */
  --bg-active:       #1A1A2E;    /* Active/selected states */

  /* Borders & Dividers */
  --border-subtle:   #1A1A2E;    /* Default borders, almost invisible */
  --border-default:  #2A2A3E;    /* Visible borders */
  --border-strong:   #3A3A4E;    /* Emphasized borders */

  /* Text */
  --text-primary:    #E8E8F0;    /* Primary content, high contrast */
  --text-secondary:  #8888A0;    /* Labels, supporting text */
  --text-tertiary:   #55556A;    /* Disabled, placeholder */
  --text-inverse:    #050508;    /* Text on bright backgrounds */

  /* Accent: Electric Cyan -- the "Sentinel eye" */
  --accent-primary:  #00F0FF;    /* Primary actions, key data */
  --accent-muted:    #00F0FF33;  /* Accent at 20% opacity for glows */
  --accent-bg:       #00F0FF0A;  /* Accent at 4% for tinted surfaces */

  /* Semantic: Threat Classification */
  --threat-critical: #FF2D55;    /* INSIDER classification, critical alerts */
  --threat-high:     #FF6B2D;    /* OSINT_EDGE, high severity */
  --threat-medium:   #FFB800;    /* FAST_REACTOR, medium severity */
  --threat-low:      #34D399;    /* SPECULATOR, low/normal */
  --threat-info:     #6366F1;    /* Informational, system messages */

  /* Semantic: Status */
  --status-online:   #00FF88;    /* System healthy, connected */
  --status-warning:  #FFB800;    /* Degraded, attention needed */
  --status-error:    #FF2D55;    /* Down, failed */
  --status-offline:  #55556A;    /* Disconnected, inactive */

  /* Chart Colors (ordered for data viz) */
  --chart-1:         #00F0FF;
  --chart-2:         #6366F1;
  --chart-3:         #FF6B2D;
  --chart-4:         #34D399;
  --chart-5:         #FFB800;
  --chart-6:         #FF2D55;
}
```

### Glow Effects

Glows are used sparingly to draw attention. They should feel like light bleeding from data, not decorative neon.

```css
/* Accent glow -- for key metrics and active elements */
.glow-accent {
  box-shadow: 0 0 20px var(--accent-muted), 0 0 60px var(--accent-muted);
}

/* Threat-level glows -- for alert badges and critical cards */
.glow-critical {
  box-shadow: 0 0 12px #FF2D5533, 0 0 40px #FF2D5518;
}

.glow-high {
  box-shadow: 0 0 12px #FF6B2D33, 0 0 40px #FF6B2D18;
}

/* Subtle inner glow on cards to suggest depth */
.glow-inner {
  box-shadow: inset 0 1px 0 0 rgba(255,255,255,0.03);
}
```

### Gradient Treatments

```css
/* Hero/header gradient -- subtle, atmospheric */
.gradient-sentinel {
  background: linear-gradient(
    135deg,
    #050508 0%,
    #0A0A1A 40%,
    #0A1020 60%,
    #050508 100%
  );
}

/* Card shimmer on hover */
.gradient-card-hover {
  background: linear-gradient(
    135deg,
    rgba(0, 240, 255, 0.02) 0%,
    transparent 50%,
    rgba(99, 102, 241, 0.02) 100%
  );
}

/* Threat level gradient bar */
.gradient-threat-bar {
  background: linear-gradient(90deg, #34D399, #FFB800, #FF6B2D, #FF2D55);
}
```

---

## 3. Typography

### Font Stack

```css
/* Primary: JetBrains Mono -- monospace for that terminal/surveillance feel */
/* This is the IDENTITY font. All data, numbers, labels use this. */
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&display=swap');

/* Display: Space Grotesk -- geometric sans for headings */
/* Clean, technical, pairs well with monospace body */
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap');

:root {
  --font-mono:     'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;
  --font-display:  'Space Grotesk', 'Inter', sans-serif;
}
```

**IMPORTANT NOTE FOR IMPLEMENTER**: Space Grotesk is used deliberately here despite being common in AI aesthetics because it genuinely pairs well with JetBrains Mono and suits a surveillance terminal. If the implementer wants to differentiate further, substitute with **Outfit**, **Syne**, or **Instrument Sans** for display. The monospace font is non-negotiable -- it IS the brand.

### Type Scale

| Token             | Font           | Size   | Weight | Line Height | Letter Spacing | Usage                          |
|-------------------|----------------|--------|--------|-------------|----------------|--------------------------------|
| `display-lg`      | Space Grotesk  | 48px   | 700    | 1.1         | -0.02em        | Hero numbers, page titles      |
| `display-md`      | Space Grotesk  | 36px   | 700    | 1.15        | -0.02em        | Section headers                |
| `display-sm`      | Space Grotesk  | 24px   | 600    | 1.2         | -0.01em        | Card titles, panel headers     |
| `heading`         | Space Grotesk  | 18px   | 600    | 1.3         | -0.01em        | Subsection headers             |
| `body-lg`         | JetBrains Mono | 16px   | 400    | 1.6         | 0              | Primary body, descriptions     |
| `body`            | JetBrains Mono | 14px   | 400    | 1.6         | 0              | Default body text              |
| `body-sm`         | JetBrains Mono | 13px   | 400    | 1.5         | 0.01em         | Secondary info, timestamps     |
| `caption`         | JetBrains Mono | 11px   | 500    | 1.4         | 0.06em         | Labels, badges, overlines      |
| `data`            | JetBrains Mono | 14px   | 500    | 1.2         | 0.02em         | Table data, metrics            |
| `data-lg`         | JetBrains Mono | 32px   | 700    | 1.0         | -0.01em        | Big numbers, KPI values        |
| `code`            | JetBrains Mono | 13px   | 400    | 1.5         | 0              | Code blocks, addresses, hashes |

### Overline Labels

Section labels and category tags use an "overline" style: all-uppercase, wide letter spacing, tiny size. This is a signature element of the Cipher aesthetic.

```css
.overline {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-secondary);
}
```

---

## 4. Spacing & Layout

### Spacing Scale

Use a 4px base grid:

```
4px  | --space-1  | Inline padding, icon gaps
8px  | --space-2  | Tight element spacing
12px | --space-3  | Default inner padding
16px | --space-4  | Card inner padding, section gaps
24px | --space-6  | Between card groups
32px | --space-8  | Major section breaks
48px | --space-12 | Page section padding
64px | --space-16 | Hero areas, major landmarks
```

### Dashboard Grid

The dashboard uses a sidebar + main content layout:

```
+------------------+-----------------------------------------------+
|                  |                                               |
|    SIDEBAR       |           MAIN CONTENT AREA                  |
|    240px fixed   |           flex: 1                             |
|    (collapsible  |                                               |
|     to 64px)     |   +-------------------+-------------------+  |
|                  |   |   CARD (span 1)   |   CARD (span 1)   |  |
|  Logo            |   +-------------------+-------------------+  |
|  Nav items       |   |                                       |  |
|  System status   |   |   CARD (span 2 - full width)          |  |
|                  |   |                                       |  |
|                  |   +-------------------+-------------------+  |
|                  |   |   CARD            |   CARD            |  |
+------------------+-----------------------------------------------+
```

Main content grid:
- Use CSS Grid with `grid-template-columns: repeat(auto-fit, minmax(400px, 1fr))`
- Gap: 16px between cards
- Page padding: 24px
- Cards can span 1 or 2 columns

### Card Component

Cards are the primary content container. They should feel like terminal panels.

```css
.card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 20px;
  position: relative;
  overflow: hidden;
  transition: border-color 0.2s ease, box-shadow 0.3s ease;
}

.card:hover {
  border-color: var(--border-default);
  box-shadow: inset 0 1px 0 0 rgba(255,255,255,0.03);
}

/* Card header */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-subtle);
}

/* Optional: scanline texture overlay on cards */
.card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(0, 0, 0, 0.03) 2px,
    rgba(0, 0, 0, 0.03) 4px
  );
  pointer-events: none;
  z-index: 1;
  opacity: 0.5;
}
```

---

## 5. Component Specifications

### 5.1 Sidebar Navigation

The sidebar is always visible (collapsible on mobile). Dark, minimal, with the Sentinel logo at top.

```
STRUCTURE:
  [Logo: "SENTINEL" in JetBrains Mono, weight 700, with a small
   animated cyan dot/pulse to the left representing "the eye"]

  [Overline: "MONITORING"]
  - Live Monitor        (icon: activity/pulse)
  - Anomaly Feed        (icon: alert-triangle)

  [Overline: "ANALYSIS"]
  - Case Detail         (icon: file-search)
  - Sentinel Index      (icon: database)

  [Overline: "COMMUNITY"]
  - Arena               (icon: users)

  [Overline: "SYSTEM"]
  - System Health       (icon: cpu)
  - Settings            (icon: settings)

  [Bottom: connection status indicator]
  - "CONNECTED" with green dot, or "OFFLINE" with red dot
  - Last sync timestamp in caption style
```

Nav items:
- Default: `--text-secondary`, no background
- Hover: `--text-primary`, `--bg-hover` background
- Active: `--accent-primary` text, `--accent-bg` background, left border 2px `--accent-primary`
- Icons: 18px, Lucide icon set (stroke-width: 1.5)
- Font: JetBrains Mono, 13px, weight 500

### 5.2 KPI Metric Cards (Top Row)

A row of 4-5 key metrics across the top of the main view.

```
+--------------------------------------+
|  OVERLINE LABEL              [icon]  |
|                                      |
|  128                                 |  <-- data-lg, accent color
|  +12.4% vs 24h                       |  <-- body-sm, green/red
|  ================================    |  <-- thin sparkline
+--------------------------------------+
```

Spec:
- Height: ~120px
- Background: `--bg-secondary` with very subtle gradient shimmer
- The big number should use `--accent-primary` color (or threat color if it represents a threat metric)
- Sparkline: 40px tall, stroke-width 1.5, color matching the metric's semantic meaning
- Change indicator: green up-arrow for positive, red down-arrow for negative

Suggested KPIs:
1. Active Anomalies (count)
2. Cases Under Review (count)
3. Average BSS Score (number)
4. System Uptime (percentage)
5. Markets Monitored (count)

### 5.3 Anomaly Feed / Live Monitor

The primary view. A real-time scrolling feed of detected anomalies.

Each anomaly row:

```
+-----------------------------------------------------------------------+
| [THREAT BADGE]  Market Name                        2 min ago     [>]  |
| INSIDER         "Will X happen by date?"                              |
|                                                                       |
| BSS: 78 ████████░░  |  PES: 45 ████░░░░░░  |  Confidence: 0.89      |
|                                                                       |
| Signals: Volume Spike, Fresh Wallet, Cluster Match                    |
+-----------------------------------------------------------------------+
```

Spec:
- Rows alternate between `--bg-secondary` and `--bg-primary`
- Threat badge: pill-shaped, 11px uppercase mono, colored background at 15% opacity with colored text
  - INSIDER: `--threat-critical` (red)
  - OSINT_EDGE: `--threat-high` (orange)
  - FAST_REACTOR: `--threat-medium` (yellow)
  - SPECULATOR: `--threat-low` (green)
- BSS/PES bars: 6px tall, rounded, background `--border-subtle`, fill uses threat-level gradient
- Timestamp: relative ("2 min ago"), `--text-tertiary`
- On hover: row lifts slightly (translateY -1px), border-left 3px in threat color
- New items animate in from top with a subtle slide + fade (200ms ease-out)

### 5.4 Case Detail View

The deep-dive view for a single anomaly case. This is where the Temporal Gap Chart lives -- the KEY visualization.

Layout:
```
+---------------------------+---------------------------+
|  CASE HEADER (full width)                             |
|  Classification badge + Market name + BSS/PES scores  |
+---------------------------+---------------------------+
|                           |                           |
|  TEMPORAL GAP CHART       |  WALLET PROFILE           |
|  (span 2, hero element)   |                           |
|  Shows trade timing vs    |  Address (truncated)      |
|  OSINT event timing       |  Age, trade count         |
|                           |  Win rate                 |
|                           |  Risk flags               |
+---------------------------+---------------------------+
|                           |                           |
|  AI ANALYSIS              |  OSINT EVENTS             |
|  Stage 1 triage output    |  Related news/events      |
|  Stage 2 deep reasoning   |  with timestamps          |
|  Fraud triangle viz       |                           |
+---------------------------+---------------------------+
|  SAR REPORT (full width, collapsible)                 |
|  Generated Suspicious Activity Report                 |
+-------------------------------------------------------+
```

#### Temporal Gap Chart (Hero Visualization)

This is the most important chart in the entire dashboard. It shows the time relationship between trading activity and public information release.

```
  TRADE BEFORE INFO (suspicious)          TRADE AFTER INFO (normal)
       <----- gap ----->                     <----- gap ----->

  ╔═══════╗              ╔═══════╗
  ║ TRADE ║──────────────║ NEWS  ║──────────────────────────────> time
  ╚═══════╝   12h gap    ╚═══════╝
     ^                      ^
   Trade at                News breaks
   0.72 -> 0.95           "Event confirmed"
```

Implementation:
- Use a horizontal timeline (left to right)
- Trade events as cyan circles/diamonds on the line
- OSINT events as orange circles on the line
- The GAP between them is the key visual: shade it with a gradient from red (suspicious, trade before news) to green (normal, trade after news)
- Label the gap duration prominently: "12h 34m BEFORE public information"
- The gap area should pulse gently if classification is INSIDER or OSINT_EDGE
- Below the timeline, show a mini price chart for the market during this period

Chart tech: Use Recharts (available in React artifacts) or D3. Prefer Recharts for simpler implementation.

### 5.5 Sentinel Index (Searchable Database)

A data table of all processed cases.

```
+-----------------------------------------------------------------------+
| SENTINEL INDEX                                    [Search] [Filters]  |
+-----------------------------------------------------------------------+
| ID    | Market          | Class.     | BSS | PES | Time    | Status   |
|-------|-----------------|------------|-----|-----|---------|----------|
| S-001 | Iran Strike...  | INSIDER    | 85  | 30  | 2h ago  | REVIEW   |
| S-002 | Bitcoin 100k... | SPECULATOR | 22  | 78  | 4h ago  | CLEARED  |
| S-003 | FDA Approval... | OSINT_EDGE | 67  | 55  | 6h ago  | FLAGGED  |
+-----------------------------------------------------------------------+
```

Spec:
- Table header: `--bg-tertiary`, overline style text, sticky
- Rows: alternating `--bg-primary` / `--bg-secondary`
- Classification column: use colored badge (same as anomaly feed)
- BSS column: color-code the number (>70 red, 40-70 yellow, <40 green)
- Status column: pill badges
  - REVIEW: cyan outline
  - FLAGGED: red fill at 15%
  - CLEARED: green fill at 15%
  - PENDING: grey outline
- Sortable columns (click header to sort, show arrow indicator)
- Filter bar: dropdown filters for classification, status, date range, BSS threshold
- Search: searches market name, case ID, wallet addresses

### 5.6 Arena (Human-in-the-Loop Voting)

An interface for human analysts to vote on AI classifications.

```
+-----------------------------------------------------------------------+
|  ARENA: CASE S-003                                                    |
+-----------------------------------------------------------------------+
|                                                                       |
|  Market: "FDA Approval for Drug X by Q2?"                             |
|  AI Classification: OSINT_EDGE (confidence: 0.73)                     |
|                                                                       |
|  [Summary of evidence...]                                             |
|                                                                       |
|  +-----------+ +-----------+ +-----------+ +-----------+              |
|  |  INSIDER  | |OSINT_EDGE | |FAST_REACT | |SPECULATOR |              |
|  | (12 votes)| |(8 votes)  | |(3 votes)  | |(1 vote)   |              |
|  +-----------+ +-----------+ +-----------+ +-----------+              |
|                                                                       |
|  Consensus: INSIDER (48% agreement)                                   |
|  [============================--------]                               |
+-----------------------------------------------------------------------+
```

Spec:
- Vote buttons: large (60px height), bordered, with vote count
- Selected vote: filled background in classification color, border glow
- Consensus bar: horizontal bar showing vote distribution with colored segments
- After voting: show "Your vote: X" confirmation, disable re-voting
- Include an optional text field for analyst notes

### 5.7 System Health Panel

```
+-----------------------------------------------------------------------+
|  SYSTEM HEALTH                                          ALL SYSTEMS GO |
+-----------------------------------------------------------------------+
|                                                                        |
|  Polymarket API    [====] CONNECTED     Latency: 45ms                 |
|  Mistral AI        [====] CONNECTED     Model: mistral-small-latest    |
|  OSINT Pipeline    [====] CONNECTED     Sources: 4/5 active           |
|  WebSocket Feed    [====] CONNECTED     Events/min: 12                |
|  Database          [====] CONNECTED     Size: 24MB                    |
|                                                                        |
|  Pipeline Throughput    ████████████████████░░░░   78 cases/hr         |
|  Classification Acc.    ████████████████░░░░░░░░   72% (Arena)        |
|  FPR                    ██░░░░░░░░░░░░░░░░░░░░░░   8.2%              |
|  FNR                    ████░░░░░░░░░░░░░░░░░░░░   15.1%             |
|                                                                        |
+-----------------------------------------------------------------------+
```

Spec:
- Status dots: 8px circles, pulsing green for connected, static red for down
- Metric bars: thin (4px), rounded, colored by health (green > yellow > red)
- "ALL SYSTEMS GO" banner: green text when healthy, red "DEGRADED" when issues exist

---

## 6. Background & Ambient Effects

These are what make the dashboard feel ALIVE. They run behind the main content.

### 6.1 ASCII Flow Trail (Hero/Background)

Inspired by the Framer ASCII FlowTrail component. Implement as a full-page canvas behind the main content.

Behavior:
- Renders a grid of ASCII characters (use: `/ \\ | - + * . : ; ,`) in `--text-tertiary` color (very faint)
- Characters slowly drift/flow in a direction (like wind or data streaming)
- On mouse movement: characters near cursor ripple outward, temporarily becoming brighter and cycling through different characters
- Dithering style: Halftone or Atkinson for that retro-tech look
- Canvas covers the entire background, sits at z-index 0
- Opacity: 0.15 max -- this is ambient, not distracting

Implementation approach:
- Use an HTML `<canvas>` element covering the viewport
- Render ASCII characters on a grid (approximately 12px spacing)
- Use `requestAnimationFrame` for smooth 30fps animation
- Characters flow from top-right to bottom-left (diagonal, like falling data)
- Mouse proximity causes local distortion: characters within 80px radius grow slightly, become `--accent-primary` color, and scatter

Performance: Keep character count reasonable. On a 1920x1080 screen at 12px spacing, that's ~160x90 = 14,400 characters. Render at 30fps to keep CPU usage low. Consider reducing density on mobile.

### 6.2 Interactive Dot Grid (Section Backgrounds)

Inspired by the Framer Interactive Dot Grid component. Use in hero sections and behind the KPI row.

Behavior:
- A uniform grid of small dots (2px diameter, 20px spacing) in `--border-subtle` color
- On mouse proximity: dots within a radius (100px) scale up to 4px and shift toward `--accent-primary` color
- Smooth spring-based animation as mouse moves
- Creates a "breathing" effect around the cursor

Implementation:
- Canvas-based for performance
- Or CSS grid of `<span>` elements with JavaScript tracking mouse position (simpler but heavier DOM)
- For React: use a canvas ref and animate with requestAnimationFrame
- Dot count: keep to ~2000 max per section

### 6.3 Scanline Overlay (Subtle)

A very faint CRT scanline effect applied globally via CSS:

```css
body::after {
  content: '';
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 1px,
    rgba(0, 0, 0, 0.015) 1px,
    rgba(0, 0, 0, 0.015) 2px
  );
  pointer-events: none;
  z-index: 9999;
}
```

This is EXTREMELY subtle. The user should not consciously notice it, but it gives the whole interface a slightly textured, terminal-like quality.

---

## 7. Animation & Motion

### Principles

- Prefer `transform` and `opacity` for all animations (GPU-composited)
- Default easing: `cubic-bezier(0.16, 1, 0.3, 1)` (fast out, slow in -- feels responsive)
- Duration scale: micro (100ms), fast (200ms), normal (300ms), slow (500ms), dramatic (800ms)
- NEVER animate layout properties (width, height, top, left) -- use transforms

### Page Load Sequence

When a page loads, elements should appear in a choreographed sequence:

1. **0ms**: Background effects (ASCII trail, dot grid) fade in at 300ms
2. **100ms**: Sidebar nav items stagger in from left, 50ms between each
3. **200ms**: KPI cards stagger in from bottom (translateY 20px -> 0), 80ms between each
4. **400ms**: Main content cards fade and slide up, 60ms between each
5. **600ms**: Chart data animates (lines draw, bars grow)

### Micro-interactions

| Element | Trigger | Animation |
|---------|---------|-----------|
| Card | hover | `border-color` transition 200ms, subtle `translateY(-1px)` |
| Button | hover | Background shifts, subtle `scale(1.02)` |
| Button | click | Quick `scale(0.98)` then release |
| Nav item | hover | Background fades in, text brightens |
| Threat badge | appear | Quick `scale(0 -> 1)` with a 50ms bounce |
| New feed item | enter | Slide down from top + fade, 200ms |
| Metric number | update | Counter animates from old value to new (500ms) |
| Chart | data update | Smooth morphing transition (300ms) |
| Toggle/switch | click | Spring animation on thumb position |

### Loading States

- Skeleton screens: Use `--bg-tertiary` blocks with a shimmer animation (a diagonal light sweep)
- The shimmer should use: `background: linear-gradient(90deg, transparent, rgba(0,240,255,0.03), transparent)` animated from left to right over 1.5s, looping

---

## 8. Iconography

Use **Lucide React** icons throughout:
- Stroke width: 1.5px
- Size: 18px default, 16px in compact contexts, 24px for nav
- Color: inherits text color (usually `--text-secondary`)
- Active: `--accent-primary`

Key icons:
| Purpose | Lucide Icon |
|---------|-------------|
| Live Monitor | `Activity` |
| Anomalies | `AlertTriangle` |
| Cases | `FileSearch` |
| Database/Index | `Database` |
| Arena | `Users` |
| System Health | `Cpu` |
| Settings | `Settings` |
| Search | `Search` |
| Filter | `Filter` |
| Wallet | `Wallet` |
| Time/Clock | `Clock` |
| Expand/Detail | `ChevronRight` |
| Close | `X` |
| Success | `CheckCircle2` |
| Warning | `AlertCircle` |
| Error | `XCircle` |
| Trend Up | `TrendingUp` |
| Trend Down | `TrendingDown` |

---

## 9. Data Visualization

### Chart Theme

All charts share a consistent theme:

```javascript
const chartTheme = {
  backgroundColor: 'transparent',
  gridColor: '#1A1A2E',             // --border-subtle
  axisLabelColor: '#55556A',        // --text-tertiary
  axisLineColor: '#2A2A3E',         // --border-default
  tooltipBg: '#0F0F18',            // --bg-tertiary
  tooltipBorder: '#2A2A3E',
  tooltipTextColor: '#E8E8F0',
  fontFamily: "'JetBrains Mono', monospace",
  fontSize: 11,
};
```

### Chart Types Used

1. **Temporal Gap Timeline** (Case Detail) -- Custom horizontal timeline with event markers
2. **Price/Volume Area Chart** (Case Detail) -- Filled area chart showing market movement
3. **BSS vs PES Scatter Plot** (Sentinel Index) -- 2x2 quadrant grid with dots colored by classification
4. **Sparklines** (KPI cards, table rows) -- Minimal line charts, no axes, just the stroke
5. **Bar Charts** (System Health) -- Horizontal progress-style bars
6. **Pie/Donut** (Arena voting) -- Donut chart showing vote distribution

### Tooltip Style

```css
.chart-tooltip {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-default);
  border-radius: 6px;
  padding: 8px 12px;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-primary);
  box-shadow: 0 8px 32px rgba(0,0,0,0.5);
}
```

---

## 10. Responsive Behavior

### Breakpoints

```
Mobile:   < 768px    -- Sidebar collapses to bottom tab bar, single column
Tablet:   768-1024px -- Sidebar collapses to 64px (icons only), 1-2 column grid
Desktop:  1024-1440px -- Full sidebar, 2 column grid
Wide:     > 1440px   -- Full sidebar, 2-3 column grid, larger charts
```

### Mobile Adaptations

- Sidebar becomes a bottom tab bar (5 tabs max)
- KPI cards become a horizontal scrolling row
- Tables switch to card-based layout (each row becomes a card)
- Background effects (ASCII trail, dot grid) are disabled or heavily reduced on mobile for performance
- Charts: reduce data point density, increase touch target sizes

---

## 11. Specific UI Patterns

### Classification Badge

```jsx
// The classification badge is used everywhere and must be consistent
<span className={`
  inline-flex items-center gap-1.5
  px-2.5 py-1
  rounded-full
  font-mono text-[11px] font-semibold uppercase tracking-wider
  ${classColors[classification]}
`}>
  <span className="w-1.5 h-1.5 rounded-full bg-current" />
  {classification}
</span>

// Color mapping
const classColors = {
  INSIDER:      'text-[#FF2D55] bg-[#FF2D550F]',
  OSINT_EDGE:   'text-[#FF6B2D] bg-[#FF6B2D0F]',
  FAST_REACTOR: 'text-[#FFB800] bg-[#FFB8000F]',
  SPECULATOR:   'text-[#34D399] bg-[#34D3990F]',
};
```

### Score Bar (BSS/PES)

```jsx
<div className="flex items-center gap-3">
  <span className="font-mono text-xs text-secondary w-8">BSS</span>
  <div className="flex-1 h-1.5 rounded-full bg-border-subtle overflow-hidden">
    <div
      className="h-full rounded-full transition-all duration-500"
      style={{
        width: `${score}%`,
        background: score > 70 ? '#FF2D55' : score > 40 ? '#FFB800' : '#34D399'
      }}
    />
  </div>
  <span className="font-mono text-sm font-semibold w-8 text-right">{score}</span>
</div>
```

### Wallet Address Display

Always truncate wallet addresses with a copy button:

```
0x7a3B...4f2E  [copy icon]
```

Use JetBrains Mono, `--text-secondary`, 13px. Full address appears in a tooltip on hover.

### Timestamp Display

Use relative timestamps in the feed ("2m ago", "1h ago") and absolute timestamps in detail views ("2024-01-15 14:23:07 UTC"). Always use JetBrains Mono.

---

## 12. Implementation Notes

### Recommended Stack

```
Framework:   React 18+ (or Next.js 14+)
Styling:     Tailwind CSS v3 + CSS custom properties for the design tokens
Charts:      Recharts (available in React artifacts, good composability)
Icons:       Lucide React
Animation:   Framer Motion (for page transitions and complex sequences)
             CSS transitions for simple hover/micro-interactions
Canvas:      Raw Canvas API for ASCII trail and dot grid (no library needed)
State:       React Context or Zustand for dashboard state
Data:        REST API calls to the FastAPI backend
```

### File Structure Suggestion

```
src/
  components/
    layout/
      Sidebar.tsx
      DashboardLayout.tsx
      TopBar.tsx
    cards/
      KPICard.tsx
      AnomalyCard.tsx
      CaseCard.tsx
    charts/
      TemporalGapChart.tsx
      PriceVolumeChart.tsx
      BSSvsPESScatter.tsx
      Sparkline.tsx
    ui/
      ClassificationBadge.tsx
      ScoreBar.tsx
      WalletAddress.tsx
      StatusIndicator.tsx
      ThreatBadge.tsx
      Button.tsx
      Input.tsx
      Table.tsx
    effects/
      AsciiFlowTrail.tsx       -- Canvas-based ASCII background
      InteractiveDotGrid.tsx   -- Canvas-based dot grid
      ScanlineOverlay.tsx      -- CSS overlay component
  pages/
    LiveMonitor.tsx
    CaseDetail.tsx
    SentinelIndex.tsx
    Arena.tsx
    SystemHealth.tsx
  hooks/
    useMousePosition.ts        -- For interactive effects
    useAnimatedCounter.ts      -- For KPI number animation
    useWebSocket.ts            -- Real-time data stream
  styles/
    globals.css                -- CSS variables, base styles, font imports
    animations.css             -- Keyframe definitions
  lib/
    api.ts                     -- API client
    colors.ts                  -- Color utility functions
    formatters.ts              -- Date, number, address formatters
```

### Performance Targets

- First Contentful Paint: < 1.5s
- Canvas effects: 30fps minimum, drop to 15fps when tab is not focused
- Disable canvas effects entirely on devices with `prefers-reduced-motion: reduce`
- Lazy-load pages that are not the default view
- Virtualize long lists (anomaly feed, sentinel index table) with react-window or similar

---

## 13. Brand Assets

### Logo

"SENTINEL" in JetBrains Mono Bold, 18px, letter-spacing 0.15em, all uppercase. To the left, a small icon: a stylized eye or crosshair made from simple geometric shapes (circle + crosshair lines), rendered in `--accent-primary` with a subtle pulsing glow animation (opacity oscillates between 0.7 and 1.0 over 2 seconds).

For a minimal version (collapsed sidebar): just the eye/crosshair icon.

### Favicon

A 32x32 representation of the eye icon in cyan on a dark background.

---

## Summary for Implementer

The Sentinel dashboard should feel like a classified intelligence monitoring terminal that happens to be beautifully designed. Every pixel should serve a purpose. The dark palette keeps analysts focused during long monitoring sessions. The monospace typography reinforces precision and data integrity. The ambient ASCII and dot-grid effects communicate that the system is alive and watching without ever distracting from the actual data.

Key priorities in order:
1. Get the layout, typography, and color system right first
2. Build the core components (cards, badges, score bars, tables)
3. Wire up the data visualizations (temporal gap chart is the hero)
4. Add the ambient background effects last (they are polish, not foundation)
5. Add page transition animations as final polish

The aesthetic reference points: Cipher's dark, trust-building cybersecurity vibe crossed with Bloomberg Terminal's information density, brought to life with ASCII art texture and interactive dot-grid particle effects.
