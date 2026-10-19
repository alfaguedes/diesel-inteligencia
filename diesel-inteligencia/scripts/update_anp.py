#!/usr/bin/env python3
"""Fetch the latest ANP open CSV for Diesel S10/S500 and update public JSON.

The ANP page is the source of truth. This script discovers the newest diesel/GNV CSV
link from the official page instead of hard-coding a monthly filename.
"""
from __future__ import annotations
import csv, hashlib, io, json, re, sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

PAGE = "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/serie-historica-de-precos-de-combustiveis"
OUT = Path("data")
ARCHIVE = OUT / "archive"
UA = "DieselInteligencia/1.0 (open-data updater)"
MONTH_RE = re.compile(r"(?P<year>20\d{2})[-.](?P<month>0[1-9]|1[0-2])")

def get(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=60) as resp:
        return resp.read()

def discover_csv(page: str) -> tuple[str, str]:
    html = get(page).decode("utf-8", errors="replace")
    # ANP links look like .../2026/09-dados-abertos-precos-2026-09-diesel-gnv.csv
    links = re.findall(r"""href=["']([^"']+\.csv(?:\?[^"']*)?)["']""", html, flags=re.I)
    candidates = []
    for raw in links:
        url = urljoin(page, raw.replace("&amp;", "&"))
        name = url.rsplit("/", 1)[-1].lower()
        if "diesel" not in name or "gnv" not in name:
            continue
        m = MONTH_RE.search(name)
        if m:
            candidates.append((int(m.group("year")), int(m.group("month")), url, name))
    if not candidates:
        raise RuntimeError("Não encontrei link CSV de Diesel/GNV na página oficial da ANP. Nenhum dado foi sobrescrito.")
    candidates.sort()
    _, _, url, name = candidates[-1]
    return url, name

def clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").replace("\ufeff", "")).strip()

def norm(s: str) -> str:
    return clean(s).casefold()

def normalize_date(raw: str) -> str:
    raw = clean(raw)
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            pass
    return raw

def parse_price(raw: str) -> float | None:
    raw = clean(raw).replace("R$", "").replace(" ", "")
    if not raw:
        return None
    # Brazilian CSV usually uses decimal comma. Handle either comma or decimal dot.
    if "," in raw:
        raw = raw.replace(".", "").replace(",", ".")
    try:
        value = float(raw)
        return value if value > 0 else None
    except ValueError:
        return None

def parse_csv(blob: bytes) -> list[dict]:
    # ANP files have appeared in UTF-8 and Windows-1252 depending on the publication.
    text = None
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = blob.decode(enc)
            break
        except UnicodeDecodeError:
            pass
    if text is None:
        raise RuntimeError("Não foi possível decodificar o CSV da ANP.")
    sample = text[:10000]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,\\t")
    except csv.Error:
        dialect = csv.excel
        dialect.delimiter = ";"
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    if not reader.fieldnames:
        raise RuntimeError("CSV oficial sem cabeçalhos.")
    fields = {norm(f): f for f in reader.fieldnames if f}
    def find(*parts):
        for normalized, original in fields.items():
            if all(part in normalized for part in parts):
                return original
        return None
    product_col = find("produto")
    price_col = find("valor de venda") or find("preco de venda")
    date_col = find("data da coleta") or find("data coleta")
    state_col = find("estado", "sigla")
    city_col = find("municipio") or find("município")
    seller_col = find("revenda")
    brand_col = find("bandeira")
    if not all((product_col, price_col, state_col, city_col)):
        raise RuntimeError("Cabeçalhos não reconhecidos no CSV ANP: " + ", ".join(reader.fieldnames))
    output = []
    for row in reader:
        prod = clean(row.get(product_col, "")).upper()
        if "DIESEL" not in prod:
            continue
        if "S-10" in prod or "S10" in prod:
            product = "DIESEL S10"
        elif "S-500" in prod or "S500" in prod:
            product = "DIESEL S500"
        else:
            continue
        price = parse_price(row.get(price_col, ""))
        if price is None:
            continue
        output.append({
            "date": normalize_date(row.get(date_col, "")) if date_col else "",
            "state": clean(row.get(state_col, "")).upper(),
            "city": clean(row.get(city_col, "")),
            "seller": clean(row.get(seller_col, "")) if seller_col else "",
            "product": product,
            "price": round(price, 3),
            "source": "ANP",
            "brand": clean(row.get(brand_col, "")) if brand_col else ""
        })
    if not output:
        raise RuntimeError("CSV foi baixado, mas nenhum registro S10/S500 válido foi encontrado. Dados anteriores foram preservados.")
    return output

def main():
    OUT.mkdir(exist_ok=True)
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    page_bytes = get(PAGE)
    html = page_bytes.decode("utf-8", errors="replace")
    links = re.findall(r"""href=["']([^"']+\.csv(?:\?[^"']*)?)["']""", html, flags=re.I)
    candidates = []
    for raw in links:
        url = urljoin(PAGE, raw.replace("&amp;", "&"))
        name = url.rsplit("/", 1)[-1].lower()
        if "diesel" in name and "gnv" in name:
            m = MONTH_RE.search(name)
            if m: candidates.append((int(m.group("year")), int(m.group("month")), url, name))
    if not candidates:
        raise RuntimeError("Nenhum CSV mensal de Diesel/GNV encontrado na página oficial.")
    candidates.sort()
    year, month, url, filename = candidates[-1]
    blob = get(url)
    digest = hashlib.sha256(blob).hexdigest()
    records = parse_csv(blob)
    archive_file = ARCHIVE / f"{year:04d}-{month:02d}.json"
    payload = {
        "meta": {
            "source": "Agência Nacional do Petróleo, Gás Natural e Biocombustíveis (ANP)",
            "source_url": url,
            "source_page": PAGE,
            "source_file": filename,
            "source_sha256": digest,
            "reference_month": f"{year:04d}-{month:02d}",
            "checked_at_utc": now,
            "record_count": len(records),
            "note": "Levantamento oficial de revenda; a pesquisa é semanal. A verificação automática diária não implica publicação diária."
        },
        "records": records
    }
    # Save a month-specific snapshot. Re-running a check updates that month only if ANP changes it.
    archive_file.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    # Combine month archives to retain history. Latest source file is discovered each run.
    all_records = []
    archive_meta = []
    for path in sorted(ARCHIVE.glob("????-??.json")):
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
            all_records.extend(item.get("records", []))
            if item.get("meta"):
                archive_meta.append(item["meta"])
        except (json.JSONDecodeError, OSError):
            continue
    combined = {
        "meta": {
            **payload["meta"],
            "archive_months": len(archive_meta),
            "combined_record_count": len(all_records),
            "checked_at_utc": now
        },
        "records": all_records
    }
    (OUT / "prices.json").write_text(json.dumps(combined, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (OUT / "status.json").write_text(json.dumps({
        "checked_at_utc": now,
        "source_url": url,
        "source_file": filename,
        "source_sha256": digest,
        "record_count": len(records),
        "archive_months": len(archive_meta),
        "status": "success"
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"ANP: {filename}; {len(records)} registros; histórico com {len(archive_meta)} mês(es).")
if __name__ == "__main__":
    main()
