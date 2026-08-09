# -*- coding: utf-8 -*-
"""★轮82 AV4:把当日HTML产品渲成唯一入口PDF(00_今日日报.pdf)·同run_id·写 .pdf.runid 边车。
Edge headless print-to-pdf → 临时 → copy覆盖canonical(避pdfpreview.exe锁)。"""
import sys, subprocess, shutil, argparse, pathlib, tempfile, time, os, re
ROOT = pathlib.Path(__file__).resolve().parent.parent
SEE = ROOT / "00_请先看这里"
EDGE_CANDS = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"]


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", required=True); ap.add_argument("--run-id", required=True)
    ap.add_argument("--force", action="store_true", help="★轮95 NA5:董事长明令本轮出PDF·绕完工度守卫(未完工仍出·但HTML/PDF同run_id)")
    a = ap.parse_args()
    src = SEE / a.html
    if not src.exists():
        print("[pdf FAIL] 源HTML不存在:", src); return 5
    # ★轮83 AW4:完工度未全满足→不进 00_今日日报.pdf(董事长2026-08-02:机器装好前不交产品)
    import json as _json
    _m = re.search(r"(\d{8})", a.html) or re.search(r"(\d{4}-\d{2}-\d{2})", a.html)
    _dc = _m.group(1).replace("-", "") if _m else ""
    _csp = ROOT / "data" / "logs" / f"completion_status_{_dc}.json"
    # ★轮100 NG0/NG4:判据分离——机器完工判据不再拦产品交付·PDF是董事长唯一入口·【必须出】(缺项在产品内局部标注·不整体否定)。
    if _csp.exists():
        _cs = _json.loads(_csp.read_text(encoding="utf-8"))
        print("[pdf NG4] 正式产品出PDF(判据分离·完工度实情=%s·缺项已在产品内局部标注)" % _cs.get("★页头串", "?"))
    edge = next((e for e in EDGE_CANDS if pathlib.Path(e).exists()), None)
    if not edge:
        print("[pdf FAIL] 未找到 msedge.exe"); return 5
    td = tempfile.mkdtemp(prefix="dailypdf_")
    tmp_pdf = os.path.join(td, "daily.pdf"); udd = os.path.join(td, "udd")
    url = src.as_uri()
    cmd = [edge, "--headless", "--disable-gpu", "--no-first-run", f"--user-data-dir={udd}",
           "--allow-file-access-from-files", "--no-pdf-header-footer",
           f"--print-to-pdf={tmp_pdf}", url]
    try:
        subprocess.run(cmd, timeout=280, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        pass
    # 轮询等文件落盘
    for _ in range(20):
        if os.path.exists(tmp_pdf) and os.path.getsize(tmp_pdf) > 1000:
            break
        time.sleep(1)
    if not (os.path.exists(tmp_pdf) and os.path.getsize(tmp_pdf) > 1000):
        print("[pdf FAIL] Edge未产出PDF(headless渲染失败·如实报未生成)"); return 5
    dst = SEE / "00_今日日报.pdf"
    try:
        shutil.copyfile(tmp_pdf, dst)
    except (PermissionError, OSError) as e:
        # ★★轮128 PH2-1:canonical被锁→自动降级出【新文件名】PDF·★台账记原因·★不跳过·★不假报「已覆盖」。
        _dh = a.html.replace(".html", "").replace("★每日产品_", "") or "unknown"
        _rid = re.sub(r"[^0-9A-Za-z-]", "", a.run_id)
        alt = SEE / ("★每日产品PDF_管道版_%s_%s.pdf" % (_dh, _rid))
        try:
            shutil.copyfile(tmp_pdf, alt)
        except Exception as e2:
            print("[pdf FAIL] canonical被锁·新文件名也写不出:", e2); return 5
        note = {"canonical未覆盖": True, "原因": "canonical 00_今日日报.pdf 被锁(%s: %s)" % (type(e).__name__, str(e)[:60]),
                "★降级真出": alt.name, "run_id": a.run_id, "as_of": time.strftime("%Y-%m-%d %H:%M:%S"),
                "★解锁步骤": "关闭预览窗格/PDF阅读器→★不杀msedgewebview2/GoogleDriveFS(掉G盘)→重跑render_daily_pdf"}
        _fp = ROOT / "data" / "logs" / ("pdf_fallback_%s.json" % _dc)
        _fp.parent.mkdir(parents=True, exist_ok=True); _fp.write_text(_json.dumps(note, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[pdf 降级·PH2] ★canonical被锁·未覆盖(★不假报)→真出新文件名 %s · 台账记原因 %s" % (alt.name, _fp.name))
        print("  ★解锁:关预览窗格/PDF阅读器·★不杀webview2/GoogleDrive·重跑")
        return 6   # ★降级码:PDF真出但canonical未覆盖(非失败·非假报)
    # 边车(canonical覆盖成功才写·否则不冒充新轮)
    sys.path.insert(0, str(ROOT / "scripts"))
    import product_manifest as pm
    pm.write_pdf_runid(a.run_id)
    ok, msg = pm.check_pdf_html_same_run(a.run_id)
    print("[pdf 出品] 00_今日日报.pdf bytes=%d · run_id=%s" % (dst.stat().st_size, a.run_id))
    print("  同轮校验:", msg)
    return 0 if ok else 5


if __name__ == "__main__":
    raise SystemExit(main())
