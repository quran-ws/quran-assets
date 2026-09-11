"""One CLI for the whole repo.

    python -m qa build [--lineage font] [--type page-frames] [--style mushaf-qalon] [--to detect]
    python -m qa catalog          rebuild catalog.json from the meta.json files
    python -m qa optimize         run SVGO over assets/ and refresh path counts
    python -m qa validate         catalog + SVG contract + license checks
    python -m qa quality [...]    raster review sheets and the regression gate
    python -m qa preview          demo/review.html (per-asset review sheet)
    python -m qa demo             demo/index.html (the public demo)
    python -m qa dist             build dist/ for npm and the CDN

`--type` takes the directory name (surah-headers, page-frames, ayah-markers); `--style`
is the `<lineage>-<name>` style id (`mushaf-qalon`, `font-003-regular`). With no
`--lineage`, `build` runs both: the scan pipeline over the mushaf PDFs and the font
one over what is committed in qa/font/. `--to` applies to the scan stages only.
"""
import argparse
import sys

from qa import ASSET_OF_TYPE, TYPE_DIR, split_style


def main(argv=None):
    parser = argparse.ArgumentParser(prog="qa", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="run the scan pipeline for the selected jobs")
    build.add_argument("--type", choices=sorted(TYPE_DIR.values()))
    build.add_argument("--lineage", choices=["scan", "font"], help="build one lineage only")
    build.add_argument("--style", help="style id, e.g. mushaf-qalon")
    build.add_argument("--to", default="vectorize", choices=["render", "detect", "clean", "vectorize"], help="stop after this stage")
    build.add_argument("--force", action="store_true", help="ignore cached page renders")
    build.add_argument("--no-catalog", action="store_true", help="skip the catalog rebuild afterwards")

    sub.add_parser("catalog", help="rebuild catalog.json")
    sub.add_parser("optimize", help="optimize the SVGs in place")
    sub.add_parser("preview", help="write demo/review.html")
    sub.add_parser("demo", help="write demo/index.html")
    sub.add_parser("validate", help="check the catalog, the SVG contract and licenses")
    dist = sub.add_parser("dist", help="build dist/ for npm and the CDN")
    dist.add_argument("--exclude-unconfirmed", action="store_true",
                      help="leave out assets whose license is not 'confirmed' (default: ship them flagged)")
    sub.add_parser("quality", help="raster review and regression gate (see `qa quality --help`)", add_help=False)

    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "quality":   # its own flags, forwarded untouched
        from qa.common.quality import main as quality_main
        return quality_main(argv[1:])
    args = parser.parse_args(argv)

    if args.command == "build":
        from qa.common.catalog import write_catalog
        # --style names one asset, so it also says which lineage to run.
        lineage = args.lineage
        if args.style:
            try:
                style_lineage, name = split_style(args.style)
            except ValueError as e:
                raise SystemExit(f"{e} -- try --style mushaf-{args.style}")
            if lineage and lineage != style_lineage:
                raise SystemExit(f"--style {args.style} is {style_lineage}-derived, not {lineage}")
            lineage = style_lineage
        if lineage in (None, "scan"):
            from qa.scan.build import build as run_scan
            run_scan(mushaf=(name if args.style else None), asset=ASSET_OF_TYPE.get(args.type), to=args.to, force=args.force)
        if lineage == "font" and args.type not in (None, "ayah-markers"):
            # Say so rather than exiting 0 having built nothing.
            raise SystemExit(f"the font lineage only produces ayah-markers, not {args.type}")
        if lineage in (None, "font") and args.type in (None, "ayah-markers"):
            from qa.font.build import build as run_font
            print(f"font: {run_font(style=args.style)} markers")
        if not args.no_catalog and args.to == "vectorize":
            print(f"catalog: {write_catalog()} assets -> catalog.json")
        return 0
    if args.command == "catalog":
        from qa.common.catalog import write_catalog
        print(f"catalog: {write_catalog()} assets -> catalog.json")
        return 0
    if args.command == "optimize":
        from qa.common.optimize import main as optimize
        optimize()
        return 0
    if args.command in ("preview", "demo"):
        import runpy
        runpy.run_module(f"qa.common.{args.command}", run_name="__main__")
        return 0
    if args.command == "validate":
        from qa.common.validate import main as validate
        return validate()
    if args.command == "dist":
        from qa.common.dist import main as dist
        dist(exclude_unconfirmed=args.exclude_unconfirmed)
        return 0
    raise SystemExit(f"unknown command {args.command}")


if __name__ == "__main__":
    sys.exit(main())
