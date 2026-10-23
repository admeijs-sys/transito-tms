import os

html_content = """<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Transito TMS & SDI - Systeemopbouw en Architectuur</title>
<style>
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    line-height: 1.6;
    color: #1e293b;
    max-width: 900px;
    margin: 40px auto;
    padding: 0 24px;
    background-color: #f8fafc;
  }
  .doc-container {
    background: #ffffff;
    padding: 48px;
    border-radius: 12px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1);
  }
  h1 {
    color: #1e3a8a;
    font-size: 28px;
    margin-bottom: 8px;
    border-bottom: 2px solid #e2e8f0;
    padding-bottom: 12px;
  }
  h2 {
    color: #1d4ed8;
    font-size: 20px;
    margin-top: 32px;
    margin-bottom: 12px;
  }
  h3 {
    color: #334155;
    font-size: 16px;
    margin-top: 20px;
    margin-bottom: 8px;
  }
  .meta {
    color: #64748b;
    font-size: 14px;
    margin-bottom: 24px;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    margin: 20px 0;
    font-size: 14px;
  }
  th, td {
    padding: 10px 14px;
    text-align: left;
    border-bottom: 1px solid #e2e8f0;
  }
  th {
    background-color: #f1f5f9;
    color: #0f172a;
    font-weight: 600;
  }
  tr:hover {
    background-color: #f8fafc;
  }
  .badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 9999px;
    font-size: 12px;
    font-weight: 500;
    background-color: #e0f2fe;
    color: #0369a1;
  }
  code {
    background: #f1f5f9;
    padding: 2px 6px;
    border-radius: 4px;
    font-family: monospace;
    font-size: 13px;
    color: #0f172a;
  }
  ul, ol {
    padding-left: 24px;
  }
  li {
    margin-bottom: 6px;
  }
  .highlight-box {
    background-color: #eff6ff;
    border-left: 4px solid #3b82f6;
    padding: 16px;
    margin: 20px 0;
    border-radius: 0 8px 8px 0;
  }
</style>
</head>
<body>
<div class="doc-container">
  <h1>Transito TMS & SDI Facturatie 🤝🇮🇹</h1>
  <p class="meta"><strong>Document:</strong> Systeemopbouw, Architectuur & Tools Overzicht | <strong>Datum:</strong> 23 oktober 2026 | <strong>Status:</strong> Productie v2.4</p>

  <h2>1. Doel & Bedrijfsmodel van de Applicatie</h2>
  <p>De applicatie is speciaal ontworpen en ingericht voor een <strong>transportintermediair / vrachtmakelaar / agent</strong> (<em>intermediario dei trasporti</em> of <em>procacciatore d'affari</em>) gevestigd in Italië, die optreedt namens een vast <strong>partner-transportbedrijf</strong>.</p>
  
  <div class="highlight-box">
    <h3 style="margin-top:0;">Hoe het operationele en fiscale model werkt:</h3>
    <ol>
      <li><strong>Verlader (Opdrachtgever)</strong>: Vraagt een transport aan. Jij stelt een vrachtofferte op. Na akkoord betaalt de verlader het volledige vrachttarief rechtstreeks aan het partner-transportbedrijf.</li>
      <li><strong>Partner-Transportbedrijf</strong>: Voert het fysieke transport uit en factureert de vracht aan de verlader.</li>
      <li><strong>Jouw Onderneming (Intermediair)</strong>: Heeft géén eigen vrachtwagens en rijdt niet zelf. Jij brengt een bemiddelingsprovisie (standaard 10% of vast bedrag) in rekening bij het transportbedrijf via officiële Italiaanse elektronische facturen (<strong>FatturaPA FPR12 via SDI</strong>).</li>
      <li><strong>Btw-vrijstelling & Verlegging</strong>: Conform de Italiaanse wetgeving valt de commissie onder:
        <ul>
          <li><strong>Artikel 7-ter DPR 633/72</strong> (<em>Inversione contabile</em>, Natura <code>N6</code>, btw-verlegd naar EU/NL transportbedrijf).</li>
          <li><strong>Artikel 9 DPR 633/72</strong> (<em>Non imponibile</em>, Natura <code>N3.2</code>, bij internationaal Italiaans vervoer).</li>
        </ul>
      </li>
    </ol>
  </div>

  <h2>2. Systeemarchitectuur & Bestandsstructuur</h2>
  <p>De applicatie is gebouwd volgens een robuust <strong>Zero-External-Pip</strong> principe. De volledige backend draait op de pure <strong>Python Standard Library</strong> zonder zware externe dependencies.</p>

  <table>
    <thead>
      <tr>
        <th style="width: 25%;">Bestand / Module</th>
        <th>Functie & Verantwoordelijkheid</th>
      </tr>
    </thead>
    <tbody>
      <tr><td><code>server.py</code></td><td>Centrale HTTP REST API backend. Handelt alle API-routes, sessies, PDF-downloads en e-mailverzendingen af.</td></tr>
      <tr><td><code>database.py</code></td><td>SQLite databasebeheer met automatische migraties, tabellen voor ritten, facturen, partijen en OIC-boekhouding.</td></tr>
      <tr><td><code>pdf_generator.py</code></td><td>Pure Python PDF 1.4 vector generator. Produceert officiële A4 PDF's van offertes en commissiefacturen.</td></tr>
      <tr><td><code>sdi_generator.py</code></td><td>FatturaPA FPR12 XML generator. Genereert conforme SDI-facturen met alle Italiaanse fiscale velden.</td></tr>
      <tr><td><code>email_sender.py</code></td><td>SMTP & PEC mailclient. Verzendt professionele HTML/tekst e-mails met automatische PDF- en XML-bijlagen.</td></tr>
      <tr><td><code>transito_tms.db</code></td><td>Lokale SQLite database waarin alle dossiers, offertes, facturen en instellingen veilig op de eigen pc worden bewaard.</td></tr>
      <tr><td><code>cloudflared.exe</code></td><td>Cloudflare tunnel client. Creëert een veilige end-to-end versleutelde HTTPS-tunnel naar de smartphone.</td></tr>
      <tr><td><code>tunnel_url.txt</code></td><td>Houdt automatisch de actuele live Cloudflare URL bij.</td></tr>
      <tr><td><code>static/index.html</code></td><td>Volledig kantoordashboard (Single Page App) voor desktop pc met tabs voor ritten, facturen, SDI en boekhouding.</td></tr>
      <tr><td><code>static/app.js</code></td><td>Desktop frontend logica, data-synchronisatie, berekeningen, grafieken en interacties.</td></tr>
      <tr><td><code>static/mobile.html</code></td><td>Touch-geoptimaliseerde mobiele web-app voor iPhone en Android met grote knoppen en PWA-ondersteuning.</td></tr>
      <tr><td><code>static/mobile.js</code></td><td>Mobiele interacties, touch targets, live provisieberekening, WhatsApp delen en PDF-downloads.</td></tr>
      <tr><td><code>start.bat / run_online.py</code></td><td>Eén-klik Windows opstartbestanden die server en Cloudflare tunnel synchroon starten.</td></tr>
    </tbody>
  </table>

  <h2>3. Overzicht van Gebruikte Tools & Technologieën</h2>
  <table>
    <thead>
      <tr>
        <th style="width: 22%;">Categorie</th>
        <th style="width: 28%;">Tool / Technologie</th>
        <th>Toelichting & Doel</th>
      </tr>
    </thead>
    <tbody>
      <tr><td><span class="badge">Backend Runtime</span></td><td><strong>Python 3 Standard Library</strong></td><td>Geen pip packages nodig; gebruikt http.server, urllib, json, sqlite3, smtplib, email.</td></tr>
      <tr><td><span class="badge">Database Engine</span></td><td><strong>SQLite3</strong></td><td>Betrouwbare serverless SQL database; data staat 100% lokaal op de eigen harde schijf.</td></tr>
      <tr><td><span class="badge">PDF Engine</span></td><td><strong>Pure Python PDF 1.4 Builder</strong></td><td>Zelfgebouwde vector PDF generator met WinAnsiEncoding, tabellen en CMR-clausules.</td></tr>
      <tr><td><span class="badge">SDI XML Engine</span></td><td><strong>FatturaPA v1.2.2 (FPR12)</strong></td><td>Gereed voor Sistema di Interscambio; automatische Art. 7-ter / Art. 9 codering.</td></tr>
      <tr><td><span class="badge">E-mail / SMTP</span></td><td><strong>Python smtplib + MIME</strong></td><td>Gekoppeld met live Gmail SMTP (app-wachtwoord) en optionele Italiaanse PEC-ondersteuning.</td></tr>
      <tr><td><span class="badge">Desktop Styling</span></td><td><strong>Tailwind CSS + FontAwesome 6</strong></td><td>Moderne, overzichtelijke gebruikersinterface met duidelijke kleurcodes en iconen.</td></tr>
      <tr><td><span class="badge">Grafieken & KPI</span></td><td><strong>Chart.js</strong></td><td>Visuele weergave van ritvolumes, provisiepercentages en maandelijkse provisie-ontwikkeling.</td></tr>
      <tr><td><span class="badge">Mobiele App (PWA)</span></td><td><strong>HTML5 + Tailwind + PWA Manifest</strong></td><td>Progressive Web App; direct installeerbaar via 'Zet op beginscherm' op iPhone en Android.</td></tr>
      <tr><td><span class="badge">Tunneling & SSL</span></td><td><strong>Cloudflare Tunnel (cloudflared)</strong></td><td>Wereldwijde HTTPS toegang zonder port-forwarding of router firewall aanpassingen.</td></tr>
      <tr><td><span class="badge">Versiebeheer</span></td><td><strong>Git & GitHub</strong></td><td>Veilige private backup op GitHub (admeijs-sys/transito-tms).</td></tr>
    </tbody>
  </table>

  <h2>4. De Belangrijkste Modules in Detail</h2>
  <h3>A. Bemiddelingsopdrachten & Offertes (Preventivo Trasporto)</h3>
  <ul>
    <li><strong>Offerte of Direct Aanmelden</strong>: Keuze tussen een vrijblijvende vrachtofferte voor de klant of een definitieve aanmelding.</li>
    <li><strong>4 Flexibele Provisiemodellen</strong>: Percentage (standaard 10%), Vaste Fee, Marge (verschil verlader/vervoerder), Vrije Invoer.</li>
    <li><strong>Directe Offerte E-mail</strong>: Offerte kan met één klik als professionele PDF doorgemaild worden naar de klant én in kopie naar de eigen administratie.</li>
  </ul>

  <h3>B. Facturatie & Officiële SDI Export</h3>
  <ul>
    <li><strong>Consolidatie</strong>: Bundel meerdere voltooide ritten op één verzamelfactuur voor de transporteur.</li>
    <li><strong>SDI FatturaPA FPR12</strong>: 100% conforme XML met Codice Destinatario, Codice Fiscale en Partita IVA.</li>
    <li><strong>Fiscale Verlegging</strong>: Automatische vermelding van Artikel 7-ter DPR 633/72 of Artikel 9 DPR 633/72.</li>
  </ul>

  <h3>C. OIC-Boekhouding & Financiële Controle</h3>
  <ul>
    <li><strong>Dubbel Boekhouden</strong>: Journaalposten volgens de Italiaanse OIC-standaarden (Attivo, Passivo, Costi, Ricavi).</li>
    <li><strong>Geautomatiseerde Boekingen</strong>: Factuurverzending, provisieontvangsten en betalingen worden direct verwerkt.</li>
  </ul>

  <h3>D. Mobiele PWA App</h3>
  <ul>
    <li><strong>Geoptimaliseerd voor Smartphone</strong>: Grote, direct tikbare touch-targets, gestroomlijnd mobiel formulier.</li>
    <li><strong>Volledige Mobiliteit</strong>: Onderweg vanaf de smartphone offertes maken, ritten bekijken en PDF's downloaden.</li>
  </ul>
</div>
</body>
</html>
"""

p1 = r'G:\Mijn Drive\mijn gemini opslag\johan\Transito_App_Opbouw_en_Architectuur.html'
p2 = r'G:\Mijn Drive\mijn gemini opslag\johan\transito-tms-sdi\Transito_App_Opbouw_en_Architectuur.html'

with open(p1, 'w', encoding='utf-8') as f:
    f.write(html_content)
with open(p2, 'w', encoding='utf-8') as f:
    f.write(html_content)

print('HTML documenten opgeslagen.')
