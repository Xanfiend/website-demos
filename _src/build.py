"""Builds one demo page per shop from _src/autoserviss.html. Run: python3 _src/build.py"""
import html, json, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parent.parent
TPL = (ROOT / "_src" / "autoserviss.html").read_text(encoding="utf-8")

# slug, name, "in <town>" (locative), town, services, what customers type into Google
SHOPS = [
    ("autoserviss", "Jūsu Autoserviss", "", "Jūsu pilsēta",
     ["Diagnostika", "Apkope", "Ritošās daļas remonts", "Riepu serviss"], ""),
    ("bergs-serviss", "Bergs Serviss", "Valmierā", "Valmiera", ["Diagnostika", "Apkope", "Remonts"], "autoserviss Valmiera"),
    ("rem-sport", "REM sport", "Valmierā", "Valmiera",
     ["Evakuatora pakalpojumi", "Tehniskā palīdzība uz ceļa", "Autoserviss"], "evakuators Valmiera", "evak"),
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
     ["Kravas auto apkope", "Vieglo auto apkope", "Kondicionieru uzpilde un remonts"], "kravas auto serviss Jēkabpils", "kravas"),
    ("green-garage", "Green Garage", "Ozolniekos", "Ozolnieki", ["Auto remonts", "Apkope", "Diagnostika"], "autoserviss Ozolnieki"),
    ("vvva", "VVVA", "Jelgavā", "Jelgava",
     ["Kravas auto remonts", "Autobusu remonts", "Metināšana", "Radiatoru remonts"], "kravas auto remonts Jelgava", "kravas"),
    ("garaze", "Garaze", "Valmierā", "Valmiera",
     ["Diagnostika un remonts", "Riepu montāža un balansēšana", "Motoru un ātrumkārbu remonts", "Autoelektriķis",
      "Kondicionieru uzpilde"], "autoserviss Valmiera"),
    ("k36", "K36", "Valmierā", "Valmiera",
     ["Pretrūsas apstrāde", "Bremžu remonts", "Datordiagnostika", "Sagatavošana tehniskajai apskatei"],
     "pretrūsas apstrāde Valmiera", "prets"),
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
     "kravas auto serviss Dobele", "kravas"),
    ("treks", "TREKS", "Daugavpilī", "Daugavpils",
     ["Dzinēju remonts un diagnostika", "Ritošās daļas remonts", "Bremžu sistēmas remonts", "Savirzes regulēšana",
      "Sajūga un ātrumkārbu remonts"], "autoserviss Daugavpils"),
    ("silavas-servisa-centrs", "Silavas Servisa Centrs", "Salaspilī", "Salaspils",
     ["Auto remonts un apkope", "Riepu montāža un balansēšana", "Bremžu diagnostika un remonts", "Savirzes regulēšana",
      "Mikroautobusu remonts"], "autoserviss Salaspils"),
    ("re-crs", "RE-CRS", "Grobiņā", "Grobiņa",
     ["Sprauslu remonts", "Common Rail sūkņu diagnostika un remonts", "Dīzeļdegvielas sistēmas diagnostika",
      "Autoserviss"], "sprauslu remonts Liepāja", "dizelis"),
    ("eskada-serviss", "Eskada-Serviss", "Rīgā", "Rīga",
     ["Stūres reiku restaurācija", "Elektrisko stūru remonts", "Diagnostika", "Bremžu remonts", "Riepu serviss"],
     "stūres reikas remonts Rīga", "sture"),
    ("koruns", "Koruns", "Rīgā", "Rīga",
     ["Automātisko ātrumkārbu remonts", "Mehānisko ātrumkārbu remonts", "Transmisijas remonts",
      "Ritošās daļas remonts", "Tehniskā apkope"], "ātrumkārbu remonts Rīga", "karbas"),
    ("dsc", "D.S.C.", "Daugavpilī", "Daugavpils",
     ["Autostiklu maiņa", "Plaisu remonts", "Stikli kravas auto un autobusiem", "Stikli lauksaimniecības tehnikai"],
     "auto stikli Daugavpils", "stikli"),
    ("ags-serviss", "AGS serviss", "Daugavpilī", "Daugavpils",
     ["Gāzes iekārtu uzstādīšana", "Gāzes iekārtu remonts", "Benzīna un gāzes dzinēju datordiagnostika"],
     "auto gāzes iekārtas Daugavpils", "gaze"),
    ("togo-serviss", "ToGo serviss", "Ludzā", "Ludza",
     ["Riepu montāža un balansēšana", "Riepu remonts", "Sezonas riepu glabāšana", "Riepu tirdzniecība",
      "Kravas auto un traktoru riepas"], "riepu serviss Ludza", "riepas"),
    ("damiron", "Damiron", "Jelgavā", "Jelgava",
     ["Virsbūves remonts", "Auto krāsošana", "Auto pulēšana", "OCTA un KASKO remonti"],
     "auto krāsošana Jelgava", "virsbuve"),
    ("aidaks", "Aidaks", "Cēsīs", "Cēsis",
     ["Riepu montāža un balansēšana", "Riepu remonts", "Riepu tirdzniecība",
      "Kravas un lauksaimniecības tehnikas riepas"], "riepu serviss Cēsis", "riepas"),
]

