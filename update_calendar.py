"""
update_calendar.py
Obtiene los partidos del Mundial 2026 desde la API de FIFA,
genera un archivo .ics y actualiza el Gist de GitHub.
"""

import json
import os
import uuid
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone


# ── Configuración ────────────────────────────────────────────────────────────
FIFA_API = (
    "https://api.fifa.com/api/v3/calendar/matches"
    "?idCompetition=17&idSeason=285023&count=200&language=es"
)
GIST_ID  = os.environ["GIST_ID"]    # se lee del secreto de GitHub
GH_TOKEN = os.environ["GH_TOKEN"]   # se lee del secreto de GitHub
ICS_FILENAME = "Copa_Mundial_FIFA_2026.ics"


# ── Mapeo de código FIFA → emoji de bandera ──────────────────────────────────
FIFA_TO_ISO2 = {
    "MEX":"MX","USA":"US","CAN":"CA","JAM":"JM","TRI":"TT","HAI":"HT",
    "CUB":"CU","PAN":"PA","HON":"HN","CRC":"CR","SLV":"SV","GUA":"GT","CUW":"CW",
    "ARG":"AR","BRA":"BR","URU":"UY","COL":"CO","ECU":"EC","PAR":"PY",
    "PER":"PE","CHI":"CL","VEN":"VE","BOL":"BO",
    "FRA":"FR","ESP":"ES","GER":"DE","POR":"PT","ITA":"IT","NED":"NL",
    "BEL":"BE","SUI":"CH","AUT":"AT","DEN":"DK","SWE":"SE","NOR":"NO",
    "FIN":"FI","POL":"PL","CRO":"HR","SRB":"RS","GRE":"GR","TUR":"TR",
    "ALB":"AL","SVN":"SI","SVK":"SK","CZE":"CZ","HUN":"HU","ROU":"RO",
    "UKR":"UA","BUL":"BG","ISL":"IS","IRL":"IE","SCO":"GB","WAL":"GB",
    "ENG":"GB","NIR":"GB","MKD":"MK","MNE":"ME","BIH":"BA","ROM":"RO",
    "LUX":"LU","GEO":"GE","AZE":"AZ","KOS":"XK",
    "MAR":"MA","SEN":"SN","NGA":"NG","GHA":"GH","CMR":"CM","CIV":"CI",
    "MLI":"ML","RSA":"ZA","ZAF":"ZA","EGY":"EG","TUN":"TN","ALG":"DZ",
    "ANG":"AO","COD":"CD","TAN":"TZ","UGA":"UG","ZIM":"ZW","MOZ":"MZ",
    "BEN":"BJ","CPV":"CV",
    "JPN":"JP","KOR":"KR","AUS":"AU","CHN":"CN","IRN":"IR","SAU":"SA",
    "KSA":"SA","QAT":"QA","UAE":"AE","IRQ":"IQ","JOR":"JO","UZB":"UZ",
    "THA":"TH","IND":"IN","IDN":"ID","NZL":"NZ","FIJ":"FJ","PNG":"PG",
    "OMA":"OM","BHR":"BH","KUW":"KW","VIE":"VN","PHI":"PH",
}

def flag(code):
    iso2 = FIFA_TO_ISO2.get(code, "")
    if not iso2:
        return "🏳️"
    return chr(0x1F1E6 + ord(iso2[0]) - 65) + chr(0x1F1E6 + ord(iso2[1]) - 65)

def locale(items):
    for loc in ("es-ES", "es-MX", "en-US", "en-GB"):
        for item in (items or []):
            if item.get("Locale") == loc:
                return item.get("Description", "")
    return items[0].get("Description", "") if items else ""

def get_team(t):
    if not t:
        return "TBD", ""
    names = t.get("TeamName", [])
    name  = locale(names) if names else (t.get("PlaceHolderA") or t.get("Abbreviation") or "TBD")
    code  = t.get("IdCountry") or t.get("Abbreviation") or ""
    return name, code

def fdt(s, dh=0):
    dt = datetime.fromisoformat(s.rstrip("Z")).replace(tzinfo=timezone.utc)
    return (dt + timedelta(hours=dh)).strftime("%Y%m%dT%H%M%SZ")

def esc(t):
    return (str(t)
            .replace("\\", "\\\\")
            .replace(";", "\\;")
            .replace(",", "\\,")
            .replace("\n", "\\n"))


