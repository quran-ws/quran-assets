<div align="center">

<img src=".github/banner.svg" alt="Quran Assets — Pages & Assets, Beta" width="820">

**Surah headers, page frames and ayah markers traced from eight printed mushafs, and ayah markers drawn from Arabic fonts — recolourable SVGs under one contract.**

<a href="https://quran.ws/blocks/quran-assets"><img alt="See it work" src="https://img.shields.io/badge/See_it_work-15705D?style=for-the-badge&labelColor=102F29"></a>
<a href="https://quran.ws/docs/reference/quran-assets"><img alt="Documentation" src="https://img.shields.io/badge/Documentation-102F29?style=for-the-badge&labelColor=102F29"></a>

</div>

> زخارف المصاحف — عناوين السور وأُطُر الصفحات وعلامات الآيات — مُتَّبعةً من مصاحف مطبوعة ومن خطوط عربية.

| | |
|---|---|
| **Package** | `@quran-ws/assets` · `0.1.0` |
| **Assets** | 71 · two lineages |
| **Provenance** | Scan or font recorded in every file |
| **Licence** | **Scan assets: not redistributable** (CC BY-NC-SA 4.0, provisional) · 40 of 47 font markers OFL-1.1 |

> [!IMPORTANT]
> **The 24 scan assets are not cleared for redistribution.** They are tracings of ornaments whose designs belong to their publishers; `redistributable: false` in `catalog.json` is the gate, and no licence checker will enforce it for you. 40 of the 47 font markers *are* OFL-1.1 and may be redistributed. [The full position](https://quran.ws/docs/reference/licensing).

```sh
# not published yet — read from assets/ in the repository
```

## Where the documentation is

Everything about using it lives on the site. This repository is the source.

| | |
|---|---|
| **Overview and demo** | [quran.ws/blocks/quran-assets](https://quran.ws/blocks/quran-assets) |
| **Reference** | [quran.ws/docs/reference/quran-assets](https://quran.ws/docs/reference/quran-assets) |
| **Use markers, frames and ornaments** | [quran.ws/docs/build/assets](https://quran.ws/docs/build/assets) |
| **Licensing in full** | [quran.ws/docs/reference/licensing](https://quran.ws/docs/reference/licensing) |

## What is in here

| | |
|---|---|
| `assets/` | the SVGs: `surah-headers/`, `page-frames/`, `ayah-markers/` |
| `catalog.json` | one entry per asset — the contract every consumer reads |
| `sources/` | the scans and fonts each asset was traced from |
| `qa/` | the audits that keep the catalogue honest |
| `tests/` | the gates that must stay green |
| `docs/` | how to work on this repository, including rebuilding from source |

Issues and pull requests are welcome here. Everything that is not about *changing* this repository is on the site.
