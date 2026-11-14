# Style catalog (what the skill can make, and how)

Every style is a combination of (a) grade and type in Edits, (b) moves Edits already has (punch-ins, transitions,
text animations), and (c) at most one generated layer kind when Edits cannot draw it. Pick styles per section
(`segments[].look` in the EDL). Status: **ready** = Edits does it or an existing generator does; **build** = new
generator or Edits probe needed before it is safe to promise.

The three original looks (`looks.md`) stay the defaults: **bold**, **cool girl**, **cool dude**.

## Word and text styles

| id | Look | How it is made | Layer kind | Status |
|---|---|---|---|---|
| `bold` | Kinetic lowercase words, big ones behind the head | Edits text + `layer: behind` | alpha speaker layer (matte.py) | ready (needs alpha codec OK) |
| `cool-girl` | Small calm caps + one serif-italic punch word in yellow | Edits text, grade | none | ready |
| `cool-dude` | Tracked caps + heavy serif words, slow push-ins | Edits text, slow zoom keyframes | none | ready |
| `recorte-papel` | Paper card with bold black word, slightly rotated, drop shadow (reel 2, "RECORTE PAPEL") | `scripts/reelstyles.py --style recorte-papel` | generated text overlay (alpha) | generator ready; still checked, not yet exported in Edits |
| `adesivo` | Yellow label with black text and tape corners ("texto adesivo") | `scripts/reelstyles.py --style adesivo` | generated overlay (alpha) | ready: placed and exported in Edits |
| `rabisco` | Hand-drawn yellow scribble ring around a word, drawn on | `scripts/reelstyles.py --style rabisco` | generated overlay (alpha) | generator ready; still checked, not yet exported in Edits |
| `manchete` | Black-bordered white headline box, slams in (keep to 3-6 words; longer text shrinks) | `scripts/reelstyles.py --style manchete` | generated overlay (alpha) | generator ready; still checked, not yet exported in Edits |
| `digitado` | Typewriter words, mono font, blinking cursor | Edits text (mono), per-word reveal | none | ready (verify mono font in Edits) |

## Background and frame styles

| id | Look | How it is made | Layer kind | Status |
|---|---|---|---|---|
| `parede-caracteres` | Dark background wall of falling characters behind the speaker (reel 2 intro) | `scripts/reelstyles.py --style parede-caracteres` (full canvas, use `layer: behind`). Use `--codec hevc` on a Mac: ProRes for 3 s was 210 MB | generated behind layer (alpha) | generator ready; still checked, not yet exported in Edits |
| `moldura-camera` | Camera focus brackets, REC dot and timecode over the frame (`--text` = timecode) | `scripts/reelstyles.py --style moldura-camera` | generated overlay (alpha) | ready: placed and exported in Edits |
| `flash-transicao` | White flash or light sweep between sections | Edits transition or short white overlay | none or alpha | ready |
| `antes-depois` | Vertical wipe split with ANTES / DEPOIS labels | Edits split wipe if available, else two clips + mask | none | ready (probe wipe) |
| `split-tela` | Two creators side by side, or a reaction split | Two clips with cropped transforms | none | build (probe multi-track layout) |

## Insert styles (generated UI and data, alpha)

| id | Look | How it is made | Layer kind | Status |
|---|---|---|---|---|
| `mockup-celular` | Phone mockup floating beside the head, showing app or post | Generated insert (overlays.md brief) | alpha insert | ready (pattern exists) |
| `card-comparativo` | ANTES / HOJE cards with a time or money number | Generated insert | alpha insert | ready (pattern exists) |
| `mapa-plantas` | Map with pins or floor plan with area numbers (reel 1 real estate) | Generated insert, static or animated | alpha insert | build |
| `chat-ia` | Chat UI (ChatGPT / Claude) with two cards, the one named wins | Generated insert (claude-desktop example) | alpha insert | ready (claude-desktop example) |
| `cta-saiba-mais` | "Toque em **Saiba mais** ↓" CTA with arrow, yellow highlight | Edits text + arrow, or generated insert | Edits text or alpha | ready |
| `infografico` | Anatomy or diagram that draws in step by step (reel 1 medical) | Generated insert, SVG draw-on | alpha insert | build (heavy, use only on request) |

## Rules
- A style is only used when the user asked for it OR when the script clearly fits it. Never mix more than two
  text styles in one section. The grade follows the base look, not the sticker or paper style.
- Generated text styles (`recorte-papel`, `adesivo`, `rabisco`, `manchete`, `parede-caracteres`) must use only the
  palette of the chosen identity or look and the fonts in `looks.md`. No copied logos, no real creator's brand.
- Stat, price or map content on a real person's card is a generic placeholder unless the user's own profile.
- Before any `build` style is promised in a reply, say it is new and show one test frame first.
