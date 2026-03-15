import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

SLIDES_DIR = Path("slides")
SLIDES_DIR.mkdir(exist_ok=True)

scenes = json.load(open("Opus4.6_60cusd.json", encoding="utf-8"))["scenes"]


def build_html(scene: dict) -> str:
    title = scene["title"]
    section = scene["section"]
    key_points = scene.get("key_points", [])
    formulas = scene.get("formulas", [])
    images = scene.get("images", [])

    bullets_html = "".join(f"<li>{p}</li>" for p in key_points)

    formulas_html = ""
    if formulas:
        formulas_html = '<div class="formulas">' + "".join(
            f'<div class="formula">\\({f}\\)</div>' for f in formulas
        ) + "</div>"

    # Shrink images more aggressively when there are multiple or combined with formulas
    has_formulas = bool(formulas)
    n_images = len(images)
    if n_images == 0:
        img_max_h = 0
    elif n_images == 1 and not has_formulas:
        img_max_h = 600
    elif n_images == 1 and has_formulas:
        img_max_h = 380
    else:
        img_max_h = 280 if not has_formulas else 220

    images_html = ""
    if images:
        imgs = "".join(
            f'<img src="../output_images/{img}" alt="{img}" style="max-height:{img_max_h}px">'
            for img in images
        )
        images_html = f'<div class="images">{imgs}</div>'

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    width: 1920px; height: 1080px; overflow: hidden;
    background: #0f1117;
    color: #e8eaf0;
    font-family: 'Segoe UI', Arial, sans-serif;
    display: flex;
    flex-direction: column;
    padding: 60px 80px;
  }}
  .section-label {{
    font-size: 22px;
    color: #7c8ba1;
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-bottom: 18px;
  }}
  h1 {{
    font-size: 56px;
    font-weight: 700;
    color: #ffffff;
    line-height: 1.15;
    margin-bottom: 40px;
    border-left: 6px solid #4f8ef7;
    padding-left: 24px;
  }}
  .content {{
    display: flex;
    flex: 1;
    gap: 60px;
    align-items: flex-start;
  }}
  .left {{ flex: 1; }}
  .right {{
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 20px;
    overflow: hidden;
    max-height: 780px;
  }}
  ul {{
    list-style: none;
    display: flex;
    flex-direction: column;
    gap: 20px;
  }}
  li {{
    font-size: 30px;
    line-height: 1.4;
    padding-left: 28px;
    position: relative;
    color: #d0d8e8;
  }}
  li::before {{
    content: '▸';
    position: absolute;
    left: 0;
    color: #4f8ef7;
  }}
  .formulas {{
    background: #1a1f2e;
    border: 1px solid #2e3650;
    border-radius: 10px;
    padding: 20px 26px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    flex-shrink: 0;
  }}
  .formula {{
    font-size: 24px;
    color: #c8d8f8;
    text-align: center;
    overflow: hidden;
  }}
  .images {{
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    justify-content: center;
    align-items: flex-start;
    overflow: hidden;
    flex: 1;
  }}
  .images img {{
    border-radius: 8px;
    border: 1px solid #2e3650;
    object-fit: contain;
    max-width: calc(50% - 8px);
  }}
</style>
<script>
  window.MathJax = {{
    tex: {{
      inlineMath: [['\\\\(', '\\\\)']],
      packages: {{'[+]': ['noerrors']}}
    }},
    options: {{ ignoreHtmlClass: 'no-mathjax' }},
    loader: {{ load: ['[tex]/noerrors'] }},
    startup: {{ ready() {{ MathJax.startup.defaultReady(); }} }}
  }};
</script>
<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"></script>
</head>
<body>
  <div class="section-label">{section}</div>
  <h1>{title}</h1>
  <div class="content">
    <div class="left">
      <ul>{bullets_html}</ul>
    </div>
    <div class="right">
      {formulas_html}
      {images_html}
    </div>
  </div>
</body>
</html>"""


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1920, "height": 1080})

    for i, scene in enumerate(scenes):
        html = build_html(scene)
        tmp = SLIDES_DIR / f"_tmp_{i:03d}.html"
        tmp.write_text(html, encoding="utf-8")

        page.goto(f"file:///{tmp.resolve().as_posix()}")
        # Wait for MathJax to finish rendering
        page.wait_for_function("typeof MathJax !== 'undefined' && MathJax.startup && MathJax.startup.promise", timeout=10000)
        page.wait_for_function("MathJax.startup.promise.then(() => true)", timeout=10000)
        time.sleep(0.3)  # small buffer for fonts/images

        out = SLIDES_DIR / f"slide_{i+1:03d}.png"
        page.screenshot(path=str(out), full_page=False)
        tmp.unlink()
        print(f"[{i+1}/{len(scenes)}] {out.name} — {scene['title']}")

    browser.close()

print(f"\nDone! {len(scenes)} slides saved to slides/")
