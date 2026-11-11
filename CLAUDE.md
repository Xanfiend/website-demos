# website-demos

Raivo (Valmiera) sells one-page websites to small Latvian businesses. This repo is the public portfolio and the per-prospect demo pages, served by GitHub Pages at https://xanfiend.github.io/website-demos/.

## Layout
- `index.html`: portfolio front page (Latvian).
- `<slug>/index.html`: generated demo pages. Do not edit by hand.
- `_src/autoserviss.html`: template for car repair shops. `_src/build.py`: shop list and generator. Run `python3 _src/build.py` after any change.
- `assets/avatar.png`: profile picture.

## Rules
- All customer-facing text is Latvian. Keep it plain and honest: no invented statistics, testimonials or client claims.
- Demo pages for real businesses must stay clearly marked as samples (top banner, owner note, footer, `noindex`), with placeholder phone, address and prices.
- Outreach goes out from Raivo's Gmail. Create drafts only; Raivo sends them himself. Business addresses only, each with an opt-out line.
- Do not commit prospect lists or email addresses; this repo is public.
- New business type: add a template in `_src/`, extend `build.py`, link the generic demo from `index.html`.
