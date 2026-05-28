#!/usr/bin/env python3
"""
KOLAI — Kling AI Video Generator
Generates an AI video using Kling V2.6 (or V3.0 fallback) via Replicate.
"""

import argparse
import json
import os
import sys
import time
import mimetypes
from pathlib import Path

import replicate
import requests

# ── Constants ────────────────────────────────────────────────────────────────
CONFIG_FILE = Path(__file__).parent / "config.json"
DEFAULT_CONFIG = {
    "replicate_api_token": "",
    "model": "kwaivgi/kling-v2.6-motion-control",
    "model_fallback": "kling-v3-motion-control",
    "prompt": "A short text prompt controlling motion",
    "steps": 30,
    "scale": 7.5,
    "output_file": "output/output.mp4",
}


# ── Config helpers ────────────────────────────────────────────────────────────

def load_config() -> dict:
    """Load config.json, falling back to defaults for missing keys."""
    cfg = DEFAULT_CONFIG.copy()
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            overrides = json.load(f)
        cfg.update(overrides)
    return cfg


def resolve_token(cfg: dict) -> str:
    """Return API token from env var or config; exit if missing."""
    token = os.environ.get("REPLICATE_API_TOKEN") or cfg.get("replicate_api_token", "")
    if not token or token == "<PUT_TOKEN_HERE>":
        sys.exit(
            "❌  No Replicate API token found.\n"
            "    Set the REPLICATE_API_TOKEN environment variable, or add it to config.json."
        )
    return token


# ── Input helpers ─────────────────────────────────────────────────────────────

def is_url(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


def resolve_input(value: str, label: str):
    """
    Return a file-like object (for local paths) or a plain URL string.
    Replicate's Python client accepts both.
    """
    if is_url(value):
        return value  # pass URL directly to Replicate

    path = Path(value)
    if not path.exists():
        sys.exit(f"❌  {label} file not found: {path}")
    return open(path, "rb")  # caller must close


# ── Model call ────────────────────────────────────────────────────────────────

def run_model(client: replicate.Client, model_id: str, inputs: dict):
    """Run the model and return the output (URL or list of URLs)."""
    print(f"🚀  Running model: {model_id}")
    try:
        output = client.run(model_id, input=inputs)
        return output
    except replicate.exceptions.ReplicateError as exc:
        raise exc


def run_with_fallback(client: replicate.Client, primary: str, fallback: str, inputs: dict):
    """Try primary model; fall back to secondary on error."""
    try:
        return run_model(client, primary, inputs)
    except replicate.exceptions.ReplicateError as exc:
        print(f"⚠️   Primary model failed ({exc}). Trying fallback: {fallback}")
        return run_model(client, fallback, inputs)


# ── Output helpers ────────────────────────────────────────────────────────────

def download_video(url: str, dest: Path) -> None:
    """Stream-download a video URL to dest."""
    print(f"⬇️   Downloading result → {dest}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    print(f"✅  Saved: {dest}")


def confirm_overwrite(dest: Path, force: bool) -> None:
    """Ask the user before overwriting an existing file (unless --force)."""
    if dest.exists() and not force:
        answer = input(f"⚠️   {dest} already exists. Overwrite? [y/N] ").strip().lower()
        if answer != "y":
            sys.exit("Aborted.")


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="KOLAI — Generate AI video with Kling via Replicate"
    )
    parser.add_argument("--image", help="Input image (local path under src/ or URL)")
    parser.add_argument("--video", help="Input video (local path under src/ or URL)")
    parser.add_argument("--prompt", help="Motion-control text prompt")
    parser.add_argument("--model", help="Replicate model ID (overrides config)")
    parser.add_argument("--steps", type=int, help="Inference steps (overrides config)")
    parser.add_argument("--scale", type=float, help="Guidance scale (overrides config)")
    parser.add_argument("--output", help="Output file path (overrides config)")
    parser.add_argument(
        "--force", action="store_true", help="Overwrite output file without confirmation"
    )
    return parser.parse_args()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    args = parse_args()
    cfg = load_config()

    # ── Merge CLI args into config ──
    if args.model:
        cfg["model"] = args.model
    if args.prompt:
        cfg["prompt"] = args.prompt
    if args.steps:
        cfg["steps"] = args.steps
    if args.scale:
        cfg["scale"] = args.scale
    if args.output:
        cfg["output_file"] = args.output

    image_src = args.image or cfg.get("image")
    video_src = args.video or cfg.get("video")

    if not image_src:
        sys.exit("❌  No image provided. Use --image or set 'image' in config.json.")
    if not video_src:
        sys.exit("❌  No video provided. Use --video or set 'video' in config.json.")

    token = resolve_token(cfg)
    dest = Path(cfg["output_file"])

    confirm_overwrite(dest, args.force)

    # ── Resolve inputs ──
    image_input = resolve_input(image_src, "Image")
    video_input = resolve_input(video_src, "Video")

    # ── Build Replicate client ──
    client = replicate.Client(api_token=token)

    # ── Assemble model inputs ──
    model_inputs = {
        "image": image_input,
        "video": video_input,
        "prompt": cfg["prompt"],
        "num_inference_steps": cfg["steps"],
        "guidance_scale": cfg["scale"],
    }

    # ── Run model (with fallback) ──
    try:
        output = run_with_fallback(
            client,
            primary=cfg["model"],
            fallback=cfg["model_fallback"],
            inputs=model_inputs,
        )
    finally:
        # Close any open file handles
        for v in model_inputs.values():
            if hasattr(v, "close"):
                v.close()

    # ── Handle output ──
    # Replicate returns a URL string, a list of URLs, or a FileOutput object
    if isinstance(output, list):
        output_url = str(output[0])
    elif hasattr(output, "url"):
        output_url = output.url
    else:
        output_url = str(output)

    if not output_url:
        sys.exit("❌  Model returned no output. Check your inputs and model parameters.")

    download_video(output_url, dest)


if __name__ == "__main__":
    main()
