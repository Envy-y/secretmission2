import anthropic
import argparse
import json
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
from pydantic import BaseModel
from typing import List

# --- Args ---

parser = argparse.ArgumentParser()
parser.add_argument("--model", default="claude-opus-4-6",
    choices=["claude-opus-4-6", "claude-sonnet-4-6", "claude-haiku-4-5"],
    help="Model to use (default: claude-opus-4-6)")
parser.add_argument("--thinking", default="adaptive",
    choices=["adaptive", "none"],
    help="Thinking mode: 'adaptive' or 'none' (default: adaptive)")
args = parser.parse_args()

# --- Schema ---

class Scene(BaseModel):
    title: str           # Short slide title, e.g. "What is IRT?"
    section: str         # Parent section from the paper
    key_points: List[str]  # 3-5 bullet points for the slide
    formulas: List[str]  # LaTeX formulas relevant to this slide (empty list if none)
    images: List[str]    # Image filenames from output_images/ (empty list if none)
    narration: str       # Full spoken narration for this slide (~3-5 sentences)

class ScenesOutput(BaseModel):
    scenes: List[Scene]

def strict_schema(model):
    """Add additionalProperties: false to all objects in a Pydantic schema."""
    def patch(obj):
        if isinstance(obj, dict):
            if obj.get("type") == "object":
                obj["additionalProperties"] = False
            for v in obj.values():
                patch(v)
        elif isinstance(obj, list):
            for item in obj:
                patch(item)
    schema = model.model_json_schema()
    patch(schema)
    return schema

# --- Load inputs ---

markdown = Path("output.md").read_text(encoding="utf-8")
images = sorted(Path("output_images").glob("*.png"))
image_list = "\n".join(f"- {img.name} (page {img.stem.split('_')[0].replace('page','')})" for img in images)

# Estimate a sensible slide count: ~1 slide per 350 words, capped at 60
word_count = len(markdown.split())
target_slides = max(8, min(40, round(word_count / 350)))
print(f"Paper word count: {word_count} → target slides: {target_slides}")

# --- Prompt ---

prompt = f"""You are an expert at turning academic papers into engaging educational video scripts.

Below is the full text of an academic paper converted to markdown, followed by a list of extracted figures.

Your task is to break the paper into slides for an educational video. Follow these rules:
- One small, focused topic per slide — if a section covers multiple concepts, make multiple slides
- Each slide should be self-contained and understandable on its own
- key_points: 3-5 concise bullet points (not full sentences, just clear phrases)
- formulas: include any LaTeX formulas (as-is from the markdown) that are central to this slide's topic
- images: reference image filenames ONLY if the figure is directly relevant to this slide's topic
- narration: write as if a lecturer is explaining this to a student — clear, plain English, ~3-5 sentences. Explain any formulas in plain English.
- Aim for approximately {target_slides} slides (this paper has {word_count} words — adjust if some sections are denser or lighter than others)

Available figures:
{image_list}

---
PAPER MARKDOWN:
{markdown}
"""

# --- Call Claude ---

client = anthropic.Anthropic()

thinking_param = {"type": "adaptive"} if args.thinking == "adaptive" else None
print(f"Generating scenes with {args.model}, thinking={args.thinking}...")

stream_kwargs = dict(
    model=args.model,
    max_tokens=32000,
    messages=[{"role": "user", "content": prompt}],
    output_config={"format": {"type": "json_schema", "schema": strict_schema(ScenesOutput)}}
)
if thinking_param:
    stream_kwargs["thinking"] = thinking_param

with client.messages.stream(**stream_kwargs) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
    final = stream.get_final_message()

# --- Parse and save ---

raw = next(b.text for b in final.content if b.type == "text")
scenes_data = ScenesOutput.model_validate_json(raw)

output = {"scenes": [s.model_dump() for s in scenes_data.scenes]}
Path("scenes.json").write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

print(f"\n\nDone! Generated {len(scenes_data.scenes)} scenes → scenes.json")
