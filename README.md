<div align="center">

<img src=".github/banner.svg" alt="Quran Assets — Pages & Assets, Beta" width="820">

**A library of Mushaf visual elements, including surah headers, page frames, and ayah markers, sourced from printed Mushafs and Arabic fonts and provided as recolourable SVGs.**

<a href="https://quran.ws/blocks/quran-assets"><img alt="See it work" src="https://img.shields.io/badge/See_it_work-15705D?style=for-the-badge&labelColor=102F29"></a>
<a href="https://quran.ws/docs/reference/quran-assets"><img alt="Documentation" src="https://img.shields.io/badge/Documentation-102F29?style=for-the-badge&labelColor=102F29"></a>

</div>

Use it when designing a Quran application or website and you need ready-made Mushaf-style visual elements instead of recreating them yourself.

> مكتبة لعناصر المصحف البصرية، مثل عناوين السور، وأُطر الصفحات، وعلامات الآيات، مستخرجة من مصاحف مطبوعة وخطوط عربية ومتاحة بصيغة SVG قابلة للتلوين.
>
> استخدمها عندما تصمم تطبيقًا أو موقعًا قرآنيًا وتحتاج عناصر مصحفية جاهزة ومتناسقة بدل إعادة رسمها من الصفر.

| | |
|---|---|
| **Package** | `@quran-ws/assets` · `0.1.0` |
| **Assets** | 71 · two lineages |
| **Provenance** | Scan or font recorded in every file |
| **Licence** | 40 of 47 font markers OFL-1.1 · scan assets CC BY-NC-SA 4.0, provisional |

> [!NOTE]
> Every asset carries its own licence and status in `catalog.json`. 40 of the 47 font markers are OFL-1.1 and confirmed; the 24 scan-derived ornaments are tracings of designs that belong to their publishers and sit at CC BY-NC-SA 4.0, provisional, while permission is settled per publisher. [The full position](https://quran.ws/docs/reference/licensing).

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
