"""
Script om een professioneel Word-document (.docx) te genereren
met de volledige architectuur, opbouw en tools van de Transito TMS applicatie.
100% pure Python Standard Library (zipfile, xml).
"""

import zipfile
import io
import os
from datetime import datetime

def create_transito_docx(output_path: str):
    # XML templates
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>"""

    root_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

    doc_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

    styles_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:docDefaults>
    <w:rPrDefault>
      <w:rPr>
        <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/>
        <w:sz w:val="22"/>
        <w:szCs w:val="22"/>
        <w:color w:val="1E293B"/>
      </w:rPr>
    </w:rPrDefault>
  </w:docDefaults>
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
    <w:pPr>
      <w:spacing w:after="160" w:line="276" w:lineRule="auto"/>
    </w:pPr>
  </w:style>
</w:styles>"""

    # Helper functions for WordProcessingML
    def escape_xml(s):
        if not s:
            return ""
        return (str(s)
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&apos;"))

    def make_p(text="", bold=False, italic=False, color="1E293B", size=22, space_after=140, align="left", bullet=False):
        b_tag = "<w:b/>" if bold else ""
        i_tag = "<w:i/>" if italic else ""
        jc_tag = f'<w:jc w:val="{align}"/>' if align != "left" else ""
        num_pr = """<w:pPr><w:pStyle w:val="ListParagraph"/><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr></w:pPr>""" if bullet else ""
        bullet_char = "•  " if bullet else ""

        p_pr = f"""<w:pPr>
          {jc_tag}
          <w:spacing w:after="{space_after}" w:line="276" w:lineRule="auto"/>
        </w:pPr>"""

        run = f"""<w:r>
          <w:rPr>
            {b_tag}
            {i_tag}
            <w:color w:val="{color}"/>
            <w:sz w:val="{size}"/>
            <w:szCs w:val="{size}"/>
          </w:rPr>
          <w:t xml:space="preserve">{bullet_char}{escape_xml(text)}</w:t>
        </w:r>"""

        return f"<w:p>{p_pr}{run}</w:p>"

    def make_heading(text, level=1):
        if level == 1:
            size = 36
            color = "1E3A8A" # Deep navy
            space_after = 200
            space_before = 360
        elif level == 2:
            size = 28
            color = "2563EB" # Royal blue
            space_after = 160
            space_before = 280
        else:
            size = 24
            color = "0F766E" # Teal
            space_after = 120
            space_before = 200

        return f"""<w:p>
          <w:pPr>
            <w:spacing w:before="{space_before}" w:after="{space_after}"/>
          </w:pPr>
          <w:r>
            <w:rPr>
              <w:b/>
              <w:color w:val="{color}"/>
              <w:sz w:val="{size}"/>
              <w:szCs w:val="{size}"/>
            </w:rPr>
            <w:t>{escape_xml(text)}</w:t>
          </w:r>
        </w:p>"""

    def make_table(headers, rows):
        # XML Table with styling and borders
        tbl_pr = """<w:tblPr>
          <w:tblW w:w="9400" w:type="dxa"/>
          <w:tblBorders>
            <w:top w:val="single" w:sz="6" w:space="0" w:color="CBD5E1"/>
            <w:left w:val="none"/>
            <w:bottom w:val="single" w:sz="6" w:space="0" w:color="CBD5E1"/>
            <w:right w:val="none"/>
            <w:insideH w:val="single" w:sz="4" w:space="0" w:color="E2E8F0"/>
            <w:insideV w:val="none"/>
          </w:tblBorders>
          <w:tblCellMar>
            <w:top w:w="120" w:type="dxa"/>
            <w:left w:w="160" w:type="dxa"/>
            <w:bottom w:w="120" w:type="dxa"/>
            <w:right w:w="160" w:type="dxa"/>
          </w:tblCellMar>
        </w:tblPr>"""

        # Header Row
        tr_head = "<w:tr><w:trPr><w:tblHeader/><w:cantSplit/></w:trPr>"
        for h in headers:
            tc = f"""<w:tc>
              <w:tcPr>
                <w:shd w:val="clear" w:color="auto" w:fill="F1F5F9"/>
              </w:tcPr>
              <w:p>
                <w:pPr><w:spacing w:after="60"/></w:pPr>
                <w:r>
                  <w:rPr><w:b/><w:color w:val="0F172A"/><w:sz w:val="20"/></w:rPr>
                  <w:t>{escape_xml(h)}</w:t>
                </w:r>
              </w:p>
            </w:tc>"""
            tr_head += tc
        tr_head += "</w:tr>"

        # Data Rows
        tr_rows = ""
        for idx, row in enumerate(rows):
            fill = 'w:fill="F8FAFC"' if idx % 2 == 1 else 'w:fill="FFFFFF"'
            tr = f"<w:tr><w:trPr><w:cantSplit/></w:trPr>"
            for c_idx, cell in enumerate(row):
                bold = (c_idx == 0)
                b_tag = "<w:b/>" if bold else ""
                color = "0F172A" if bold else "334155"
                tc = f"""<w:tc>
                  <w:tcPr>
                    <w:shd w:val="clear" w:color="auto" {fill}/>
                  </w:tcPr>
                  <w:p>
                    <w:pPr><w:spacing w:after="60"/></w:pPr>
                    <w:r>
                      <w:rPr>{b_tag}<w:color w:val="{color}"/><w:sz w:val="19"/></w:rPr>
                      <w:t>{escape_xml(cell)}</w:t>
                    </w:r>
                  </w:p>
                </w:tc>"""
                tr += tc
            tr += "</w:tr>"
            tr_rows += tr

        return f"<w:tbl>{tbl_pr}{tr_head}{tr_rows}</w:tbl><w:p><w:pPr><w:spacing w:after=\"160\"/></w:pPr></w:p>"

    # Build Document Body
    body_parts = []

    # Title & Subtitle
    body_parts.append("""<w:p>
      <w:pPr>
        <w:spacing w:before="0" w:after="80"/>
      </w:pPr>
      <w:r>
        <w:rPr>
          <w:b/>
          <w:color w:val="1E3A8A"/>
          <w:sz w:val="52"/>
          <w:szCs w:val="52"/>
        </w:rPr>
        <w:t>Transito TMS &amp; SDI Facturatie</w:t>
      </w:r>
    </w:p>""")

    body_parts.append("""<w:p>
      <w:pPr>
        <w:spacing w:after="240"/>
      </w:pPr>
      <w:r>
        <w:rPr>
          <w:b/>
          <w:color w:val="2563EB"/>
          <w:sz w:val="28"/>
        </w:rPr>
        <w:t>Systeemopbouw, Architectuur &amp; Tools Overzicht</w:t>
      </w:r>
    </w:p>""")

    # Metadata banner
    body_parts.append(make_p(f"Gegenereerd op: {datetime.now().strftime('%d-%m-%Y')}  |  Versie: 2.4 Productie  |  Locatie: PC Lokaal + Cloudflare Tunnel", italic=True, color="64748B", size=18, space_after=300))

    # Hoofdstuk 1: Wat doet deze applicatie?
    body_parts.append(make_heading("1. Doel & Bedrijfsmodel van de Applicatie", level=1))
    body_parts.append(make_p("De applicatie is speciaal ontworpen en ingericht voor een transportintermediair / vrachtmakelaar / agent (in het Italiaans: 'intermediario dei trasporti' of 'procacciatore d'affari') gevestigd in Italië, die optreedt namens een vast partner-transportbedrijf."))
    body_parts.append(make_p("Het operationele en fiscale model werkt als volgt:"))
    body_parts.append(make_p("Verlader (Opdrachtgever): Vraagt een transport aan. Jij stelt een vrachtofferte op. Na akkoord betaalt de verlader het volledige vrachttarief rechtstreeks aan het partner-transportbedrijf.", bullet=True))
    body_parts.append(make_p("Partner-Transportbedrijf: Voert het fysieke transport uit en factureert de vracht aan de verlader.", bullet=True))
    body_parts.append(make_p("Jouw Onderneming (Intermediair): Heeft géén eigen vrachtwagens en rijdt niet zelf. Jij brengt een bemiddelingsprovisie (standaard 10% of vast bedrag) in rekening bij het transportbedrijf via officiële Italiaanse elektronische facturen (FatturaPA FPR12 via SDI).", bullet=True))
    body_parts.append(make_p("Btw-vrijstelling & Verlegging: Conform de Italiaanse wetgeving valt de commissie onder Art. 7-ter DPR 633/72 (Natura N6, btw-verlegd naar EU/NL) of Art. 9 DPR 633/72 (Natura N3.2, niet belastbaar bij internationaal Italiaans vervoer).", bullet=True))

    # Hoofdstuk 2: Systeemarchitectuur & Bestanden
    body_parts.append(make_heading("2. Systeemarchitectuur & Bestandsstructuur", level=1))
    body_parts.append(make_p("De applicatie is gebouwd volgens een robuust 'Zero-External-Pip' principe. De volledige backend draait op de pure Python Standard Library zonder zware externe dependencies. Dit garandeert maximale stabiliteit, razendsnelle opstarttijden en volledige onafhankelijkheid van verouderende pip-pakketten."))

    file_rows = [
        ["server.py", "Centrale HTTP REST API backend. Handelt alle API-routes, sessies, PDF-downloads en e-mailverzendingen af."],
        ["database.py", "SQLite databasebeheer. Bevat automatische schemamigraties, tabellen voor ritten, facturen, partijen en OIC-boekhouding."],
        ["pdf_generator.py", "Pure Python PDF 1.4 vector generator. Produceert officiële A4 PDF's van offertes en commissiefacturen."],
        ["sdi_generator.py", "FatturaPA FPR12 XML generator. Genereert conforme SDI-facturen met alle Italiaanse fiscale velden."],
        ["email_sender.py", "SMTP & PEC mailclient. Verzendt professionele HTML/tekst e-mails met automatische PDF- en XML-bijlagen."],
        ["transito_tms.db", "Lokale SQLite database waarin alle dossiers, offertes, facturen en instellingen veilig op de eigen pc worden bewaard."],
        ["cloudflared.exe", "Cloudflare tunnel client. Creëert een veilige end-to-end versleutelde HTTPS-tunnel naar de smartphone."],
        ["tunnel_url.txt", "Houdt automatisch de actuele live Cloudflare URL bij."],
        ["static/index.html", "Volledig kantoordashboard (Single Page App) voor desktop pc met tabs voor ritten, facturen, SDI en boekhouding."],
        ["static/app.js", "Desktop frontend logica, data-synchronisatie, berekeningen, grafieken en interacties."],
        ["static/mobile.html", "Touch-geoptimaliseerde mobiele web-app voor iPhone en Android met grote knoppen en PWA-ondersteuning."],
        ["static/mobile.js", "Mobiele interacties, touch targets, live provisieberekening, WhatsApp delen en PDF-downloads."],
        ["start.bat / run_online.py", "Eén-klik Windows opstartbestanden die server en Cloudflare tunnel synchroon starten."]
    ]
    body_parts.append(make_table(["Bestand / Module", "Functie & Verantwoordelijkheid"], file_rows))

    # Hoofdstuk 3: Overzicht van Tools & Technologieën
    body_parts.append(make_heading("3. Overzicht van Gebruikte Tools & Technologieën", level=1))
    body_parts.append(make_p("In onderstaande tabel staan alle toegepaste tools, bibliotheken en protocollen samengevat:"))

    tool_rows = [
        ["Backend Runtime", "Python 3 Standard Library", "Geen pip packages nodig; gebruikt http.server, urllib, json, sqlite3, smtplib, email."],
        ["Database Engine", "SQLite3", "Betrouwbare serverless SQL database; data staat 100% lokaal op de eigen harde schijf."],
        ["PDF Engine", "Pure Python PDF 1.4 Builder", "Zelfgebouwde PDF generator met WinAnsiEncoding, tabellen, vectorlijnen en CMR-clausules."],
        ["SDI XML Engine", "FatturaPA v1.2.2 (FPR12)", "Gereed voor Sistema di Interscambio; automatische Art. 7-ter / Art. 9 codering."],
        ["E-mail / SMTP", "Python smtplib + MIME", "Gekoppeld met live Gmail SMTP (app-wachtwoord) en optionele Italiaanse PEC-ondersteuning."],
        ["Desktop Styling", "Tailwind CSS + FontAwesome 6", "Moderne, overzichtelijke gebruikersinterface met duidelijke kleurcodes en iconen."],
        ["Grafieken & KPI", "Chart.js", "Visuele weergave van ritvolumes, provisiepercentages en maandelijkse provisie-ontwikkeling."],
        ["Mobiele App (PWA)", "HTML5 + Tailwind + PWA Manifest", "Progressive Web App; kan direct via 'Zet op beginscherm' als app op de telefoon worden geïnstalleerd."],
        ["Tunneling & SSL", "Cloudflare Tunnel (cloudflared)", "Wereldwijde HTTPS toegang zonder port-forwarding of router firewall aanpassingen."],
        ["Versiebeheer", "Git & GitHub", "Veilige private backup op GitHub (admeijs-sys/transito-tms)."]
    ]
    body_parts.append(make_table(["Categorie", "Tool / Technologie", "Toelichting & Doel"], tool_rows))

    # Hoofdstuk 4: Hoofdmodules & Functionaliteiten
    body_parts.append(make_heading("4. De Belangrijkste Modules in Detail", level=1))

    body_parts.append(make_heading("A. Bemiddelingsopdrachten & Offertes (Preventivo Trasporto)", level=2))
    body_parts.append(make_p("Offerte of Direct Aanmelden: Bij het invoeren van een rit kun je kiezen tussen een vrijblijvende vrachtofferte voor de klant of een definitieve aanmelding.", bullet=True))
    body_parts.append(make_p("4 Flexibele Provisiemodellen: Percentage (bijv. 10%), Vaste Fee (bijv. € 200), Marge (verschil tussen verlader- en vervoerderstarief) of Vrije Invoer.", bullet=True))
    body_parts.append(make_p("Automatisch E-mailen: Bij het opslaan van een offerte wordt deze direct per e-mail met het officiële A4 PDF-document verzonden naar admeijs@gmail.com.", bullet=True))
    body_parts.append(make_p("A4 PDF Document: Compleet met laad- en losadres, CMR-voorwaarden, geldigheidstermijn en akkoordblok.", bullet=True))

    body_parts.append(make_heading("B. Elektronische Facturatie (SDI FatturaPA)", level=2))
    body_parts.append(make_p("1-Klik Facturatie: Individuele ritten factureren of openstaande ritten bundelen op één maandelijkse verzamelfactuur aan het transportbedrijf.", bullet=True))
    body_parts.append(make_p("Fiscale Foutpreventie: Automatische Natura-codes (N6 voor EU, N3.2 voor internationaal binnenlands transport).", bullet=True))
    body_parts.append(make_p("XML & PDF Export: Zowel het officiële .xml bestand als het opgemaakte A4 PDF factuursjabloon kunnen direct worden ingezien en gedownload.", bullet=True))
    body_parts.append(make_p("SDI Simulatie: Volg de status van verzonden commissiefacturen (Gegenereerd, Verzonden, Geaccepteerd / Notifica di avvenuta consegna).", bullet=True))

    body_parts.append(make_heading("C. Italiaanse Boekhouding (Contabilità e Fisco)", level=2))
    body_parts.append(make_p("Registro IVA Vendite (art. 23 DPR 633/72): Wettelijk verkoopregister van alle uitgaande provisiefacturen.", bullet=True))
    body_parts.append(make_p("Registro IVA Acquisti (art. 25 DPR 633/72): Inkoopregister van bedrijfskosten met aftrekbare btw.", bullet=True))
    body_parts.append(make_p("Liquidazione IVA & F24: Berekening van het periodieke btw-saldo met officiële belastingcode (Codice Tributo 6031).", bullet=True))
    body_parts.append(make_p("Conto Economico & Balans: Winst- en verliesrekening ex art. 2425 Codice Civile, inclusief automatische reservering voor vennootschapsbelasting (IRES 24% en IRAP 3,9%).", bullet=True))

    body_parts.append(make_heading("D. Mobiele Smartphone App (/mobile)", level=2))
    body_parts.append(make_p("Onderweg ritten en offertes invoeren met geoptimaliseerde touch-knoppen.", bullet=True))
    body_parts.append(make_p("Direct de offerte downloaden als PDF of met 1 tik doorsturen naar de eigen e-mail of via WhatsApp delen.", bullet=True))
    body_parts.append(make_p("Geleverde ritten onderweg direct factureren met de Factureer-knop.", bullet=True))
    body_parts.append(make_p("KPI-dashboard met actieve ritten en omzet.", bullet=True))

    # Hoofdstuk 5: Connectiviteit & Beveiliging
    body_parts.append(make_heading("5. Connectiviteit & Veiligheid", level=1))
    body_parts.append(make_p("Data Soevereiniteit: Alle dossiers, bedragen en facturen blijven 100% op uw eigen computer in transito_tms.db bewaard. Er worden geen gegevens opgeslagen in externe clouddatabases van derden.", bullet=True))
    body_parts.append(make_p("Cloudflare Beveiliging: De communicatie tussen smartphone en pc verloopt over een met TLS/SSL versleutelde HTTPS-verbinding via Cloudflare. Er hoeven geen routers of modems opengezet te worden.", bullet=True))
    body_parts.append(make_p("Offerte Archivering: Alle verzonden offertes en facturen zijn per dossier terug te vinden, inclusief datum en tijdstip van verzending.", bullet=True))

    # Construct complete document.xml
    doc_body = "".join(body_parts)
    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
            xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <w:body>
    {doc_body}
    <w:sectPr>
      <w:pgSz w:w="11906" w:h="16838"/>
      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/>
    </w:sectPr>
  </w:body>
</w:document>"""

    # Build Zip File (.docx)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", root_rels)
        z.writestr("word/_rels/document.xml.rels", doc_rels)
        z.writestr("word/styles.xml", styles_xml)
        z.writestr("word/document.xml", document_xml)

    docx_bytes = buf.getvalue()
    with open(output_path, "wb") as f:
        f.write(docx_bytes)

    print(f"Document succesvol gegenereerd: {output_path} ({len(docx_bytes)} bytes)")
    return docx_bytes

if __name__ == "__main__":
    out_dir = os.path.dirname(os.path.abspath(__file__))
    target_docx = os.path.join(out_dir, "Transito_App_Opbouw_en_Architectuur.docx")
    target_doc = os.path.join(out_dir, "Transito_App_Opbouw_en_Architectuur.doc")
    parent_docx = os.path.abspath(os.path.join(out_dir, "..", "Transito_App_Opbouw_en_Architectuur.docx"))
    
    b = create_transito_docx(target_docx)
    # Ook opslaan als .doc kopie zodat elk Word-programma het opent ongeacht extensie
    with open(target_doc, "wb") as f:
        f.write(b)
    # En in bovenliggende map Johan
    try:
        with open(parent_docx, "wb") as f:
            f.write(b)
        print(f"Kopie opgeslagen in hoofdmap: {parent_docx}")
    except Exception as e:
        print(f"Kon kopie niet opslaan in hoofdmap: {e}")
