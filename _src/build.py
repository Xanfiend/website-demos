"""Builds one demo page per shop from _src/autoserviss.html. Run: python3 _src/build.py"""
import html, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
TPL = (ROOT / "_src" / "autoserviss.html").read_text(encoding="utf-8")

# slug, name, "in <town>" (locative), town, services
SHOPS = [
    ("autoserviss", "Jūsu Autoserviss", "", "Jūsu pilsēta",
     ["Diagnostika", "Apkope", "Ritošās daļas remonts", "Riepu serviss"]),
    ("bergs-serviss", "Bergs Serviss", "Valmierā", "Valmiera", ["Diagnostika", "Apkope", "Remonts"]),
    ("rem-sport", "REM sport", "Valmierā", "Valmiera",
     ["Evakuatora pakalpojumi", "Tehniskā palīdzība uz ceļa", "Autoserviss"]),
    ("dzinca", "Dzinča", "Priekuļu pagastā", "Priekuļu pagasts",
     ["Apkope un remonts", "Stiklu ielīmēšana", "Ātrumkārbu remonts", "Metālapstrāde"]),
    ("aizezere", "Aizezere", "Madonā", "Madona",
     ["Starteru remonts", "Ģeneratoru remonts", "Eļļas maiņa", "Auto remonts"]),
    ("kn-autoklubs", "KN autoklubs", "Madonā", "Madona",
     ["Diagnostika", "Riteņu savirze", "Ritošās daļas remonts", "Dzinēja remonts"]),
    ("saules-serviss", "Saules serviss", "Ērgļos", "Ērgļi",
     ["Auto remonts", "Riepu serviss", "Sagatavošana tehniskajai apskatei"]),
    ("teiksmas-auto", "Teiksmas Auto", "Bauskas novadā", "Bauskas novads",
     ["Auto remonts", "Krāsošana", "Riepu serviss"]),
    ("mobile-truck-service", "Mobile Truck Service", "Jēkabpilī", "Jēkabpils",
     ["Kravas auto apkope", "Vieglo auto apkope", "Kondicionieru uzpilde un remonts"]),
    ("green-garage", "Green Garage", "Ozolniekos", "Ozolnieki", ["Auto remonts", "Apkope", "Diagnostika"]),
    ("vvva", "VVVA", "Jelgavā", "Jelgava",
     ["Kravas auto remonts", "Autobusu remonts", "Metināšana", "Radiatoru remonts"]),
]

for slug, name, loc, town, services in SHOPS:
    generic = slug == "autoserviss"
    e = html.escape
    note = ("Paraugs autoservisa mājaslapai. Nosaukumu, cenas, foto un kontaktus nomainu pret jūsu."
            if generic else
            f"Šis paraugs ir sagatavots tieši uzņēmumam «{e(name)}». Cenas, tālrunis un adrese ir piemēri, ieliksim jūsu.")
    page = (TPL
            .replace("{{NAME}}", e(name))
            .replace("{{NOTE}}", note)
            .replace("{{EYEBROW}}", "Autoserviss" + (f" {e(loc)}" if loc else ""))
            .replace("{{TOWN}}", e(town))
            .replace("{{SERVICES}}", "".join(f"<li>{e(s)}</li>" for s in services)))
    out = ROOT / slug
    out.mkdir(exist_ok=True)
    (out / "index.html").write_text(page, encoding="utf-8")
    print("built", slug)