WINTER = ("Ziemas riepas obligātas no 1. decembra", "Riepu maiņa bez rindas, piesakoties iepriekš.")
GENERIC_SUB = "Cenu piemēri. Precīzu cenu jūsu auto nosaucam pirms darba."
# profile: page copy that changes with the kind of shop. Prices are placeholders the owner replaces.
# noun, h1, lead, estimate rows (last = total), season banner, price intro, price rows (name, note, price)
PROFILES = {
    "auto": ("Autoserviss", "Remonts bez <em>pārsteigumiem</em> rēķinā",
        "Pirms sākam darbu, jūs saņemat tāmi ar cenu. Ja remonta laikā atklājas kas papildu, vispirms piezvanām un tikai tad darām.",
        [("Priekšējo bremžu kluču maiņa", "35,00"), ("Bremžu kluči, komplekts", "42,00"), ("Bremžu sistēmas pārbaude", "0,00"), ("Kopā ar PVN", "77,00")],
        WINTER, "Darba cenas vieglajām automašīnām. Detaļas rēķinām atsevišķi un nosaucam cenu pirms pasūtīšanas.",
        [("Eļļas un filtra maiņa", "Eļļu varat atvest arī savu", "no 25 €"), ("Riepu maiņa, 4 riteņi", "Ar balansēšanu", "no 30 €"),
         ("Bremžu kluču maiņa, viena ass", "", "no 35 €"), ("Datordiagnostika", "Kļūdu nolasīšana un skaidrojums", "no 20 €"),
         ("Ritošās daļas pārbaude", "", "no 15 €"), ("Sagatavošana tehniskajai apskatei", "Pārbaudām to pašu, ko skatīs apskatē", "no 25 €"),
         ("Kondicioniera uzpilde", "", "no 45 €")]),
    "kravas": ("Kravas auto serviss", "Kravas auto atpakaļ uz ceļa <em>bez liekas dīkstāves</em>",
        "Katra stāvēšanas diena maksā. Pirms darba nosaucam cenu un termiņu, un paziņojam uzreiz, ja kas mainās.",
        [("Bremžu uzliku maiņa, viena ass", "90,00"), ("Bremžu uzlikas, komplekts", "140,00"), ("Bremžu sistēmas pārbaude", "0,00"), ("Kopā bez PVN", "230,00")],
        None, "Darba cenu piemēri kravas transportam. Detaļas rēķinām atsevišķi un nosaucam cenu pirms pasūtīšanas.",
        [("Datordiagnostika", "Kļūdu nolasīšana un skaidrojums", "no 40 €"), ("Eļļas un filtru maiņa", "", "no 80 €"),
         ("Bremžu uzliku maiņa, viena ass", "", "no 90 €"), ("Riepas maiņa, viens ritenis", "", "no 15 €"),
         ("Sagatavošana tehniskajai apskatei", "", "no 50 €"), ("Metināšanas darbi", "Pēc apskates", "pēc tāmes")]),
    "evak": ("Evakuators", "Evakuators, kad auto <em>vairs nebrauc</em>",
        "Piezvaniet, un uzreiz pateiksim cenu un pēc cik ilga laika būsim klāt. Aizvedam uz servisu vai mājām.",
        [("Izsaukums pilsētā", "40,00"), ("Ceļš ārpus pilsētas, 20 km", "20,00"), ("Iekraušana un nostiprināšana", "0,00"), ("Kopā ar PVN", "60,00")],
        None, "Cenu piemēri. Precīzu cenu nosaucam pa telefonu, pirms izbraucam.",
        [("Evakuācija pilsētā", "", "no 40 €"), ("Evakuācija ārpus pilsētas", "Par katru kilometru", "no 1 €/km"),
         ("Akumulatora palaišana", "", "no 20 €"), ("Riepas maiņa uz ceļa", "", "no 20 €"),
         ("Izvilkšana no grāvja", "Atkarīgs no vietas", "pēc vienošanās")]),
    "riepas": ("Riepu serviss", "Riepu maiņa <em>bez rindas</em>",
        "Piesakieties uz konkrētu laiku, un jums nav jāgaida. Cenu zināt jau pirms ierašanās.",
        [("Riepu maiņa, 4 riteņi", "24,00"), ("Balansēšana, 4 riteņi", "16,00"), ("Riepu spiediena pārbaude", "0,00"), ("Kopā ar PVN", "40,00")],
        WINTER, "Cenu piemēri vieglajām automašīnām. Citai tehnikai cenu nosaucam pa telefonu.",
        [("Riepu maiņa ar balansēšanu, R13–R15", "4 riteņi", "no 30 €"), ("Riepu maiņa ar balansēšanu, R16–R18", "4 riteņi", "no 40 €"),
         ("Riepas remonts", "", "no 10 €"), ("Sezonas riepu glabāšana", "4 riepas, viena sezona", "no 25 €"),
         ("Kravas auto riepas montāža", "Viens ritenis", "no 20 €")]),
    "virsbuve": ("Virsbūves remonts un krāsošana", "Virsbūve <em>kā no jauna</em>",
        "Atsūtiet bojājuma foto un saņemiet tāmi. Pirms darba zināt cenu un termiņu.",
        [("Bampera remonts", "60,00"), ("Bampera krāsošana", "120,00"), ("Krāsas toņa piemeklēšana", "0,00"), ("Kopā ar PVN", "180,00")],
        None, GENERIC_SUB,
        [("Vienas detaļas krāsošana", "", "no 120 €"), ("Bampera remonts", "", "no 60 €"), ("Skrāpējumu pulēšana", "", "no 30 €"),
         ("Virsbūves pulēšana", "", "no 90 €"), ("Lukturu pulēšana", "Abi lukturi", "no 25 €")]),
    "stikli": ("Auto stikli", "Stikla maiņa ar <em>skaidru cenu</em>",
        "Nosauciet auto marku un gadu, un pateiksim cenu un laiku. Mazas plaisas bieži var salabot, nemainot stiklu.",
        [("Vējstikls", "110,00"), ("Stikla ielīmēšana", "50,00"), ("Vecā stikla utilizācija", "0,00"), ("Kopā ar PVN", "160,00")],
        None, GENERIC_SUB,
        [("Vējstikla maiņa", "Ar stiklu un darbu", "no 150 €"), ("Sānu stikla maiņa", "", "no 60 €"), ("Aizmugurējā stikla maiņa", "", "no 120 €"),
         ("Plaisas remonts", "", "no 25 €"), ("Stikli kravas auto un traktoriem", "", "pēc pieprasījuma")]),
    "gaze": ("Auto gāzes iekārtas", "Brauciet lētāk <em>ar gāzi</em>",
        "Uzstādām un remontējam auto gāzes iekārtas. Pirms darba nosaucam pilnu cenu: iekārta, uzstādīšana un regulēšana.",
        [("Gāzes iekārta, 4 cilindri", "420,00"), ("Uzstādīšana un regulēšana", "180,00"), ("Pārbaude pēc 1000 km", "0,00"), ("Kopā ar PVN", "600,00")],
        None, GENERIC_SUB,
        [("Gāzes iekārtas uzstādīšana", "Ar iekārtu un regulēšanu", "no 600 €"), ("Iekārtas apkope un filtru maiņa", "", "no 30 €"),
         ("Regulēšana", "", "no 25 €"), ("Datordiagnostika", "Benzīna un gāzes dzinējiem", "no 20 €"), ("Sprauslu tīrīšana", "", "no 40 €")]),
    "karbas": ("Ātrumkārbu remonts", "Ātrumkārbu remonts ar <em>skaidru tāmi</em>",
        "Vispirms diagnostika, tad tāme. Remontējam automātiskās un mehāniskās ātrumkārbas un godīgi pasakām, vai remonts atmaksājas.",
        [("Ātrumkārbas diagnostika", "40,00"), ("Eļļas un filtra maiņa automātam", "90,00"), ("Izmēģinājuma brauciens", "0,00"), ("Kopā ar PVN", "130,00")],
        None, GENERIC_SUB,
        [("Ātrumkārbas diagnostika", "", "no 40 €"), ("Eļļas maiņa automātiskajā ātrumkārbā", "", "no 90 €"), ("Sajūga maiņa", "", "no 150 €"),
         ("Ātrumkārbas remonts", "Pēc diagnostikas", "pēc tāmes"), ("Ritošās daļas pārbaude", "", "no 15 €")]),
    "sture": ("Stūres iekārtu remonts", "Stūres reikas remonts <em>bez minēšanas</em>",
        "Atrodam vainu, nosaucam cenu un tikai tad remontējam. Turpat veicam arī ikdienas apkopi.",
        [("Stūres reikas diagnostika", "20,00"), ("Stūres reikas restaurācija", "180,00"), ("Savirzes pārbaude pēc remonta", "0,00"), ("Kopā ar PVN", "200,00")],
        None, GENERIC_SUB,
        [("Stūres reikas restaurācija", "", "no 180 €"), ("Elektriskās stūres remonts", "Pēc diagnostikas", "pēc tāmes"),
         ("Savirzes regulēšana", "", "no 30 €"), ("Eļļas un filtra maiņa", "", "no 25 €"), ("Bremžu kluču maiņa, viena ass", "", "no 35 €"),
         ("Riepu maiņa, 4 riteņi", "Ar balansēšanu", "no 30 €")]),
    "dizelis": ("Dīzeļa sistēmu remonts", "Sprauslu remonts, kad zināt, <em>par ko maksājat</em>",
        "Pārbaudām sprauslas un sūkņus un parādām rezultātu. Remontējam tikai to, kas tiešām jāremontē.",
        [("Sprauslu pārbaude, 4 gab.", "40,00"), ("Vienas sprauslas remonts", "90,00"), ("Pārbaudes rezultātu izdruka", "0,00"), ("Kopā ar PVN", "130,00")],
        None, GENERIC_SUB,
        [("Sprauslas pārbaude", "Viena sprausla", "no 10 €"), ("Sprauslas remonts", "", "no 90 €"), ("Augstspiediena sūkņa diagnostika", "", "no 40 €"),
         ("Dīzeļa sistēmas datordiagnostika", "", "no 25 €"), ("Sūkņa remonts", "Pēc diagnostikas", "pēc tāmes")]),
    "prets": ("Pretrūsas apstrāde un autoserviss", "Pasargājiet auto <em>no rūsas</em>",
        "Apstrādājam auto apakšu un slēptās vietas. Pirms darba parādām, kādā stāvoklī ir virsbūve, un nosaucam cenu.",
        [("Apakšas mazgāšana un žāvēšana", "40,00"), ("Pretrūsas apstrāde, apakša", "180,00"), ("Foto pirms un pēc", "0,00"), ("Kopā ar PVN", "220,00")],
        ("Sāls uz ceļiem bojā virsbūvi", "Pretrūsas apstrādi vislabāk veikt pirms ziemas."), GENERIC_SUB,
        [("Pretrūsas apstrāde, vieglais auto", "", "no 220 €"), ("Pretrūsas apstrāde, apvidus auto vai mikroautobuss", "", "no 280 €"),
         ("Bremžu kluču maiņa, viena ass", "", "no 35 €"), ("Datordiagnostika", "", "no 20 €"), ("Sagatavošana tehniskajai apskatei", "", "no 25 €")]),
}

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

