#!/usr/bin/env python3
"""BONUS - Quantization sweep across Unsloth's UD ladder for Gemma 4 E2B.

Same weights, same hardware, one variable: bits per weight. Because these are all
"UD" (Unsloth Dynamic) quants, the sensitive layers stay at higher precision in
every one of them -- so the curve you get is a fairer size/speed trade-off than a
flat-quantization ladder would show.

Downloads only what is missing, and tells you the cost before it starts.

    make sweep-quant
    .venv/bin/python bonus/sweeps/quant-sweep.py --grid UD-Q2_K_XL,UD-Q4_K_XL,UD-Q6_K_XL,UD-Q8_K_XL
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import sys
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lib"))
import labkit  # noqa: E402

# Ladder comes from the model registry, so this works for either lab model.
LADDER = labkit.quant_ladder()
DEFAULT_GRID = ["UD-Q2_K_XL", "UD-Q4_K_XL", "UD-Q6_K_XL"]


def filename_for(label: str) -> str:
    return labkit.quant_filename(label)


def remote_sizes() -> dict[str, int]:
    """Ask the Hub how big each file is, so we can warn before downloading."""
    url = f"https://huggingface.co/api/models/{labkit.model_repo()}?blobs=true"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "day20-lab"})
        data = json.loads(urllib.request.urlopen(req, timeout=30).read())
        return {s["rfilename"]: s.get("size") or 0 for s in data.get("siblings", [])}
    except Exception:  # noqa: BLE001 -- best-effort only
        return {}


def local_path(name: str) -> pathlib.Path | None:
    for p in (labkit.repo_root() / "models").rglob(name):
        if p.is_file():
            return p
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="GGUF quantization sweep (bonus).")
    ap.add_argument("--grid", default=",".join(DEFAULT_GRID),
                    help=f"Comma-separated labels. Available: {','.join(LADDER)}")
    ap.add_argument("--metric", default="tg128", help="tg128 = decode, pp512 = prefill")
    ap.add_argument("--reps", type=int, default=2)
    ap.add_argument("--yes", action="store_true", help="Skip the download-size prompt")
    args = ap.parse_args()

    labels = [l.strip() for l in args.grid.split(",") if l.strip()]
    unknown = [l for l in labels if l not in LADDER]
    if unknown:
        labkit.die(f"Unknown quant label(s): {unknown}", f"Available: {', '.join(LADDER)}")

    sizes = remote_sizes()
    missing = [(l, filename_for(l)) for l in labels if not local_path(filename_for(l))]
    to_download_gb = sum(sizes.get(f, 0) for _, f in missing) / 1024**3

    labkit.banner(f"Quantization sweep: {', '.join(labels)}")
    if missing:
        print(f"  Need to download {len(missing)} file(s), about {to_download_gb:.1f} GB:")
        for label, f in missing:
            print(f"    {label:12s} {sizes.get(f, 0) / 1024**3:5.2f} GB  {f}")
        free_gb = shutil.disk_usage(labkit.repo_root()).free / 1024**3
        print(f"  Free disk: {free_gb:.1f} GB")
        if to_download_gb > free_gb - 2:
            labkit.die("Not enough free disk for this grid.",
                       "Use a smaller --grid, or delete unused GGUFs from models/.")
        if not args.yes and sys.stdin.isatty():
            if input("  Continue? [y/N] ").strip().lower() not in ("y", "yes"):
                print("  Aborted.")
                return 0
    else:
        print("  All requested quantizations are already on disk.")

    from huggingface_hub import hf_hub_download

    models_dir = labkit.repo_root() / "models"
    ngl = labkit.n_gpu_layers()
    threads = labkit.threads()
    is_prefill = args.metric.startswith("pp")
    shape = ["-p", args.metric[2:], "-n", "0"] if is_prefill else ["-p", "0", "-n", "128"]

    rows = []
    for label in labels:
        fname = filename_for(label)
        path = local_path(fname)
        if not path:
            print(f"\n==> Downloading {label}")
            path = pathlib.Path(hf_hub_download(repo_id=labkit.model_repo(), filename=fname,
                                                local_dir=str(models_dir)))
        size_gb = path.stat().st_size / 1024**3
        out = labkit.run_bench(["-m", str(path), "-t", str(threads), "-ngl", str(ngl),
                                *shape, "-r", str(args.reps)])
        tps = labkit.bench_metric(out, args.metric)
        rows.append({"quant": label, "size_gb": round(size_gb, 2), "tok_s": tps})
        print(f"   {label:12s} {size_gb:5.2f} GB   {args.metric} = {tps:7.1f} tok/s")

    if not any(r["tok_s"] for r in rows):
        labkit.die("llama-bench produced no numbers for any quantization.")

    base = next((r for r in rows if r["quant"] == "UD-Q4_K_XL"), rows[0])
    table = labkit.md_table(
        ["Quantization", "Size (GB)", f"{args.metric} (tok/s)", "vs UD-Q4_K_XL", "tok/s per GB"],
        [[r["quant"], f"{r['size_gb']:.2f}", f"{r['tok_s']:.1f}",
          f"{r['tok_s'] / base['tok_s']:.2f}x" if base["tok_s"] else "-",
          f"{r['tok_s'] / r['size_gb']:.1f}" if r["size_gb"] else "-"] for r in rows],
    )

    md = f"""# Bonus - Quantization sweep ({labkit.model_label()}, Unsloth Dynamic ladder)

Host `{labkit.host_tag()}` · llama.cpp `{labkit.LLAMA_CPP_BUILD}` ·
`threads={threads}` `ngl={ngl}` · metric `{args.metric}`

{table}

Decode is memory-bandwidth-bound, so fewer bytes per weight usually means more
tokens per second -- the "tok/s per GB" column shows how much of that you are
actually getting back per gigabyte spent.

Speed is only half the trade. The other half is quality, and no benchmark here
measures it. Serve two of these (`make serve` and
`.venv/bin/python labs/02-serve/serve.py --compare`) and ask each the same three questions
before you claim a winner.

## Your finding (required -- replace this line)

_Which point on this ladder would you actually ship on this machine, and what
made you stop there? Name the quantization where quality broke down for you, if
one did._
"""
    out = labkit.write_report("bonus-quant-sweep.md", md, rows)
    print("\n" + md)
    print(f"==> Wrote {out.relative_to(labkit.repo_root())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
