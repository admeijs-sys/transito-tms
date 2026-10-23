"""
Script om een professioneel Excel/Google Sheets (.xlsx) werkblad te genereren
met de volledige architectuur, bestandsopbouw en tools van de Transito TMS applicatie.
100% pure Python Standard Library (zipfile, xml).
Direct compatibel met Google Sheets en Microsoft Excel.
"""

import zipfile
import io
import os

def escape_xml(s):
    if not s:
        return ""
    return (str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;"))

def col_letter(col_idx):
    # 1 -> A, 2 -> B, etc.
    result = ""
    while col_idx > 0:
        col_idx, remainder = divmod(col_idx - 1, 26)
        result = chr(65 + remainder) + result
    return result

def make_sheet_xml(rows_data, col_widths=None):
    # rows_data is list of lists. Each cell can be a string or a tuple (value, style_idx)
    cols_xml = ""
    if col_widths:
        cols_xml = "<cols>"
        for idx, w in enumerate(col_widths, 1):
            cols_xml += f'<col min="{idx}" max="{idx}" width="{w}" customWidth="1"/>'
        cols_xml += "</cols>"

    sheet_data = "<sheetData>"
    for r_idx, row in enumerate(rows_data, 1):
        row_xml = f'<row r="{r_idx}">'
        for c_idx, cell in enumerate(row, 1):
            val = ""
            s_idx = 0
            if isinstance(cell, tuple):
                val = cell[0]
                s_idx = cell[1]
            else:
                val = cell
            
            c_ref = f"{col_letter(c_idx)}{r_idx}"
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                cell_xml = f'<c r="{c_ref}" s="{s_idx}"><v>{val}</v></c>'
            else:
                cell_xml = f'<c r="{c_ref}" t="inlineStr" s="{s_idx}"><is><t>{escape_xml(val)}</t></is></c>'
            row_xml += cell_xml
        row_xml += "</row>"
        sheet_data += row_xml
    sheet_data += "</sheetData>"

    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  {cols_xml}
  {sheet_data}
</worksheet>"""

def create_transito_sheets(output_path: str):
    # Content Types
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/worksheets/sheet3.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>"""

    root_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""

    wb_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet3.xml"/>
  <Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

    workbook_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="1. Bedrijfsmodel &amp; Info" sheetId="1" r:id="rId1"/>
    <sheet name="2. Bestandsstructuur" sheetId="2" r:id="rId2"/>
    <sheet name="3. Tools &amp; Modules" sheetId="3" r:id="rId3"/>
  </sheets>
</workbook>"""

    # Styles (Fonts, Fills, Borders)
    # Style 0: Normal
    # Style 1: Title (Bold 16pt, Navy)
    # Style 2: Subtitle (11pt, Slate)
    # Style 3: Table Header (Bold 11pt, White text, Navy Blue Fill)
    # Style 4: Bold cell (10pt, Dark)
    # Style 5: Normal cell with border (10pt)
    # Style 6: Alternating row cell with border (10pt, Light Gray fill)
    styles_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="4">
    <font><sz val="10"/><name val="Calibri"/><color rgb="FF1E293B"/></font>
    <font><b/><sz val="16"/><name val="Calibri"/><color rgb="FF1E3A8A"/></font>
    <font><i/><sz val="10"/><name val="Calibri"/><color rgb="FF64748B"/></font>
    <font><b/><sz val="11"/><name val="Calibri"/><color rgb="FFFFFFFF"/></font>
  </fonts>
  <fills count="4">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="gray125"/></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FF1E3A8A"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFF8FAFC"/></patternFill></fill>
  </fills>
  <borders count="2">
    <border><left/><right/><top/><bottom/><diagonal/></border>
    <border>
      <left style="thin"><color rgb="FFE2E8F0"/></left>
      <right style="thin"><color rgb="FFE2E8F0"/></right>
      <top style="thin"><color rgb="FFE2E8F0"/></top>
      <bottom style="thin"><color rgb="FFE2E8F0"/></bottom>
    </border>
  </borders>
  <cellXfs count="7">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
    <xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0"/>
    <xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0"/>
    <xf numFmtId="0" fontId="3" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"/>
    <xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1"/>
    <xf numFmtId="0" fontId="0" fillId="3" borderId="1" xfId="0" applyFill="1" applyBorder="1"/>
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
  </cellXfs>
</styleSheet>"""

    # TABBLAD 1: Bedrijfsmodel & Algemene Info
    sheet1_data = [
        [("Transito TMS & SDI Facturatiesysteem", 1)],
        [("Volledig Architectuuroverzicht & Bedrijfsmodel voor Google Sheets", 2)],
        [],
        [("Onderdeel", 3), ("Rol / Partij", 3), ("Omschrijving & Werking", 3), ("Fiscale Behandeling (Italië)", 3)],
        [("1. De Verlader", 4), ("Opdrachtgever / Klant", 4), ("Vraagt vrachtvervoer aan bij jouw onderneming. Ontvangt een officiële A4 offerte met CMR-condities en betaalt het transport rechtstreeks aan het partner-transportbedrijf.", 4), ("Geen btw-heffing door intermediair. Verlader ontvangt vrachtfactuur rechtstreeks van transportbedrijf.", 4)],
        [("2. Partner Transportbedrijf", 5), ("Vervoerder (Principal)", 5), ("Voert het fysieke wegtransport uit met vrachtwagens. Factureert de verlader voor de vracht en ontvangt periodiek een commissiefactuur van de intermediair.", 5), ("Ontvangt provisiefactuur via SDI. Bij NL-bedrijf: btw-verlegd ex Art. 7-ter DPR 633/72.", 5)],
        [("3. Jouw Onderneming", 4), ("Intermediair (S.r.l. / Agent)", 4), ("Bemiddelt de ritten en werft opdrachten. Bezit géén vrachtwagens. Brengt een bemiddelingscommissie in rekening bij het transportbedrijf (standaard 10% of vaste fee).", 4), ("Officiële FatturaPA XML (FPR12). Verkoopregister Art. 23. Natura N6 (EU) of N3.2 (internationaal).", 4)],
        [("4. Italiaanse Fiscus (SDI)", 5), ("Sistema di Interscambio", 5), ("Ontvangt en verwerkt alle elektronische commissiefacturen. Koppelt via Aruba / SDI API gateway.", 5), ("Conto Economico, Balans, LIPE en Modello F24 (Codice Tributo 6031).", 5)],
        [],
        [("Commissiemodel", 3), ("Berekeningswijze", 3), ("Voorbeeld bij € 2.500 vracht", 3), ("Doel / Toepassing", 3)],
        [("Percentage", 4), ("Vaste formule: Vrachtprijs x Percentage%", 4), ("€ 2.500 x 10% = € 250,00 provisie", 4), ("Standaard voor internationale FTL vrachten.", 4)],
        [("Vaste Fee", 5), ("Vast bedrag per rit ongeacht de vrachtprijs", 5), ("€ 200,00 vaste fee per rit", 5), ("Ideaal bij kortere ritten of vaste pendels.", 5)],
        [("Marge / Spread", 4), ("Verschil: Prijs Verlader minus Prijs Vervoerder", 4), ("€ 2.500 verlader - € 2.200 vervoerder = € 300,00", 4), ("Vrije marktmakelaardij met maximale marge.", 4)],
        [("Vrije Invoer", 5), ("Direct aanpasbaar bedrag per dossier", 5), ("Elk gewenst bedrag direct intypbaar", 5), ("Maatwerk en uitzonderlijke opdrachten.", 5)]
    ]
    sheet1_xml = make_sheet_xml(sheet1_data, col_widths=[28, 28, 65, 45])

    # TABBLAD 2: Bestandsstructuur & Verantwoordelijkheden
    sheet2_data = [
        [("Transito TMS - Bestandsstructuur & Technische Opbouw", 1)],
        [("Overzicht van alle kernbestanden, functies en data-opslag", 2)],
        [],
        [("Bestand / Module", 3), ("Taal / Type", 3), ("Primaire Verantwoordelijkheid", 3), ("Bijzonderheden & Afhankelijkheden", 3)],
        [("server.py", 4), ("Python 3", 4), ("Centrale HTTP REST API backend server.", 4), ("Zero-pip: gebruikt uitsluitend Python Standard Library (http.server, urllib, json).", 4)],
        [("database.py", 5), ("Python / SQLite", 5), ("Databasebeheer, tabellen, schemamigraties en standaarddata.", 5), ("SQLite3 relationele database. Volledig lokaal opgeslagen.", 5)],
        [("pdf_generator.py", 4), ("Python 3", 4), ("Pure Python PDF 1.4 vector generator.", 4), ("Genereert A4 PDF-offertes en facturen zonder ReportLab of Weasyprint.", 4)],
        [("sdi_generator.py", 5), ("Python 3", 5), ("Italiaanse FatturaPA FPR12 XML generator.", 5), ("Voldoet aan de officiële SDI 1.2.2 specificaties (Agenzia delle Entrate).", 5)],
        [("email_sender.py", 4), ("Python 3", 4), ("SMTP e-mailservice met PDF en XML bijlagen.", 4), ("Gekoppeld met live Gmail SMTP (app-wachtwoord) en PEC ondersteuning.", 4)],
        [("transito_tms.db", 5), ("SQLite Database", 5), ("Fysiek databasebestand op de harde schijf.", 5), ("Bevat ritten, offertes, facturen, kosten, contacten en instellingen.", 5)],
        [("cloudflared.exe", 4), ("Executable", 4), ("Cloudflare tunnel client voor wereldwijde HTTPS toegang.", 4), ("Maakt beveiligde verbinding naar smartphone zonder port-forwarding.", 4)],
        [("tunnel_url.txt", 5), ("Tekstbestand", 5), ("Houdt de actieve live Cloudflare URL bij.", 5), ("Wordt bij elke tunnel-herstart automatisch bijgewerkt.", 5)],
        [("static/index.html", 4), ("HTML5 / SPA", 4), ("Desktop kantoordashboard interface.", 4), ("Single Page Application met Tailwind CSS en FontAwesome 6.", 4)],
        [("static/app.js", 5), ("JavaScript (ES6)", 5), ("Frontend logica voor desktop dashboard.", 5), ("Beheert state, filters, calculaties, grafieken en SDI XML inspectie.", 5)],
        [("static/mobile.html", 4), ("HTML5 / PWA", 4), ("Mobiele web-app speciaal ontworpen voor smartphones.", 4), ("Grote touch-knoppen, haptische feedback, PWA 'Zet op beginscherm'.", 4)],
        [("static/mobile.js", 5), ("JavaScript (ES6)", 5), ("Mobiele interactielogica en formuliervalidatie.", 5), ("Directe validatie, offline fallback, WhatsApp delen en PDF-downloads.", 5)],
        [("start.bat / run_online.py", 4), ("Batch / Python", 4), ("Windows opstartbestanden.", 4), ("Start synchroon de lokale backend en de Cloudflare tunnel op.", 4)]
    ]
    sheet2_xml = make_sheet_xml(sheet2_data, col_widths=[28, 20, 50, 60])

    # TABBLAD 3: Tools, Technologieën & Modules
    sheet3_data = [
        [("Transito TMS - Tools, Technologieën & Modulematrix", 1)],
        [("Gedetailleerd overzicht van bibliotheken, versies en functies", 2)],
        [],
        [("Module / Tool", 3), ("Technologie", 3), ("Status / Versie", 3), ("Functie in Transito", 3), ("Voordelen voor Gebruiker", 3)],
        [("Backend Runtime", 4), ("Python 3.12+", 4), ("Standard Library", 4), ("Afhandelen van HTTP verzoeken, REST API, routering.", 4), ("Geen pip-fouten, start razendsnel op elke pc.", 4)],
        [("Database", 5), ("SQLite 3", 5), ("Lokaal bestand", 5), ("Opslag van alle ritten, offertes, facturen en instellingen.", 5), ("100% privacy, geen externe cloudafhankelijkheid.", 5)],
        [("PDF Engine", 4), ("Eigen PDF 1.4 Builder", 4), ("In-house pure Python", 4), ("Vectoriële A4 opmaak voor offertes en facturen.", 4), ("Geen externe dependencies, altijd perfecte A4 printkwaliteit.", 4)],
        [("SDI Facturatie", 5), ("XML FatturaPA FPR12", 5), ("v1.2.2 Italiaanse fiscus", 5), ("Automatisch opstellen van elektronische provisiefacturen.", 5), ("Direct klaar voor verzending aan transportbedrijf / accountant.", 5)],
        [("E-mail Integratie", 4), ("Python smtplib / MIME", 4), ("Gmail SMTP SSL/TLS", 4), ("Automatisch mailen van offertes en facturen met PDF bijlage.", 4), ("Directe verzending naar eigen e-mail (admeijs@gmail.com).", 4)],
        [("Desktop UI", 5), ("Tailwind CSS + FontAwesome", 5), ("CDN v3 / v6.4", 5), ("Overzichtelijk kantoordashboard met tabbladen en modals.", 5), ("Strakke zakelijke interface, eenvoudige bediening.", 5)],
        [("KPI Grafieken", 4), ("Chart.js", 4), ("v4.4 Responsive", 4), ("Visualisatie van omzet, commissies en ritvolumes.", 4), ("Direct inzicht in winstgevendheid per maand.", 4)],
        [("Mobiele App", 5), ("Progressive Web App (PWA)", 5), ("Touch Optimized", 5), ("Smartphone interface voor onderweg ritten invoeren.", 5), ("Grote knoppen, tril-feedback, werkt op iPhone en Android.", 5)],
        [("Beveiligde Tunnel", 4), ("Cloudflare Tunnel", 4), ("cloudflared v2026", 4), ("Wereldwijde HTTPS toegang zonder port-forwarding.", 4), ("Overal ter wereld veilig verbinding met eigen pc via 4G/5G.", 4)],
        [("Versiebeheer", 5), ("Git / GitHub", 5), ("Main branch", 5), ("Automatische back-up en versiebeheer van alle code.", 5), ("Altijd veilige reservekopie in private cloud repository.", 5)]
    ]
    sheet3_xml = make_sheet_xml(sheet3_data, col_widths=[24, 28, 22, 50, 50])

    # Zip alles in een geldig .xlsx bestand
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", root_rels)
        z.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        z.writestr("xl/workbook.xml", workbook_xml)
        z.writestr("xl/styles.xml", styles_xml)
        z.writestr("xl/worksheets/sheet1.xml", sheet1_xml)
        z.writestr("xl/worksheets/sheet2.xml", sheet2_xml)
        z.writestr("xl/worksheets/sheet3.xml", sheet3_xml)

    xlsx_bytes = buf.getvalue()
    with open(output_path, "wb") as f:
        f.write(xlsx_bytes)

    print(f"Excel / Google Sheets werkblad succesvol gegenereerd: {output_path} ({len(xlsx_bytes)} bytes)")
    return xlsx_bytes

if __name__ == "__main__":
    out_dir = os.path.dirname(os.path.abspath(__file__))
    target_xlsx = os.path.join(out_dir, "Transito_App_Opbouw_en_Architectuur.xlsx")
    parent_xlsx = os.path.abspath(os.path.join(out_dir, "..", "Transito_App_Opbouw_en_Architectuur.xlsx"))
    
    b = create_transito_sheets(target_xlsx)
    try:
        with open(parent_xlsx, "wb") as f:
            f.write(b)
        print(f"Kopie opgeslagen in hoofdmap: {parent_xlsx}")
    except Exception as e:
        print(f"Kon kopie niet opslaan in hoofdmap: {e}")