for slug, name, loc, town, services, term, *rest in SHOPS:
    noun, h1, lead, est, season, price_sub, prices = PROFILES[rest[0] if rest else "auto"]
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
    <li><b>Jūs atrod Google</b><span>Kad salūst auto, cilvēki meklē “{e(term)}”. Bez mājaslapas šie klienti aizbrauc pie tiem, kurus atrod. Lapā jūsu nosaukums, pilsēta un pakalpojumi ir norādīti arī meklētājam saprotamā veidā.</span></li>
    <li><b>Mazāk zvanu “cik maksā?”</b><span>Cenas un darba laiks ir redzami, tāpēc zvana tie, kas grib pieteikties.</span></li>
    <li><b>Pieteikumi arī vakaros</b><span>Forma strādā brīvdienās un pēc darba laika, kad telefonu neceļat.</span></li>
    <li><b>Jauni klienti uzticas ātrāk</b><span>Pirms brauciena cilvēks grib redzēt, ka serviss ir īsts un ko tas dara.</span></li>
  </ul>
  <p class="next">Ja patīk, atbildiet uz manu e-pastu un uzrakstiet, kas jāmaina. Cena sākas no 50 €, to nosaucu iepriekš, un maksājat tikai par gatavu lapu, kas jūs apmierina.</p>
  <p class="below">Jūsu lapas paraugs sākas šeit</p>
