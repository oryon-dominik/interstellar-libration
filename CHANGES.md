# libration Changelog

---

## [2026.11.4](https://github.com/oryon-dominik/interstellar-libration/compare/2026.11.3..2026.11.4) - 2026-11-13

### Answers

#### Bug Fixes

- **(answers)** [**breaking**] freeze choices and option extras all the way down — only the top level was read-only - ([efbdb2c](https://github.com/oryon-dominik/interstellar-libration/commit/efbdb2c3f30bf1e983b7f6f82e338946808b8dcd))



### Menus

#### Bug Fixes

- **(menus)** [**breaking**] a menu built in code passes the checks of load — it skipped every one - ([903bbf7](https://github.com/oryon-dominik/interstellar-libration/commit/903bbf7c55c9f64fcb3b69c78cb989f30070de74))
- **(menus)** [**breaking**] refuse repeated closed values and menus beyond strict mode's limits — OpenAI refused them late - ([92bbd13](https://github.com/oryon-dominik/interstellar-libration/commit/92bbd130d9175132b12fa7869cb6762487ba4aef))

#### Documentation

- **(menus)** reflow the module docstring — a line broke mid-sentence - ([4ece31d](https://github.com/oryon-dominik/interstellar-libration/commit/4ece31de975f3c9c15ff753945d91de89063a2db))



### Readme

#### Testing

- **(readme)** run the Option.extra example — no test read it - ([92bb2db](https://github.com/oryon-dominik/interstellar-libration/commit/92bb2db7cc0fe48fe21ab231287d1027a949dcfd))




---

## [2026.11.3](https://github.com/oryon-dominik/interstellar-libration/compare/2026.11.2..2026.11.3) - 2026-11-13


---

## [2026.11.2](https://github.com/oryon-dominik/interstellar-libration/compare/2026.11.1..2026.11.2) - 2026-11-13

### Answers

#### Bug Fixes

- **(answers)** a reason that is no string is named as such — it was reported empty - ([9a851eb](https://github.com/oryon-dominik/interstellar-libration/commit/9a851eb9c5b4c49f74dc25ddb3aa00afaa20687e))



### Package

#### Build

- **(package)** keywords name only what the package does — curated, no search bait - ([0414d77](https://github.com/oryon-dominik/interstellar-libration/commit/0414d775d1861f3747576cd1f68087fe3e134c36))



### Readme

#### Documentation

- **(readme)** a menu built in code skips the checks of load — the API table promised more - ([3f90f95](https://github.com/oryon-dominik/interstellar-libration/commit/3f90f95f162313ef6f5f9a53b3f3e038c72e7dc6))



### Schemas

#### Refactor

- **(schemas)** the property fragment is named for what it is — found found nothing - ([eca5f2f](https://github.com/oryon-dominik/interstellar-libration/commit/eca5f2fb4e84edbbb061475d27e349c5c1650390))



### Template

#### Chores

- **(template)** take templates 2026.11.41 — just release and just publish start from the terminal - ([3a259ed](https://github.com/oryon-dominik/interstellar-libration/commit/3a259ed2a775258a9411e4fef86dccfbafbed022))
- **(template)** take the station layer of templates 41a4edad — LF hook - ([a7848ad](https://github.com/oryon-dominik/interstellar-libration/commit/a7848add6f8619ab010595211fab0574941d21de))
- **(template)** take the library layer of templates 41a4edad — LF hook - ([3fcb10c](https://github.com/oryon-dominik/interstellar-libration/commit/3fcb10cd739864e92aea7ab52dccf717d011b24c))
- **(template)** take the station layer of templates 7813f3c0 — migrations stay out of ruff - ([05c7bd1](https://github.com/oryon-dominik/interstellar-libration/commit/05c7bd12a11287c45109970c39845e2bac8b4bb6))
- **(template)** take the library layer of templates 7813f3c0 — migrations stay out of ruff - ([853c1c8](https://github.com/oryon-dominik/interstellar-libration/commit/853c1c8ce08e6d49b4d7f9060bb3ca19ce1148d1))




---

## [2026.11.1](https://github.com/oryon-dominik/interstellar-libration/compare/2026.11.0..2026.11.1) - 2026-11-06

### Readme

#### Documentation

- **(readme)** the fleet's badges plus PyPI — strangers see them first - ([9613caa](https://github.com/oryon-dominik/interstellar-libration/commit/9613caa9dd71beb4ae9f5bcafbd16ca794b5c7b2))



### Template

#### Chores

- **(template)** take templates 2026.11.40 — the badges are the template's now - ([070c605](https://github.com/oryon-dominik/interstellar-libration/commit/070c605b6741e3422992ed6b867553fc0d23feda))




---

## 2026.11.0 - 2026-11-06

First public release: closed-list menus read from TOML, the strict schema and instructions a model answers against, and answers read into a choice or a refusal.
