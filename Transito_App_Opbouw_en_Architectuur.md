# Transito TMS & SDI Facturatie 🤝🇮🇹
## Systeemopbouw, Architectuur & Tools Overzicht

**Datum:** 23 oktober 2026  
**Status:** Productie v2.4  
**Hosting:** Lokaal op eigen pc + Beveiligde Cloudflare HTTPS Tunnel  

---

## 1. Doel & Bedrijfsmodel van de Applicatie
De applicatie is speciaal ontworpen en ingericht voor een **transportintermediair / vrachtmakelaar / agent** (*intermediario dei trasporti* of *procacciatore d'affari*) gevestigd in Italië, die optreedt namens een vast **partner-transportbedrijf**.

### Hoe het operationele en fiscale model werkt:
1. **Verlader (Opdrachtgever)**: Vraagt een transport aan. Jij stelt een vrachtofferte op. Na akkoord betaalt de verlader het volledige vrachttarief rechtstreeks aan het partner-transportbedrijf.
2. **Partner-Transportbedrijf**: Voert het fysieke transport uit en factureert de vracht aan de verlader.
3. **Jouw Onderneming (Intermediair)**: Heeft géén eigen vrachtwagens en rijdt niet zelf. Jij brengt een bemiddelingsprovisie (standaard 10% of vast bedrag) in rekening bij het transportbedrijf via officiële Italiaanse elektronische facturen (**FatturaPA FPR12 via SDI**).
4. **Btw-vrijstelling & Verlegging**: Conform de Italiaanse wetgeving valt de commissie onder:
   - **Artikel 7-ter DPR 633/72** (*Inversione contabile*, Natura **`N6`**, btw-verlegd naar EU/NL transportbedrijf).
   - **Artikel 9 DPR 633/72** (*Non imponibile*, Natura **`N3.2`**, bij internationaal Italiaans vervoer).

---

## 2. Systeemarchitectuur & Bestandsstructuur

De applicatie is gebouwd volgens een robuust **Zero-External-Pip** principe. De volledige backend draait op de pure **Python Standard Library** zonder zware externe dependencies. Dit garandeert maximale stabiliteit, razendsnelle opstarttijden en volledige onafhankelijkheid van verouderende pip-pakketten.

| Bestand / Module | Functie & Verantwoordelijkheid |
| :--- | :--- |
| **`server.py`** | Centrale HTTP REST API backend. Handelt alle API-routes, sessies, PDF-downloads en e-mailverzendingen af. |
| **`database.py`** | SQLite databasebeheer. Bevat automatische schemamigraties, tabellen voor ritten, facturen, partijen en OIC-boekhouding. |
| **`pdf_generator.py`** | Pure Python PDF 1.4 vector generator. Produceert officiële A4 PDF's van offertes en commissiefacturen. |
| **`sdi_generator.py`** | FatturaPA FPR12 XML generator. Genereert conforme SDI-facturen met alle Italiaanse fiscale velden. |
| **`email_sender.py`** | SMTP & PEC mailclient. Verzendt professionele HTML/tekst e-mails met automatische PDF- en XML-bijlagen. |
| **`transito_tms.db`** | Lokale SQLite database waarin alle dossiers, offertes, facturen en instellingen veilig op de eigen pc worden bewaard. |
| **`cloudflared.exe`** | Cloudflare tunnel client. Creëert een veilige end-to-end versleutelde HTTPS-tunnel naar de smartphone. |
| **`tunnel_url.txt`** | Houdt automatisch de actuele live Cloudflare URL bij. |
| **`static/index.html`** | Volledig kantoordashboard (Single Page App) voor desktop pc met tabs voor ritten, facturen, SDI en boekhouding. |
| **`static/app.js`** | Desktop frontend logica, data-synchronisatie, berekeningen, grafieken en interacties. |
| **`static/mobile.html`** | Touch-geoptimaliseerde mobiele web-app voor iPhone en Android met grote knoppen en PWA-ondersteuning. |
| **`static/mobile.js`** | Mobiele interacties, touch targets, live provisieberekening, WhatsApp delen en PDF-downloads. |
| **`start.bat / run_online.py`** | Eén-klik Windows opstartbestanden die server en Cloudflare tunnel synchroon starten. |

---

## 3. Overzicht van Gebruikte Tools & Technologieën

| Categorie | Tool / Technologie | Toelichting & Doel |
| :--- | :--- | :--- |
| **Backend Runtime** | **Python 3 Standard Library** | Geen pip packages nodig; gebruikt `http.server`, `urllib`, `json`, `sqlite3`, `smtplib`, `email`. |
| **Database Engine** | **SQLite3** | Betrouwbare serverless SQL database; data staat 100% lokaal op de eigen harde schijf. |
| **PDF Engine** | **Pure Python PDF 1.4 Builder** | Zelfgebouwde PDF generator met WinAnsiEncoding, tabellen, vectorlijnen en CMR-clausules. |
| **SDI XML Engine** | **FatturaPA v1.2.2 (FPR12)** | Gereed voor Sistema di Interscambio; automatische Art. 7-ter / Art. 9 codering. |
| **E-mail / SMTP** | **Python `smtplib` + MIME** | Gekoppeld met live Gmail SMTP (app-wachtwoord) en optionele Italiaanse PEC-ondersteuning. |
| **Desktop Styling** | **Tailwind CSS + FontAwesome 6** | Moderne, overzichtelijke gebruikersinterface met duidelijke kleurcodes en iconen. |
| **Grafieken & KPI** | **Chart.js** | Visuele weergave van ritvolumes, provisiepercentages en maandelijkse provisie-ontwikkeling. |
| **Mobiele App (PWA)** | **HTML5 + Tailwind + PWA Manifest** | Progressive Web App; kan direct via *"Zet op beginscherm"* als app op de telefoon worden geïnstalleerd. |
| **Tunneling & SSL** | **Cloudflare Tunnel (`cloudflared`)** | Wereldwijde HTTPS toegang zonder port-forwarding of router firewall aanpassingen. |
| **Versiebeheer** | **Git & GitHub** | Veilige private backup op GitHub (`admeijs-sys/transito-tms`). |

---

## 4. De Belangrijkste Modules in Detail

### A. Bemiddelingsopdrachten & Offertes (*Preventivo Trasporto*)
- **Offerte of Direct Aanmelden**: Bij het invoeren van een rit kun je kiezen tussen een vrijblijvende vrachtofferte voor de klant of een definitieve aanmelding.
- **4 Flexibele Provisiemodellen**:
  1. *Percentage*: bijv. 10% van het vrachttarief.
  2. *Vaste Fee*: bijv. € 200,- per rit.
  3. *Marge*: verschil tussen verladers- en vervoerderstarief.
  4. *Vrije Invoer*: direct aanpasbaar provisiebedrag.
- **Automatisch E-mailen**: Bij het opslaan van een offerte wordt deze direct per e-mail met het officiële A4 PDF-document verzonden naar `admeijs@gmail.com`.
- **A4 PDF Document**: Compleet met laad- en losadres, CMR-voorwaarden, geldigheidstermijn en akkoordblok.

### B. Elektronische Facturatie (*SDI FatturaPA*)
- **1-Klik Facturatie**: Individuele ritten factureren of openstaande ritten bundelen op één maandelijkse verzamelfactuur aan het transportbedrijf.
- **Fiscale Foutpreventie**: Automatische Natura-codes (N6 voor EU, N3.2 voor internationaal binnenlands transport).
- **XML & PDF Export**: Zowel het officiële `.xml` bestand als het opgemaakte A4 PDF factuursjabloon kunnen direct worden ingezien en gedownload.
- **SDI Simulatie**: Volg de status van verzonden commissiefacturen (*Gegenereerd*, *Verzonden*, *Geaccepteerd / Notifica di avvenuta consegna*).

### C. Italiaanse Boekhouding (*Contabilità e Fisco*)
- **Registro IVA Vendite (art. 23 DPR 633/72)**: Wettelijk verkoopregister van alle uitgaande provisiefacturen.
- **Registro IVA Acquisti (art. 25 DPR 633/72)**: Inkoopregister van bedrijfskosten met aftrekbare btw.
- **Liquidazione IVA & F24**: Berekening van het periodieke btw-saldo met officiële belastingcode (*Codice Tributo 6031*).
- **Conto Economico & Balans**: Winst- en verliesrekening ex art. 2425 Codice Civile, inclusief automatische reservering voor vennootschapsbelasting (**IRES 24%** en **IRAP 3,9%**).

### D. Mobiele Smartphone App (`/mobile`)
- Onderweg ritten en offertes invoeren met geoptimaliseerde touch-knoppen.
- Direct de offerte downloaden als PDF of met 1 tik doorsturen naar de eigen e-mail of via WhatsApp delen.
- Geleverde ritten onderweg direct factureren met de Factureer-knop.
- KPI-dashboard met actieve ritten en omzet.

---

## 5. Connectiviteit & Veiligheid
- **Data Soevereiniteit**: Alle dossiers, bedragen en facturen blijven 100% op uw eigen computer in `transito_tms.db` bewaard. Er worden geen gegevens opgeslagen in externe clouddatabases van derden.
- **Cloudflare Beveiliging**: De communicatie tussen smartphone en pc verloopt over een met TLS/SSL versleutelde HTTPS-verbinding via Cloudflare. Er hoeven geen routers of modems opengezet te worden.
- **Offerte Archivering**: Alle verzonden offertes en facturen zijn per dossier terug te vinden, inclusief datum en tijdstip van verzending.
