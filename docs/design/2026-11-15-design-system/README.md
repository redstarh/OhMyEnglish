# OhMyEnglish — Design System

Mobile home redesign, 2026-11-15. Scope: the phone-width home only (393–428 CSS px wide). The desktop (1400) layout is unchanged.
Brief: `brief.md`. Tokens: `colors_and_type.css`. Mockups: `mockups/`.

## Product context

OhMyEnglish is a daily speaking drill for one Korean adult learner. Every day they hear a short English sentence, say it out loud and see what they said.
They use it on iPhone Safari, held in one hand, for a short session. The daily sentence practice is the main thing on the screen. Anything else gives way to it.

| Surface | Purpose | Mockups |
|---|---|---|
| Home (idle) | Open the app and start today's practice in one tap | `mockups/home-idle.html` |
| Home (practising) | The practice card fills the screen: sentence, live line, result, navigation | `mockups/home-practice.html`, `mockups/home-practice-ko.html` |
| Progress | Detailed progress, the Day path and focus patterns, moved off the home screen | `mockups/progress.html` |

Target viewports (Safari visible area, measured in the brief): 428×745 (iPhone 12 Pro Max) and 393×659 (iPhone 16).
There is one fluid layout for both. Each screen is a column of exactly `100dvh`. There are no per-device variants.

## CONTENT FUNDAMENTALS

- Language: the UI is English. Korean appears only in the translation line under the sentence (`lang="ko"`). Every other string is English.
- Voice: plain and short. Second person when addressing the learner ("Say it out loud."). No exclamation marks, no praise words.
- Buttons start with a verb, or are a single direction word with an arrow: `Start speaking`, `Try again`, `Start`, `Next →`, `← Previous`, `← Close`, `← Home`, `History →`, `Weekly report →`, `View all`, `Finish Day`.
- Arrows: `←` means going back or leaving, `→` means going forward. Never use `←` for anything except leaving or the previous item.
- Casing: section labels are written in sentence case in the markup ("Today's practice"). They are shown uppercase by CSS (`.label`: 12px, 700, tracking 0.14em). Buttons and body text use sentence case.
- Numbers: counts are written `N / M` with spaces around the slash (`0 / 6 days`, `Sentence 3 / 5`). Ranges use an en dash with no spaces (`Units 1–21`). Date ranges use an en dash with spaces (`Nov 2 – Nov 8`). Month names are 3-letter English abbreviations. Use the singular form for 1 (`1 day`).
- Separators: inline facts are joined with ` · ` (middle dot with spaces): `Day 1 · Units 1–21`.
- Empty-state copy says what is missing and how to fill it, in one line: `No patterns yet. Start speaking to find them.`
- Error copy says what failed. It never blames the learner: `Can't load the course.`, `I couldn't hear you. Press "Try again" and say it again.`
- Emoji: none, anywhere. Circled step numbers (`① Listen`, `② Say it`, `③ Check`) are the only symbol prefixes allowed.
- No new strings: the mockups reuse the existing app copy. A new label needs a brief change first.

## VISUAL FOUNDATIONS

Overall: quiet and content-first. One navy card is the only dark surface. During practice the sentence is the largest text on screen.

Color roles (all values in `colors_and_type.css`; ratios from `contrast.py`):

| Token | Role | Never used for |
|---|---|---|
| `--bg` (ink-50) | Page background | Cards |
| `--surface` (white) | Cards, sentence panel, Start speaking fill | Page background |
| `--surface-muted` (ink-100) | Gray button fill, progress track, Day badge | Text |
| `--fg1` (ink-900) | Primary text, sentence, unit name | — |
| `--fg2` (ink-600) | Secondary text: meta lines, labels, translation | The sentence or a button label |
| `--fg3` (ink-500) | Tertiary text. Lowest allowed text color (4.98:1 on `--bg`) | Anything lighter; no text below `--fg3` |
| `--border` (ink-200) | Decorative card and panel outlines (1.20:1) | The only boundary of a control |
| `--border-strong` (ink-400) | Outline of every control: buttons, toggles, icon button, Day arrow chip (3.64:1 on white) | Decorative dividers |
| `--accent` (primary-600) | Forward movement (`Next →`, `History →`, `Weekly report →`) and the selected toggle; focus ring | Back or neutral buttons, body text, decoration |
| `--accent-soft` (primary-50) | Background of the "You said" result block; hover on light controls | Selected state |
| `--primary-500` | Progress bar fill only (4.2:1, below AA for text) | Any text or icon |
| `--hero` (primary-900) | Idle Today's practice card only | The practice card (it turns white during practice) |
| `--on-hero-2` | Label, description and Day line on the hero (8.20:1) | Light surfaces |
| `--danger` | Destructive or failed states | Mismatched words (they use underline and strikethrough, not red) |

Type scale (`--font-sans`: Geist, falling back to the system sans; the layout is measured with the fallback):

