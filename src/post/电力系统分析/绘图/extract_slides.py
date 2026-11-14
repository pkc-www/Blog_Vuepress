"""Extract the selected original slides used in Lectures 9-12.

Usage: python extract_slides.py --pdf-dir PATH
Put the four PDFs in PATH as 9.pdf, 10.pdf, 11.pdf, and 12.pdf.
Requires PyMuPDF. Page numbers are one-based PDF pages, equal to the
printed slide numbers for these selected pages. No PDF is modified.
"""
from pathlib import Path
import argparse
import json
import fitz

ROOT = Path(__file__).resolve().parents[1]
SLIDES = {
    9: [(3, 'polar-equations'), (5, 'scaled-correction'),
        (6, 'polar-jacobian-h'), (7, 'polar-jacobian-nml'),
        (10, 'pq-decoupling'), (12, 'diagonal-approximation'),
        (14, 'voltage-factorization'), (15, 'pq-constant-matrices'),
        (17, 'pq-iteration'), (19, 'two-bus-case'),
        (20, 'two-bus-y'), (21, 'two-bus-equations'),
        (22, 'two-bus-pv-conversion'), (25, 'four-bus-first-iteration'),
        (29, 'four-bus-converged')],
    10: [(6, 'voltage-deviation-course-table'), (9, 'qu-characteristic'),
         (10, 'qu-balance'), (13, 'local-reactive-balance'),
         (14, 'generator-pq-capability'), (16, 'synchronous-machine-states'),
         (19, 'shunt-capacitor'), (21, 'svc-structure'),
         (24, 'line-charging-reactive-power'), (27, 'pilot-node-relation'),
         (29, 'pilot-voltage-strategies'), (32, 'avc-pilot-case'),
         (34, 'voltage-regulation-principle'), (37, 'tap-changer'),
         (39, 'regulating-transformer'), (41, 'series-shunt-comparison')],
    11: [(6, 'frequency-power-balance'), (9, 'load-frequency-characteristic'),
         (11, 'hydraulic-governor'), (13, 'primary-steady-state'),
         (15, 'secondary-steady-state'), (17, 'primary-balance-geometry'),
         (19, 'secondary-balance-geometry'), (23, 'three-frequency-controls'),
         (25, 'generator-frequency-coefficient'), (26, 'aggregate-droop'),
         (27, 'system-frequency-coefficient'), (29, 'low-inertia'),
         (30, 'agc-architecture')],
    12: [(10, 'seasonal-load-allocation'), (12, 'incremental-cost'),
         (13, 'quadratic-cost'), (14, 'economic-dispatch-model'),
         (16, 'dispatch-and-power-flow'), (18, 'equal-ic-derivation'),
         (20, 'equal-ic-exchange-proof'), (21, 'two-generator-ed'),
         (23, 'ed-bounds'), (24, 'ed-bound-sequence'),
         (27, 'loss-penalty-factor'), (28, 'loss-ed-case'),
         (29, 'loss-ed-original-result')],
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdf-dir', type=Path, required=True)
    args = parser.parse_args()
    output = ROOT / '图片'
    output.mkdir(exist_ok=True)
    records = []
    index = 74
    for lecture, selection in SLIDES.items():
        with fitz.open(args.pdf_dir / f'{lecture}.pdf') as doc:
            for page, label in selection:
                filename = f'{index:02}-{label}.png'
                slide = doc[page - 1]
                scale = 1920 / slide.rect.width
                slide.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False).save(output / filename)
                records.append({'image': filename, 'lecture': lecture,
                                'pdf_page': page, 'printed_page': page})
                index += 1
    (Path(__file__).parent / 'slide_sources.json').write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Extracted {len(records)} slides, image numbers 74-{index-1}.')


if __name__ == '__main__':
    main()
