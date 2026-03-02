# Landing page

The public-facing site for Sentinel. Single-scroll page with a globe animation, system architecture diagram, and a link through to the dashboard.

Built with React + Vite + TypeScript, styled with Tailwind.

## Running

```bash
cd web
npm install
npm run dev       # http://localhost:5173
npm run build     # Production build → dist/
npm run preview   # Preview the production build
```

## Sections

The page stacks five components top to bottom:

1. **Hero** — Tagline with a typewriter effect, globe animation (uses [cobe](https://github.com/shuding/cobe)), and a launch button
2. **What is Sentinel** — Short product explainer
3. **Architecture** — System diagram showing the detection-to-classification pipeline
4. **CTA** — Links to the dashboard
5. **Footer**

A `DotGrid` component renders a subtle dot pattern behind everything.

## Files

| File | What it does |
|------|-------------|
| `App.tsx` | Page layout (stacks sections) |
| `Hero.tsx` | Landing hero with `TypeWriter` animation |
| `Globe.tsx` | Rotating globe via cobe + framer-motion |
| `DotGrid.tsx` | Background dot pattern |
| `Architecture.tsx` | Pipeline architecture diagram |
| `WhatIsSentinel.tsx` | Product overview section |
| `CTA.tsx` | Call-to-action block |
| `Footer.tsx` | Page footer |
