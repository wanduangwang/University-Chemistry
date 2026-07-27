"""Parse a single local PDF via MinerU online v4 API -> full.md + images/ + JSON.

Follows the verified local-file flow from the mineru-pdf-parse skill, WITH the
project-manual's critical 403 fix (manual SSP handbook $9): the OSS pre-signed
upload URL is signed with an EMPTY Content-Type, so the PUT must send an empty
Content-Type header, otherwise it fails with 403 SignatureDoesNotMatch. We default
to empty and fall back to application/pdf on 403.

Usage:
  python mineru/parse_pdf.py --pdf mineru/output_pdfs/p1-ch01-energy.pdf --name p1-ch01-energy
"""
import os, sys, json, uuid, time, zipfile, io, argparse
import urllib.request, urllib.error

API = "https://mineru.net"


def load_token():
    here = os.path.dirname(os.path.abspath(__file__))
    token = os.environ.get("MINERU_TOKEN")
    envpath = os.path.join(here, ".env")
    if not token and os.path.exists(envpath):
        with open(envpath) as f:
            for line in f:
                line = line.strip()
                if line.startswith("MINERU_TOKEN"):
                    token = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not token:
        raise SystemExit("MINERU_TOKEN not found in env or mineru/.env")
    return token


def api(method, url, token=None, data=None, headers=None, raw=False):
    req = urllib.request.Request(url, data=data, method=method)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            body = r.read()
    except urllib.error.HTTPError as e:
        sys.stderr.write(f"HTTPError {e.code}: {e.read().decode('utf-8','ignore')[:600]}\n")
        raise
    return body if raw else json.loads(body.decode("utf-8"))


def find_key(obj, key):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key:
                return v
            r = find_key(v, key)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for it in obj:
            r = find_key(it, key)
            if r is not None:
                return r
    return None


def parse(pdf_path, name, out_root):
    token = load_token()
    fn = os.path.basename(pdf_path)
    data_id = str(uuid.uuid4())
    body = json.dumps({"files": [{"name": fn, "data_id": data_id}], "model_version": "vlm"}).encode()
    resp = api("POST", f"{API}/api/v4/file-urls/batch", token=token, data=body,
               headers={"Content-Type": "application/json"})
    data = resp.get("data", resp)
    batch_id = data.get("batch_id") or find_key(resp, "batch_id")
    file_urls = data.get("file_urls") or find_key(resp, "file_urls")
    if not file_urls:
        raise SystemExit("no file_urls in batch response")
    print(f"[batch] batch_id={batch_id}")
    upload_url = file_urls[0]

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    print(f"[upload] {len(pdf_bytes)} bytes -> OSS presigned URL")

    # Manual $9: empty Content-Type required; fall back to application/pdf on 403.
    for ctype in ("", "application/pdf"):
        req = urllib.request.Request(upload_url, data=pdf_bytes, method="PUT")
        req.add_header("Content-Type", ctype)
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                print(f"[upload] PUT ok (Content-Type='{ctype}') status={r.status}")
            break
        except urllib.error.HTTPError as e:
            if e.code == 403 and ctype == "":
                print("[upload] 403 with empty Content-Type, retrying with application/pdf")
                continue
            raise

    # Poll
    while True:
        time.sleep(15)
        res = api("GET", f"{API}/api/v4/extract-results/batch/{batch_id}", token=token)
        items = find_key(res, "extract_result")
        states = [it.get("state") for it in items] if isinstance(items, list) else []
        print(f"[poll] states={states}")
        if states and all(s == "done" for s in states):
            break
        if any(s == "failed" for s in states):
            raise SystemExit("MinerU extract failed")

    zip_url = find_key(res, "full_zip_url")
    if not zip_url:
        raise SystemExit("no full_zip_url in result")
    print(f"[download] {zip_url[:80]}...")
    zbytes = api("GET", zip_url, raw=True)
    out_dir = os.path.join(out_root, name)
    os.makedirs(out_dir, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(zbytes)) as z:
        z.extractall(out_dir)
    print(f"[done] extracted {len(z.namelist())} entries -> {out_dir}")
    return out_dir


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    out = args.out or os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    parse(args.pdf, args.name, out)
