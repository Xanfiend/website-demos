"""Builds one demo page per shop from _src/autoserviss.html. Run: python3 _src/build.py"""
import html, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
TPL = (ROOT / "_src" / "autoserviss.html").read_text(encoding="utf-8")

# slug, name, "in <town>" (locative), town, services, what customers type into Google
SHOPS = [
    ("autoserviss", "Jūsu Autoserviss", "", "Jūsu pilsēta",
     ["Diagnostika", "Apkope", "Ritošās daļas remonts", "Riepu serviss"], ""),
    ("bergs-serviss", "Bergs Serviss", "Valmierā", "Valmiera", ["Diagnostika", "Apkope", "Remonts"], "autoserviss Valmiera"),
    ("rem-sport", "REM sport", "Valmierā", "Valmiera",
     ["Evakuatora pakalpojumi", "Tehniskā palīdzība uz ceļa", "Autoserviss"], "evakuators Valmiera"),
    ("dzinca", "Dzinča", "Priekuļu pagastā", "Priekuļu pagasts",
     ["Apkope un remonts", "Stiklu ielīmēšana", "Ātrumkārbu remonts", "Metālapstrāde"], "autoserviss Cēsis"),
    ("aizezere", "Aizezere", "Madonā", "Madona",
     ["Starteru remonts", "Ģeneratoru remonts", "Eļļas maiņa", "Auto remonts"], "autoserviss Madona"),
    ("kn-autoklubs", "KN autoklubs", "Madonā", "Madona",
     ["Diagnostika", "Riteņu savirze", "Ritošās daļas remonts", "Dzinēja remonts"], "autoserviss Madona"),
    ("saules-serviss", "Saules serviss", "Ērgļos", "Ērgļi",
     ["Auto remonts", "Riepu serviss", "Sagatavošana tehniskajai apskatei"], "autoserviss Ērgļi"),
    ("teiksmas-auto", "Teiksmas Auto", "Bauskas novadā", "Bauskas novads",
     ["Auto remonts", "Krāsošana", "Riepu serviss"], "autoserviss Bauska"),
    ("mobile-truck-service", "Mobile Truck Service", "Jēkabpilī", "Jēkabpils",
     ["Kravas auto apkope", "Vieglo auto apkope", "Kondicionieru uzpilde un remonts"], "kravas auto serviss Jēkabpils"),
    ("green-garage", "Green Garage", "Ozolniekos", "Ozolnieki", ["Auto remonts", "Apkope", "Diagnostika"], "autoserviss Ozolnieki"),
    ("vvva", "VVVA", "Jelgavā", "Jelgava",
     ["Kravas auto remonts", "Autobusu remonts", "Metināšana", "Radiatoru remonts"], "kravas auto remonts Jelgava"),
]

for slug, name, loc, town, services, term in SHOPS:
    generic = slug == "autoserviss"
    e = html.escape
    note = ("Paraugs autoservisa mājaslapai. Nosaukumu, cenas, foto un kontaktus nomainu pret jūsu."
            if generic else
            f"Šis paraugs ir sagatavots tieši uzņēmumam «{e(name)}». Cenas, tālrunis un adrese ir piemēri, ieliksim jūsu.")
    owner = "" if generic else f"""<section class="owner"><div class="wrap"><div class="card">
  <p class="tag">Tikai jums. Klienti šo daļu neredzēs.</p>
  <h2>Šo lapu sagatavoju tieši jums</h2>
  <p>Labdien! Esmu Raivo no Valmieras. Šis ir paraugs, kā varētu izskatīties «{e(name)}» mājaslapa. Zemāk tā ir tāda, kādu to redzētu jūsu klients, jau ar jūsu nosaukumu un pakalpojumiem.</p>
  <ul>
    <li><b>Jūs atrod Google</b><span>Kad salūst auto, cilvēki meklē “{e(term)}”. Bez mājaslapas šie klienti aizbrauc pie tiem, kurus atrod.</span></li>
    <li><b>Mazāk zvanu “cik maksā?”</b><span>Cenas un darba laiks ir redzami, tāpēc zvana tie, kas grib pieteikties.</span></li>
    <li><b>Pieteikumi arī vakaros</b><span>Forma strādā brīvdienās un pēc darba laika, kad telefonu neceļat.</span></li>
    <li><b>Jauni klienti uzticas ātrāk</b><span>Pirms brauciena cilvēks grib redzēt, ka serviss ir īsts un ko tas dara.</span></li>
  </ul>
  <p class="next">Ja patīk, atbildiet uz manu e-pastu ar laiku un numuru, uz kuru piezvanīt. Par cenu vienosimies, un maksājat tikai par gatavu lapu, kas jūs apmierina.</p>
  <p class="below">Jūsu lapas paraugs sākas šeit</p>
</div></div></section>
"""
    page = (TPL
            .replace("{{OWNER}}", owner)
            .replace("{{NAME}}", e(name))
            .replace("{{NOTE}}", note)
            .replace("{{EYEBROW}}", "Autoserviss" + (f" {e(loc)}" if loc else ""))
            .replace("{{TOWN}}", e(town))
            .replace("{{SERVICES}}", "".join(f"<li>{e(s)}</li>" for s in services)))
    out = ROOT / slug
    out.mkdir(exist_ok=True)
    (out / "index.html").write_text(page, encoding="utf-8")
    print("built", slug)
