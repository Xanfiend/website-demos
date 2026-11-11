"""Builds one demo page per shop from _src/autoserviss.html. Run: python3 _src/build.py"""
import html, pathlib, re

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
    ("garaze", "Garaze", "Valmierā", "Valmiera",
     ["Diagnostika un remonts", "Riepu montāža un balansēšana", "Motoru un ātrumkārbu remonts", "Autoelektriķis",
      "Kondicionieru uzpilde"], "autoserviss Valmiera"),
    ("k36", "K36", "Valmierā", "Valmiera",
     ["Pretrūsas apstrāde", "Bremžu remonts", "Datordiagnostika", "Sagatavošana tehniskajai apskatei"],
     "pretrūsas apstrāde Valmiera"),
    ("savirze", "Savirze", "Limbažos", "Limbaži",
     ["Savirzes regulēšana", "Auto remonts un apkope", "Riepu serviss", "Sagatavošana tehniskajai apskatei"],
     "autoserviss Limbaži"),
    ("jj-un-ko", "JJ un KO", "Siguldā", "Sigulda",
     ["Diagnostika", "Virsbūves remonts un krāsošana", "Alumīnija metināšana", "Savirzes regulēšana",
      "Kondicionieru uzpilde"], "autoserviss Sigulda"),
    ("kurland-auto", "Kurland Auto", "Talsos", "Talsi",
     ["Auto remonts un apkope", "Dzinēju remonts", "Elektrodiagnostika", "Kondicionieru uzpilde",
      "Evakuatora pakalpojumi"], "autoserviss Talsi"),
    ("lil-auto", "LIL auto", "Koknesē", "Koknese",
     ["Auto remonts", "Riepu maiņa", "Bremžu remonts", "Savirzes un lukturu regulēšana", "Dzinēju remonts"],
     "autoserviss Koknese"),
    ("tako-serviss", "Tako serviss", "Balvos", "Balvi",
     ["Auto remonts", "Vieglo auto apkope", "Sagatavošana tehniskajai apskatei", "Riepu remonts"], "autoserviss Balvi"),
    ("bm-motors", "BM motors", "Liepājā", "Liepāja",
     ["Auto remonts", "Elektrodiagnostika un programmēšana", "Riteņu ģeometrijas regulēšana",
      "Riepu remonts un montāža"], "autoserviss Liepāja"),
    ("rero-serviss", "Rero serviss", "Dobelē", "Dobele",
     ["Kravas auto remonts", "Virsbūves darbi", "Dzinēju remonts", "Hidraulika", "Rezerves daļas"],
     "kravas auto serviss Dobele"),
    ("treks", "TREKS", "Daugavpilī", "Daugavpils",
     ["Dzinēju remonts un diagnostika", "Ritošās daļas remonts", "Bremžu sistēmas remonts", "Savirzes regulēšana",
      "Sajūga un ātrumkārbu remonts"], "autoserviss Daugavpils"),
]

# first matching keyword picks the card icon and the one-line description
KINDS = [
    ("diagnost", "gauge", "Nolasām kļūdas un saprotami izskaidrojam, ko tās nozīmē."),
    ("riep", "tyre", "Maiņa, montāža un balansēšana, piesakoties iepriekš."),
    ("savirz|ģeometr", "tyre", "Noregulējam, lai auto brauc taisni un riepas nodilst vienmērīgi."),
    ("kondicion", "snow", "Pārbaude, uzpilde un remonts pirms sezonas."),
    ("kravas|autobus|evakuator|palīdzība", "truck", "Zvaniet, vienosimies par laiku un vietu."),
    ("elektr|starter|ģenerator", "bolt", "Atrodam vainu un salabojam, nevis mainām visu pēc kārtas."),
    ("krāso|virsbūv|pretrūs|stikl", "shield", "Rūpīgs darbs, kas pasargā auto un saglabā tā vērtību."),
    ("apkop|eļļ|apskat", "drop", "Regulāra apkope, lai lielie remonti nebūtu vajadzīgi."),
]

def card(s):
    icon, text = next(((i, t) for k, i, t in KINDS if re.search(k, s.lower())),
                      ("wrench", "Pirms darba nosaucam cenu un termiņu."))
    return (f'<li><div class="ico"><svg class="i"><use href="#{icon}"/></svg></div>'
            f'<h3>{html.escape(s)}</h3><p>{text}</p></li>')

for slug, name, loc, town, services, term in SHOPS:
    generic = slug == "autoserviss"
    e = html.escape
    note = ("Paraugs autoservisa mājaslapai. Nosaukumu, cenas, foto un kontaktus nomainu pret jūsu."
            if generic else
            f"Šis paraugs ir sagatavots tieši uzņēmumam «{e(name)}». Teksti, cenas, tālrunis un adrese ir piemēri, ieliksim jūsu.")
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
            .replace("{{INITIAL}}", e(name[0].upper()))
            .replace("{{SERVICES}}", "".join(card(s) for s in services)))
    out = ROOT / slug
    out.mkdir(exist_ok=True)
    (out / "index.html").write_text(page, encoding="utf-8")
    print("built", slug)
