"""Descarga los precios oficiales de la Comunidad de Madrid y guarda
las estaciones Repsol, Campsa y Petronor con precio de Gasolina 95 E5."""
import json, sys, time, urllib.request
from datetime import datetime, timezone

BASE = ("https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/"
        "PreciosCarburantes/EstacionesTerrestres/")
# zona -> (consulta al Ministerio, municipio al que limitar o None)
ZONES = {
    "madrid":   ("FiltroCCAA/13", None),        # Comunidad de Madrid
    "yecla":    ("FiltroProvincia/30", "YECLA"),  # Yecla (Región de Murcia)
    "alicante": ("FiltroProvincia/03", None),   # Provincia de Alicante
}
BRANDS = ("REPSOL", "CAMPSA", "PETRONOR")


def num(s):
    try:
        v = float(str(s or "").replace(",", "."))
        return v if v > 0 else None
    except ValueError:
        return None


def coord(s):
    try:
        return float(str(s or "").replace(",", "."))
    except ValueError:
        return None


def download(path):
    last = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(BASE + path, headers={
                "Accept": "application/json", "User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(15)
    print(f"::warning::El Ministerio no respondió para {path} ({last}).")
    return None


try:
    with open("data/repsol.json", encoding="utf-8") as f:
        previous = json.load(f).get("stations", [])
except Exception:  # noqa: BLE001
    previous = []

out, fecha = [], ""
for zone, (path, town) in ZONES.items():
    data = download(path)
    if data is None:
        kept = [p for p in previous if p.get("zone", "madrid") == zone]
        print(f"{zone}: se mantienen {len(kept)} estaciones anteriores")
        out += kept
        continue
    fecha = fecha or data.get("Fecha", "")
    n = 0
    for e in data.get("ListaEESSPrecio", []):
        brand = (e.get("Rótulo") or "").strip()
        price = num(e.get("Precio Gasolina 95 E5"))
        muni = (e.get("Municipio") or "").strip()
        if price is None or not any(b in brand.upper() for b in BRANDS):
            continue
        if town and muni.upper() != town:
            continue
        out.append({
            "zone": zone, "id": e.get("IDEESS"), "brand": brand,
            "addr": (e.get("Dirección") or "").strip(), "town": muni,
            "cp": e.get("C.P.") or "", "hours": e.get("Horario") or "",
            "lat": coord(e.get("Latitud")), "lon": coord(e.get("Longitud (WGS84)")),
            "price": price,
        })
        n += 1
    print(f"{zone}: {n} estaciones")

if not out:
    print("::warning::Sin datos. Se mantienen los precios anteriores.")
    sys.exit(0)
if not fecha:
    sys.exit(0)  # nada nuevo que guardar

with open("data/repsol.json", "w", encoding="utf-8") as f:
    json.dump({"fecha": fecha,
               "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "stations": out}, f, ensure_ascii=False, separators=(",", ":"))
print(f"{len(out)} estaciones guardadas")
