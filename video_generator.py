import json
import pyttsx3
from pathlib import Path
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
from moviepy.video.fx import FadeIn, FadeOut

AUDIO_DIR = Path("audio")
AUDIO_DIR.mkdir(exist_ok=True)
SLIDES_DIR = Path("slides")

scenes = json.load(open("Opus4.6_60cusd.json", encoding="utf-8"))["scenes"]

VOICE = "ZIRA"       # ZIRA = female, DAVID = male
FADE_DURATION = 0.5  # seconds for fade in/out

# --- Stage 1: Generate audio ---

print("=== Stage 1: Text to Speech ===")

engine = pyttsx3.init()
voices = engine.getProperty("voices")
selected = next((v for v in voices if VOICE in v.id), voices[0])
engine.setProperty("voice", selected.id)
engine.setProperty("rate", 175)   # words per minute (default ~200)
engine.setProperty("volume", 1.0)

for i, scene in enumerate(scenes):
    out = AUDIO_DIR / f"scene_{i+1:03d}.wav"
    if out.exists():
        print(f"[{i+1}/{len(scenes)}] Skipping (exists): {out.name}")
        continue
    print(f"[{i+1}/{len(scenes)}] Generating audio: {scene['title']}")
    engine.save_to_file(scene["narration"], str(out))

engine.runAndWait()

# --- Stage 2: Assemble video ---

print("\n=== Stage 2: Assembling video ===")
clips = []

for i, scene in enumerate(scenes):
    slide_path = SLIDES_DIR / f"slide_{i+1:03d}.png"
    audio_path = AUDIO_DIR / f"scene_{i+1:03d}.wav"

    if not slide_path.exists():
        print(f"  WARNING: missing {slide_path.name}, skipping")
        continue
    if not audio_path.exists():
        print(f"  WARNING: missing {audio_path.name}, skipping")
        continue

    audio = AudioFileClip(str(audio_path))
    clip = (
        ImageClip(str(slide_path))
        .with_duration(audio.duration)
        .with_audio(audio)
        .with_effects([FadeIn(FADE_DURATION), FadeOut(FADE_DURATION)])
    )
    clips.append(clip)
    print(f"[{i+1}/{len(scenes)}] {slide_path.name} — {audio.duration:.1f}s")

print(f"\nConcatenating {len(clips)} clips...")
final = concatenate_videoclips(clips, method="chain")

print("Rendering output.mp4...")
final.write_videofile(
    "output.mp4",
    fps=10,
    codec="h264_nvenc",
    audio_codec="aac",
    logger="bar"
)

print("\nDone! output.mp4")
