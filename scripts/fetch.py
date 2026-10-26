"""Descarga los precios oficiales de la Comunidad de Madrid y guarda
las estaciones Repsol, Campsa y Petronor con precio de Gasolina 95 E5."""
import json, sys, time, urllib.request
from datetime import datetime, timezone

URL = ("https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/"
       "PreciosCarburantes/EstacionesTerrestres/FiltroCCAA/13")
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


def download():
    last = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(URL, headers={
                "Accept": "application/json", "User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(15)
    # El Ministerio a veces no responde: se conservan los últimos precios
    # y se termina sin error para no generar avisos por correo.
    print(f"::warning::El Ministerio no respondió ({last}). Se mantienen los precios anteriores.")
    sys.exit(0)


data = download()
out = []
for e in data.get("ListaEESSPrecio", []):
    brand = (e.get("Rótulo") or "").strip()
    price = num(e.get("Precio Gasolina 95 E5"))
    if price is None or not any(b in brand.upper() for b in BRANDS):
        continue
    out.append({
        "id": e.get("IDEESS"), "brand": brand,
        "addr": (e.get("Dirección") or "").strip(),
        "town": (e.get("Municipio") or "").strip(),
        "cp": e.get("C.P.") or "", "hours": e.get("Horario") or "",
        "lat": coord(e.get("Latitud")), "lon": coord(e.get("Longitud (WGS84)")),
        "price": price,
    })

if not out:
    print("::warning::Respuesta vacía. Se mantienen los precios anteriores.")
    sys.exit(0)

with open("data/repsol.json", "w", encoding="utf-8") as f:
    json.dump({"fecha": data.get("Fecha", ""),
               "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "stations": out}, f, ensure_ascii=False, separators=(",", ":"))
print(f"{len(out)} estaciones guardadas")
