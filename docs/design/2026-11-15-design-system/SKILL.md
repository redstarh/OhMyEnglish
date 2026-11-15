---
name: ohmyenglish-design
description: Mobile home design system for OhMyEnglish (2026-11-15). Use when implementing the phone-width home, the full-screen practice card or the Progress screen in app/frontend, so that nothing scrolls at 393x659 or 428x745.
---

# OhMyEnglish mobile home — implementation entry point

## Quick map

| Need | File |
|---|---|
| What is in scope, and what is not | `brief.md` (`## Features in scope`, `## Out of scope`) |
| Color, type, spacing, radius, shadow, motion values | `colors_and_type.css` (oklch; same palette as `app/frontend/app/globals.css`) |
| Which color means what, copy rules, layout rules and measured heights | `README.md` (`VISUAL FOUNDATIONS`, `CONTENT FUNDAMENTALS`) |
| Shared component classes (button, toggle, panel, Day row) | `mockups/components.css` |
| Home idle | `mockups/home-idle.html` |
| Practice, judged, all words matched | `mockups/home-practice.html` |
| Practice with KO on, mismatch result (longest state) | `mockups/home-practice-ko.html` |
| Progress screen (moved off home) | `mockups/progress.html` |
| Icons (Lucide 0.460.0) and logo mark | `assets/icons/`, `assets/logo-mark.svg` |

Sample data in the mockups (counts, dates, unit names, sentences) only shows the layout. Real values come from the existing API.

## Rules

1. Below the `sm` breakpoint, every home and progress screen is one flex column with `height: 100dvh` and `env(safe-area-inset-*)` padding. The document must have `scrollHeight == innerHeight` and `scrollWidth == innerWidth` at 393×659 and at 428×745, in every practice phase.
2. During practice the card replaces the whole screen (the header and the summary line are hidden). Its inner slots have fixed heights: listen bar 4px, sentence 2 lines (`2.8em`, `overflow: hidden`), translation 2 lines while KO is on, and the result slot takes the rest. The `Previous / Start|Try again / Next` row never moves between idle, ① Listen, ② Say it and ③ Check.
3. The home screen holds only the header (logo, name, `trending-up` button to Progress), the one-line summary and the Today's practice card. Progress, the Day path, View all and Focus patterns live on the Progress screen. Free talk, Weak spots, More practice, Practice a pattern and videos are not drawn.
4. Every tap target is at least 44px tall (`--size-touch`). Every control has a `--border-strong` outline and a `:focus-visible` ring (white on the navy hero, inset on toggles).
5. `--accent` is only for forward movement (`Next →`, `History →`, `Weekly report →`) and the selected toggle. Back and neutral buttons are gray (`--surface-muted` + `--border-strong`). `--primary-500` is never used for text.
6. Text colors are `--fg1`, `--fg2` and `--fg3` only, and none lighter than `--fg3` (4.98:1 on `--bg`). On the hero, use `--on-hero` and `--on-hero-2`.
7. Copy is the existing app copy. Do not add labels, hints or explanations. Korean appears only in the translation line. No emoji.
8. Before claiming the screen is done, measure it in a 393×659 and a 428×745 viewport with the 61-character sentence ("We deploy on Fridays. This week we are deploying on Thursday."), KO on and a mismatch result. Paste the measured `scrollHeight` values.
