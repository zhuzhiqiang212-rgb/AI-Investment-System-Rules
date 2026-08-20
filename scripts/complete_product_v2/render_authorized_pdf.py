from __future__ import annotations

import argparse
import json
from pathlib import Path

from .contracts import load_json, validate_pdf_authorization


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--html",required=True,type=Path)
    parser.add_argument("--model",required=True,type=Path)
    parser.add_argument("--authorization",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    model=load_json(args.model)
    auth=load_json(args.authorization)
    validate_pdf_authorization(auth,model["run_id"])
    if args.output.exists():
        raise RuntimeError("PDF output already exists; one-shot renderer will not overwrite")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page(viewport={"width":1440,"height":1800})
        page.goto(args.html.resolve().as_uri(),wait_until="networkidle")
        page.evaluate("document.querySelectorAll('details').forEach(x=>x.open=true)")
        page.pdf(path=str(args.output),format="A4",print_background=True,prefer_css_page_size=True,margin={"top":"12mm","right":"10mm","bottom":"12mm","left":"10mm"})
        browser.close()
    print(json.dumps({"pdf":str(args.output),"authorization":auth["authorization"]},ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())