</div></div></section>
"""
    # structured data for search engines: business type, town and services
    ld = "" if generic else '<script type="application/ld+json">' + json.dumps({
        "@context": "https://schema.org", "@type": "AutoRepair", "name": name,
        "address": {"@type": "PostalAddress", "addressLocality": town, "addressCountry": "LV"},
        "makesOffer": [{"@type": "Offer", "itemOffered": {"@type": "Service", "name": x}} for x in services],
    }, ensure_ascii=False).replace("</", "<\\/") + "</script>\n"
    page = (TPL
            .replace("{{JSONLD}}", ld)
            .replace("{{OWNER}}", owner)
            .replace("{{NAME}}", e(name))
            .replace("{{NOTE}}", note)
            .replace("{{EYEBROW}}", noun + (f" {e(loc)}" if loc else ""))
            .replace("{{H1}}", h1).replace("{{LEAD}}", lead).replace("{{PRICE_SUB}}", price_sub)
            .replace("{{EST}}", "".join(
                "        <tr%s><td>%s</td><td>%s €</td></tr>\n" % (' class="total"' if i == len(est) - 1 else "", a, b)
                for i, (a, b) in enumerate(est)))
            .replace("{{SEASON}}", "" if not season else
                     f'<div class="season">\n  <div class="wrap">\n    <strong><svg class="i"><use href="#clock"/></svg>{season[0]}</strong>\n'
                     f'    <span>{season[1]}</span>\n    <a href="#pieteikums">Pieteikties →</a>\n  </div>\n</div>\n')
            .replace("{{PRICES}}", "".join(
                f'        <tr><td>{a}{f"<small>{n}</small>" if n else ""}</td><td>{p}</td></tr>\n' for a, n, p in prices))
            .replace("{{TOWN}}", e(town))
            .replace("{{INITIAL}}", e(name[0].upper()))
            .replace("{{SERVICES}}", "".join(card(s) for s in services)))
    if rest and rest[0] == "evak":
        page = page.replace("Pieteikt vizīti", "Izsaukt evakuatoru")
    out = ROOT / slug
    out.mkdir(exist_ok=True)
    (out / "index.html").write_text(page, encoding="utf-8")
    print("built", slug)
