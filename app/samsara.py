import os
import requests

SAMSARA_BASE_URL = "https://api.samsara.com"
TIMEOUT_SEGUNDOS = 20


def _headers() -> dict:
    token = os.getenv("SAMSARA_API_TOKEN")
    if not token:
        raise RuntimeError("No está configurada la variable de entorno SAMSARA_API_TOKEN en el servidor.")
    return {"Authorization": f"Bearer {token}"}


def listar_vehiculos() -> list[dict]:
    vehiculos = []
    url = f"{SAMSARA_BASE_URL}/fleet/vehicles"
    params = {"limit": 512}
    while url:
        resp = requests.get(url, headers=_headers(), params=params, timeout=TIMEOUT_SEGUNDOS)
        resp.raise_for_status()
        payload = resp.json()
        for v in payload.get("data", []):
            vehiculos.append({"id": v.get("id"), "name": v.get("name")})
        cursor = payload.get("pagination", {}).get("endCursor")
        has_next = payload.get("pagination", {}).get("hasNextPage")
        if has_next and cursor:
            params = {"limit": 512, "after": cursor}
        else:
            url = None
    return vehiculos


def obtener_odometros(vehicle_ids: list[str]) -> dict:
    if not vehicle_ids:
        return {}
    resultado = {}
    bloques = [vehicle_ids[i:i + 50] for i in range(0, len(vehicle_ids), 50)]
    for bloque in bloques:
        params = {"types": "obdOdometerMeters,gpsOdometerMeters", "vehicleIds": ",".join(bloque)}
        resp = requests.get(f"{SAMSARA_BASE_URL}/fleet/vehicles/stats", headers=_headers(), params=params, timeout=TIMEOUT_SEGUNDOS)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        for v in data:
            vid = v.get("id")
            metros = None
            if v.get("obdOdometerMeters"):
                metros = v["obdOdometerMeters"].get("value")
            elif v.get("gpsOdometerMeters"):
                metros = v["gpsOdometerMeters"].get("value")
            if vid and metros is not None:
                resultado[vid] = round(metros / 1000.0, 1)
    return resultado