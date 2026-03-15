from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
import pypdfium2 as pdfium
import base64, re
from pathlib import Path

source = "./Comprehensive Algorithm Portfolio Evaluation using Item Response.pdf"
chunk_size = 20  # adjust down if still getting OOM warnings
images_dir = Path("output_images")
images_dir.mkdir(exist_ok=True)

pipeline_options = PdfPipelineOptions()
pipeline_options.do_formula_enrichment = True
pipeline_options.generate_picture_images = True
pipeline_options.images_scale = 3.0  # default is 2.0, higher = better quality (72 DPI * 3 = 216 DPI)

pdf = pdfium.PdfDocument(source)
total_pages = len(pdf)
pdf.close()
print(f"Total pages: {total_pages}")

all_md = []
img_counter = 1
for start in range(1, total_pages + 1, chunk_size):
    end = min(start + chunk_size - 1, total_pages)
    print(f"Converting pages {start}-{end}...")
    converter = DocumentConverter(
        format_options={"pdf": PdfFormatOption(pipeline_options=pipeline_options)}
    )
    doc = converter.convert(source, page_range=(start, end)).document

    # Save images
    for p in doc.pictures:
        page = p.prov[0].page_no
        uri = str(p.image.uri)
        b64 = re.sub(r'^data:image/\w+;base64,', '', uri)
        img_path = images_dir / f"page{page}_fig{img_counter}.png"
        img_path.write_bytes(base64.b64decode(b64))
        img_counter += 1

    all_md.append(doc.export_to_markdown())

with open("output.md", "w", encoding="utf-8") as f:
    f.write("\n\n".join(all_md))

print(f"Done! Saved output.md and {img_counter - 1} image(s) to {images_dir}/")