| Token | Size | Use |
|---|---|---|
| `--fs-h1` | 32px / 800 / lh 1.12 | Hero title, progress number |
| `--fs-sentence` | `clamp(18px, 4.8vw, 21px)` / 650 / lh 1.4 | Practice sentence and the "You said" line (same size, as the brief asks) |
| `--fs-h3` | 17px / 700 | Unit name, app name, stat values |
| `--fs-body` | 15px | Hero description, Start speaking, translation, Day row title |
| `--fs-button` | 13.6px / 600 | All `.btn` and `.toggle` labels |
| `--fs-small` | 13px | Meta lines: summary, `Day 1 · Units 1–21`, `Sentence 3 / 5` |
| `--fs-label` | 12px / 700 / uppercase / 0.14em | Section labels, result labels, legend |
| `--fs-tag` | 10px | Logo tagline, Day badge, stat labels only |

Spacing: a 4px grid (`--space-1` … `--space-12` = 4, 8, 12, 16, 20, 24, 32, 40, 48). Screen padding is 16px left and right, and 12px top and bottom (8px on the practice screens), plus `env(safe-area-inset-*)`. Gaps between screen blocks are 12px.

Sizes: every tap target is at least `--size-touch` (44px) tall. Start speaking and Day rows are `--size-touch-lg` (52px). Measured: no button below 44px in any mockup.

Corners: `--r-md` 8px for buttons and toggles. `--r-lg` 10px for the result block, logo mark, Day badge and Start speaking. `--r-xl` 14px for cards, the hero and the sentence panel. `--r-pill` for bars. No other radius.

Cards: white, a 1px `--border` outline, `--shadow-1`, padding 16px. The hero alone uses `--shadow-2`. `--shadow-3` is reserved for overlays; there are none in this scope.

Borders: 1px only. Never thicker.
Transparency: none, except `--on-hero-2` (white mixed 75% over `--hero`) and disabled controls (`opacity: 0.5`).

Animation: background-color transitions only, `--dur-fast` (120ms) with `--ease-out`. During `② Say it` the 4px listen bar fills with `--accent` using the app's existing `omy-course-listen` / `omy-course-wait` animations. In every other phase it is `transparent` but keeps its height. No animation changes the layout.

Hover / press / focus: on hover, light controls go to the next darker step (`--surface-muted` → `--border`) and `--accent` goes to `--primary-700`. Every button and link has `:focus-visible` with a 2px `--focus-ring` outline at a 2px offset. On the hero the ring is white. On toggles the ring sits 4px inside, and it is white on the selected one.

Layout rules:

- Every screen is one flex column with `height: 100dvh`. Never `min-height`. The page never scrolls, vertically or horizontally, at 393×659 or 428×745.
- Home: header (44px) · summary line · hero card. The hero takes all remaining height. Its title group sits at the top and the Start group (Start speaking full width + Day line) at the bottom, within thumb reach.
- Practice: the card fills the screen and the home header is hidden. Inside, the order is fixed: label + Day line with `← Close` · unit name (one line, ellipsis) · KO and Auto/Manual toggles · sentence panel (takes the remaining height) · `← Previous` / `Start` or `Try again` / `Next →` (three equal columns, pinned to the bottom).
- The panel's inner slots have fixed heights that do not depend on state: the meta row; a 4px listen bar, always reserved; the sentence, 2 lines reserved (`2.8em`) with `overflow: hidden`; the translation, 2 lines reserved when KO is on; the result slot, which takes the rest. Moving through idle → ① Listen → ② Say it → ③ Check never moves the buttons.
- Measured worst case (61-character sentence, longest result with `Sentence:` + legend, KO on): at 393×659 the sentence fits in 2 lines (53px of 53px) and the result block uses 214px of a 223px slot. At 428×745 it uses 229px of 304px.
- Progress: `← Home` · Your progress card · Continue your path (heading row with View all + Day rows) · Focus patterns. Measured: everything ends at 627px of 659px at 393×659. When View all expands the Day list beyond the screen, that list (not the page) scrolls. This is not drawn.

## ICONOGRAPHY

- Set: Lucide static, version 0.460.0 (`lucide-static@0.460.0`), outline style, 24px viewBox, `stroke-width 2`, `stroke="currentColor"`.
- Sizes: 20px (`--size-icon`) in buttons and the logo mark, 16px (`--size-icon-sm`) inside the Day arrow chip. No other sizes.
- Color: icons inherit text color. `--accent` on the progress icon button, `--hero` inside Start speaking, `--on-hero` in the logo mark, `--fg1` in the Day chip.
- Key icons: `sparkles` (logo mark), `trending-up` (header button that opens Progress), `play` (Start speaking), `arrow-right` (Day row chip). Text arrows (`←` `→`) are characters in labels, not icons.
- An icon-only button always has `aria-label` and `title` (`Your progress`).
- Logo: `assets/logo-mark.svg`, a placeholder built from the brief: a 36px navy (`--hero`) rounded square, `r` 10px, holding the white `sparkles`. Next to it, "OhMyEnglish" (17px / 800) above "SPEAK. REMEMBER. GROW." (10px, `--fg2`).

## Index

```
2026-11-15-design-system/
├── brief.md                 approved brief (P1)
├── README.md                this file
├── SKILL.md                 entry point for the implementation session
├── colors_and_type.css      tokens (:root only)
├── assets/
│   ├── logo-mark.svg        placeholder mark
│   └── icons/               arrow-right · play · sparkles · trending-up (Lucide 0.460.0)
└── mockups/
    ├── components.css       shared classes
    ├── home-idle.html
    ├── home-practice.html
    ├── home-practice-ko.html
    └── progress.html
```