# ── 1. Obtener partidos de la API de FIFA ────────────────────────────────────
print("📡 Obteniendo partidos desde la API de FIFA...")
req = urllib.request.Request(FIFA_API,
      headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
with urllib.request.urlopen(req, timeout=20) as r:
    matches = json.loads(r.read()).get("Results", [])
print(f"   ✅ {len(matches)} partidos encontrados")


# ── 2. Construir el contenido .ics ───────────────────────────────────────────
print("📅 Generando archivo ICS...")
now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
lines = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//Copa Mundial FIFA 2026//ES",
    "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH",
    "X-WR-CALNAME:⚽ Copa Mundial FIFA 2026",
    "X-WR-TIMEZONE:UTC",
    "X-WR-CALDESC:Todos los partidos de la Copa Mundial de la FIFA 2026 – Canadá, México y EE.UU.",
]

for m in matches:
    hn, hc = get_team(m.get("Home", {}))
    an, ac = get_team(m.get("Away", {}))
    hf, af = flag(hc), flag(ac)
    ds     = m.get("Date", "")
    stg    = locale(m.get("StageName", []))
    grp    = locale(m.get("GroupName", []))
    stad   = m.get("Stadium") or {}
    loc    = ", ".join(p for p in [locale(stad.get("Name", [])),
                                    locale(stad.get("CityName", []))] if p)
    hs, as_ = m.get("HomeTeamScore"), m.get("AwayTeamScore")
    st     = m.get("MatchStatus", 0)

    if hs is not None and as_ is not None and st in (0, 3):
        summ = f"{hf} {hn} {hs}–{as_} {an} {af}"
    else:
        summ = f"{hf} {hn} vs. {an} {af}"

    sg   = stg + (f" – {grp}" if grp else "")
    desc = "\\n".join(filter(None, [
        "🏆 Copa Mundial de la FIFA 2026",
        f"📋 {sg}",
        f"🏟️ {loc}" if loc else "",
        f"🕐 Hora UTC: {ds[:16].replace('T', ' ')}",
        f"📊 Resultado: {hn} {hs}–{as_} {an}" if hs is not None else "",
    ]))
    uid = str(uuid.uuid5(uuid.NAMESPACE_URL,
              f"fifa-wc2026-{m.get('IdMatch')}-{m.get('IdSeason')}"))

    lines += [
        "BEGIN:VEVENT",
        f"UID:{uid}@fifa-wc2026",
        f"DTSTAMP:{now}",
        f"DTSTART:{fdt(ds)}",
        f"DTEND:{fdt(ds, 2)}",
        f"SUMMARY:{esc(summ)}",
        f"LOCATION:{esc(loc)}",
        f"DESCRIPTION:{desc}",
        "CATEGORIES:Fútbol\\,Copa Mundial\\,FIFA 2026",
        "STATUS:CONFIRMED",
        "END:VEVENT",
    ]

lines.append("END:VCALENDAR")
ics_content = "\r\n".join(lines) + "\r\n"
print(f"   ✅ ICS generado con {len(matches)} eventos")


# ── 3. Actualizar el Gist de GitHub ─────────────────────────────────────────
print("☁️  Subiendo a GitHub Gist...")
payload = json.dumps({
    "files": {
        ICS_FILENAME: {"content": ics_content}
    }
}).encode("utf-8")

gist_req = urllib.request.Request(
    f"https://api.github.com/gists/{GIST_ID}",
    data=payload,
    method="PATCH",
    headers={
        "Authorization": f"Bearer {GH_TOKEN}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "FIFA-WC2026-Calendar-Bot",
    },
)
with urllib.request.urlopen(gist_req, timeout=15) as r:
    result = json.loads(r.read())

raw_url = result["files"][ICS_FILENAME]["raw_url"]
# La raw URL cambia con cada versión; la URL base sin versión es permanente
base_url = f"https://gist.githubusercontent.com/{result['owner']['login']}/{GIST_ID}/raw/{ICS_FILENAME}"
print(f"   ✅ Gist actualizado correctamente")
print(f"   🔗 URL permanente: {base_url}")
print(f"   📲 Para Apple Calendar usa: webcal://gist.githubusercontent.com/{result['owner']['login']}/{GIST_ID}/raw/{ICS_FILENAME}")
