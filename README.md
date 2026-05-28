# KOLAI — Kling AI Video Generator

Generate AI-controlled videos using **Kling V3** (with automatic **V2.6 fallback**) via the [Replicate](https://replicate.com) API.  
Provide an input image and a reference video; KOLAI sends them to the model and saves the result to `output/output.mp4`.

---

## Project structure

```
kolai/
├── generate.py       # Main CLI script
├── requirements.txt  # Pinned dependencies
├── config.json       # Default settings & API token placeholder
├── generate.yml      # Sample run config / CI reference
├── src/              # Put your local input files here
│   ├── image.jpg     # (example) input image
│   └── video.mp4     # (example) reference video
└── output/           # Generated video is saved here
    └── output.mp4    # (created on first run)
```

---

## Setup

### 1. Install dependencies

Requires **Python 3.10+**.

```bash
pip install -r requirements.txt
```

### 2. Set your Replicate API token

**Option A — environment variable (recommended):**

```bash
export REPLICATE_API_TOKEN=r8_xxxxxxxxxxxxxxxxxxxx
```

**Option B — config.json:**

Edit `config.json` and replace `<PUT_TOKEN_HERE>` with your token:

```json
{
  "replicate_api_token": "r8_xxxxxxxxxxxxxxxxxxxx"
}
```

> Get your token at <https://replicate.com/account/api-tokens>

### 3. Add your input files

Drop your image and reference video into the `src/` directory:

```
src/image.jpg
src/video.mp4
```

Alternatively, you can pass public URLs directly via CLI flags.

---

## Usage

### Basic run (using files in `src/`)

```bash
python generate.py --image src/image.jpg --video src/video.mp4
```

### With a custom prompt

```bash
python generate.py \
  --image src/image.jpg \
  --video src/video.mp4 \
  --prompt "Camera slowly zooms in while the subject walks forward"
```

### Using URLs instead of local files

```bash
python generate.py \
  --image https://example.com/photo.jpg \
  --video https://example.com/reference.mp4
```

### All available flags

| Flag | Description | Default |
|------|-------------|---------|
| `--image` | Input image (path or URL) | `config.json → image` |
| `--video` | Reference video (path or URL) | `config.json → video` |
| `--prompt` | Motion-control text prompt | `config.json → prompt` |
| `--model` | Replicate model ID | `kwaivgi/kling-v3-motion-control` |
| `--steps` | Inference steps | `30` |
| `--scale` | Guidance scale | `7.5` |
| `--output` | Output file path | `output/output.mp4` |
| `--force` | Overwrite output without confirmation | `false` |

---

## Model selection & fallback

By default KOLAI uses **Kling V3**:

```
kwaivgi/kling-v3-motion-control
```

If V3 is unavailable (e.g. the model is not yet public on your Replicate account), it automatically retries with **Kling V2.6**:

```
kwaivgi/kling-2.6
```

You can change either model in `config.json`:

```json
{
  "model": "kwaivgi/kling-v3-motion-control",
  "model_fallback": "kwaivgi/kling-2.6"
}
```

Or override the primary model at runtime:

```bash
python generate.py --model kwaivgi/kling-2.6 --image src/image.jpg --video src/video.mp4
```

---

## Output

The generated video is saved to `output/output.mp4` by default.  
If the file already exists, you will be prompted before it is overwritten (use `--force` to skip).

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `No Replicate API token found` | Set `REPLICATE_API_TOKEN` env var or add token to `config.json` |
| `Image/Video file not found` | Check the path exists under `src/`; confirm spelling |
| `Primary model failed` | V3 may be unavailable — fallback to V2.6 runs automatically |
| HTTP 401 from Replicate | Your token is invalid or expired |
| Output video is empty / corrupt | Check model logs at <https://replicate.com/runs> |
