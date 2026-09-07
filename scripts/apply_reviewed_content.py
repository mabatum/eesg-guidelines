"""Apply the versioned bone-tumour manuscript after the Wiki export."""
from pathlib import Path
import shutil

SOURCE = Path("content-reviewed/bone-sarcomas")
DESTINATION = Path("docs/gen_docs/bone-sarcomas")
EXPECTED = {
    Path("index.md"),
    *(Path(slug) / "index.md" for slug in (
        "general-principles", "osteosarcoma-adults", "ewing-sarcoma-adults",
        "chondrosarcoma-adults", "giant-cell-tumor-of-bone", "chordoma",
        "rare-bone-tumours",
    )),
}


def main() -> None:
    # Do not re-enable a section deliberately removed by the scope configuration.
    if not DESTINATION.is_dir():
        print("Bone section is outside the current export scope; reviewed overlay skipped.")
        return
    actual = {p.relative_to(SOURCE) for p in SOURCE.rglob("*.md")}
    if actual != EXPECTED:
        raise SystemExit(f"Incomplete reviewed manuscript: missing={EXPECTED - actual}, unexpected={actual - EXPECTED}")
    # Check the complete manifest before replacing any generated text.
    for relative in sorted(EXPECTED):
        source = SOURCE / relative
        text = source.read_text(encoding="utf-8")
        if not text.startswith("# ") or "## Литература" not in text:
            raise SystemExit(f"Missing title or bibliography: {source}")
    for relative in sorted(EXPECTED):
        destination = DESTINATION / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SOURCE / relative, destination)
    print(f"Applied reviewed bone manuscript: {len(EXPECTED)} pages.")


if __name__ == "__main__":
    main()
