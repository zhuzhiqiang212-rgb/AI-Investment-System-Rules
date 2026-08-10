# -*- coding: utf-8 -*-
"""★轮346:任意 HTML → PDF(Edge headless + CDP Page.printToPDF·可控 A4/缩放/横竖·嵌中文字体·不改源HTML)。
Edge CLI 的 --print-to-pdf 不支持 scale/landscape;本脚本走 DevTools 协议(websockets)拿全部打印参数。
用法: python scripts/html_to_pdf.py --html <src.html> --out <dst.pdf> [--landscape] [--scale 0.72] [--margin 0.4]
★渲染到临时再 copy 覆盖目标(避 G 盘 pdfpreview.exe 锁·同 render_daily_pdf 手法)。中文由 Edge 原生嵌入(非Helvetica)。"""
import asyncio, json, subprocess, sys, os, tempfile, time, base64, urllib.request, pathlib, argparse, shutil, socket
import websockets

EDGE_CANDS = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"]


def _free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


async def _print(ws_url, file_url, opts, settle=3.0):
    async with websockets.connect(ws_url, max_size=None) as ws:
        _id = {"n": 0}
        async def cmd(method, params=None):
            _id["n"] += 1; mid = _id["n"]
            await ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
            while True:
                msg = json.loads(await ws.recv())
                if msg.get("id") == mid:
                    if "error" in msg:
                        raise RuntimeError("%s: %s" % (method, msg["error"]))
                    return msg.get("result", {})
        await cmd("Page.enable")
        await cmd("Page.navigate", {"url": file_url})
        await asyncio.sleep(settle)   # 静态HTML·等布局+字体+背景渲染完
        res = await cmd("Page.printToPDF", opts)
        return base64.b64decode(res["data"])


def render(src: pathlib.Path, out: pathlib.Path, landscape=False, scale=1.0, margin=0.4, settle=3.0):
    src = src.resolve(); out = out.resolve()   # ★file URI 需绝对路径
    edge = next((e for e in EDGE_CANDS if pathlib.Path(e).exists()), None)
    if not edge:
        print("[pdf FAIL] 未找到 msedge.exe"); return 5
    if not src.exists():
        print("[pdf FAIL] 源HTML不存在:", src); return 5
    port = _free_port()
    td = tempfile.mkdtemp(prefix="html2pdf_"); udd = os.path.join(td, "udd")
    proc = subprocess.Popen(
        [edge, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
         f"--user-data-dir={udd}", "--allow-file-access-from-files", f"--remote-debugging-port={port}", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        ws_url = None
        for _ in range(40):
            try:
                j = json.loads(urllib.request.urlopen("http://127.0.0.1:%d/json" % port, timeout=2).read())
                pages = [t for t in j if t.get("type") == "page" and t.get("webSocketDebuggerUrl")]
                if pages:
                    ws_url = pages[0]["webSocketDebuggerUrl"]; break
            except Exception:
                pass
            time.sleep(0.5)
        if not ws_url:
            print("[pdf FAIL] Edge 调试端口未就绪(CDP连不上)"); return 5
        opts = {
            "landscape": bool(landscape), "printBackground": True, "scale": float(scale),
            "paperWidth": 8.27, "paperHeight": 11.69,           # A4 英寸
            "marginTop": margin, "marginBottom": margin, "marginLeft": margin, "marginRight": margin,
            "preferCSSPageSize": False,
        }
        data = asyncio.run(_print(ws_url, src.as_uri(), opts, settle=settle))
    finally:
        try:
            proc.terminate(); proc.wait(timeout=10)
        except Exception:
            try:
                subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                               capture_output=True, timeout=20, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            except Exception:
                pass
    if not data or len(data) < 1000:
        print("[pdf FAIL] CDP 未产出有效PDF"); return 5
    tmp_pdf = pathlib.Path(td) / "out.pdf"
    tmp_pdf.write_bytes(data)
    try:
        shutil.copyfile(tmp_pdf, out)
    except (PermissionError, OSError) as e:
        print("[pdf FAIL] 目标被锁写不出(%s: %s)·关闭预览窗格/PDF阅读器·★不杀webview2/GoogleDrive·重跑" % (type(e).__name__, str(e)[:60]))
        return 6
    print("[pdf 出品] %s · bytes=%d · landscape=%s scale=%s margin=%s" % (out.name, out.stat().st_size, landscape, scale, margin))
    return 0


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--landscape", action="store_true")
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--margin", type=float, default=0.4)
    ap.add_argument("--settle", type=float, default=3.0)
    a = ap.parse_args()
    return render(pathlib.Path(a.html), pathlib.Path(a.out), a.landscape, a.scale, a.margin, a.settle)


if __name__ == "__main__":
    raise SystemExit(main())
