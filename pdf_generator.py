"""
Transito TMS - PDF Generator Module
Genereert 100% stand-alone, professionele A4 PDF documenten conform de PDF-1.4 standaard.
Geen externe afhankelijkheden nodig (puur Python Standard Library).
"""

from datetime import datetime


class PdfBuilder:
    def __init__(self):
        self.width = 595.28   # A4 breedte in punten (pt)
        self.height = 841.89  # A4 hoogte in punten (pt)
        self.stream = []

    def rgb(self, r, g, b):
        self.stream.append(f"{r:.3f} {g:.3f} {b:.3f} rg")

    def stroke_rgb(self, r, g, b):
        self.stream.append(f"{r:.3f} {g:.3f} {b:.3f} RG")

    def rect(self, x, y, w, h, fill=False, stroke=False, line_width=1.0):
        self.stream.append(f"{line_width:.2f} w")
        self.stream.append(f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re")
        if fill and stroke:
            self.stream.append("B")
        elif fill:
            self.stream.append("f")
        elif stroke:
            self.stream.append("S")

    def line(self, x1, y1, x2, y2, line_width=1.0, r=0.8, g=0.8, b=0.8):
        self.stroke_rgb(r, g, b)
        self.stream.append(f"{line_width:.2f} w")
        self.stream.append(f"{x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S")

    def escape(self, text):
        if not text:
            return ""
        escaped = bytearray()
        for b in str(text).encode("cp1252", "replace"):
            if b in (92, 40, 41):  # \\, (, )
                escaped.extend([92, b])
            else:
                escaped.append(b)
        return escaped.decode("latin1")

    def text(self, txt, x, y, font="F1", size=10, r=0.1, g=0.15, b=0.2):
        self.rgb(r, g, b)
        esc = self.escape(txt)
        self.stream.append(f"BT /{font} {size} Tf {x:.2f} {y:.2f} Td ({esc}) Tj ET")

    def text_right(self, txt, right_x, y, font="F1", size=10, r=0.1, g=0.15, b=0.2, approx_char_w=None):
        # Benaderde uitlijning naar rechts
        w = approx_char_w or (size * 0.52)
        txt_w = len(str(txt)) * w
        self.text(txt, right_x - txt_w, y, font=font, size=size, r=r, g=g, b=b)

    def build_pdf(self) -> bytes:
        content_bytes = "\n".join(self.stream).encode("latin1")

        objects = []
        def add(obj_str):
            objects.append(obj_str)
            return len(objects)

        # 1: Catalog
        add("<< /Type /Catalog /Pages 2 0 R >>")
        # 2: Pages
        add("<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
        # 3: Page
        # Fonts: F1=Helvetica, F2=Helvetica-Bold, F3=Helvetica-Oblique, F4=Courier, F5=Courier-Bold
        fonts = """<<
            /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>
            /F2 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>
            /F3 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Oblique /Encoding /WinAnsiEncoding >>
            /F4 << /Type /Font /Subtype /Type1 /BaseFont /Courier /Encoding /WinAnsiEncoding >>
            /F5 << /Type /Font /Subtype /Type1 /BaseFont /Courier-Bold /Encoding /WinAnsiEncoding >>
        >>"""
        add(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {self.width:.2f} {self.height:.2f}] /Contents 4 0 R /Resources << /Font {fonts} >> >>")
        # 4: Contents
        add(f"<< /Length {len(content_bytes)} >>\nstream\n" + content_bytes.decode("latin1") + "\nendstream")

        out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = []
        for i, obj in enumerate(objects, 1):
            offsets.append(len(out))
            out.extend(f"{i} 0 obj\n{obj}\nendobj\n".encode("latin1"))

        xref_pos = len(out)
        out.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("latin1"))
        for off in offsets:
            out.extend(f"{off:010d} 00000 n \n".encode("latin1"))

        out.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF".encode("latin1"))
        return bytes(out)


def generate_invoice_pdf(invoice: dict, company: dict, orders: list = None) -> bytes:
    """
    Genereert een officiële, printklare Copia di Cortesia Commissiefactuur in A4 PDF-formaat.
    """
    pdf = PdfBuilder()
    orders = orders or []

    inv_num = invoice.get("invoice_number", "PROV-2026-001")
    inv_date = invoice.get("date", datetime.now().strftime("%d-%m-%Y"))
    due_date = invoice.get("due_date", "-")
    subtotal = float(invoice.get("subtotal", 0.0))
    vat_amount = float(invoice.get("vat_amount", 0.0))
    total = float(invoice.get("total_amount", subtotal))

    comp_name = company.get("name", "Transito Intermediazioni S.r.l.")
    comp_addr = f"{company.get('address', 'Via Macello 18')} • {company.get('zip', '39100')} {company.get('city', 'Bolzano')} ({company.get('province', 'BZ')}), {company.get('country', 'IT')}"
    comp_vat = company.get("vat_number", "IT09876543210")
    comp_cf = company.get("fiscal_code", "09876543210")
    comp_rea = company.get("rea_number", "BZ-241598")
    comp_pec = company.get("pec", "transito.intermediazioni@legalmail.it")
    comp_sdi = company.get("sdi_code", "M5UXCR1")
    iban = company.get("iban", "IT60X0542811101000000123456")
    swift = company.get("swift", "CRBZIT2B")

    party_name = invoice.get("party_name", company.get("principal_name", "Veldhoven International Transport B.V."))
    party_vat = invoice.get("party_vat", company.get("principal_vat", "NL854729381B01"))
    party_addr = company.get("principal_address", "Transportlaan 14")
    party_city = f"{company.get('principal_zip', '5504 KR')} {company.get('principal_city', 'Veldhoven')}, {invoice.get('party_country', 'NL')}"

    # 1. Header achtergrond balk
    pdf.rgb(0.06, 0.09, 0.16)  # Dark slate #0f172a
    pdf.rect(0, 755, 595.28, 86.89, fill=True)

    # Logo Box
    pdf.rgb(0.15, 0.39, 0.92)  # Blue #2563eb
    pdf.rect(40, 775, 46, 46, fill=True)
    pdf.text("T", 54, 788, font="F2", size=26, r=1, g=1, b=1)

    # Bedrijfsnaam & Subtitle
    pdf.text(comp_name, 96, 805, font="F2", size=15, r=1, g=1, b=1)
    pdf.text("Intermediazione Trasporti • Vrachtbemiddeling & Facturatie", 96, 792, font="F1", size=9, r=0.58, g=0.75, b=0.98)
    pdf.text(f"P.IVA: {comp_vat} • C.F.: {comp_cf} • REA: {comp_rea} • SDI: {comp_sdi}", 96, 780, font="F1", size=8, r=0.8, g=0.85, b=0.9)
    pdf.text(f"PEC: {comp_pec} • Cap. Soc. € 100.000,00 i.v.", 96, 770, font="F1", size=8, r=0.7, g=0.75, b=0.8)

    # Factuur Type Badge rechts
    pdf.rgb(0.2, 0.25, 0.35)
    pdf.rect(370, 775, 185, 46, fill=True)
    pdf.text("COMMISSIEFACTUUR / NOTA", 380, 805, font="F2", size=9, r=0.6, g=0.8, b=1)
    pdf.text(inv_num, 380, 788, font="F5", size=13, r=1, g=1, b=1)
    pdf.text(f"Datum: {inv_date}  •  Verval: {due_date}", 380, 778, font="F1", size=8, r=0.8, g=0.85, b=0.9)

    # 2. Partijen Box
    y_box = 670
    pdf.rgb(0.96, 0.97, 0.99)
    pdf.stroke_rgb(0.85, 0.88, 0.92)
    pdf.rect(40, y_box, 515, 68, fill=True, stroke=True, line_width=1)

    # Links: Dienstverlener
    pdf.text("DIENSTVERLENER / INTERMEDIAIR (Cedente):", 52, y_box + 53, font="F2", size=8, r=0.3, g=0.4, b=0.55)
    pdf.text(comp_name, 52, y_box + 40, font="F2", size=10, r=0.1, g=0.15, b=0.25)
    pdf.text(comp_addr, 52, y_box + 28, font="F1", size=8, r=0.35, g=0.4, b=0.45)
    pdf.text(f"Italië • Btw-nummer: {comp_vat}", 52, y_box + 16, font="F1", size=8, r=0.35, g=0.4, b=0.45)

    # Rechts: Vervoerder (Debiteur)
    pdf.line(295, y_box + 5, 295, y_box + 63, line_width=0.8, r=0.85, g=0.88, b=0.92)
    pdf.text("OPDRACHTGEVER / VERVOERDER (Cessionario Committente):", 305, y_box + 53, font="F2", size=8, r=0.3, g=0.4, b=0.55)
    pdf.text(party_name, 305, y_box + 40, font="F2", size=10, r=0.1, g=0.15, b=0.25)
    pdf.text(f"{party_addr} • {party_city}", 305, y_box + 28, font="F1", size=8, r=0.35, g=0.4, b=0.45)
    pdf.text(f"Btw-nummer / P.IVA: {party_vat}", 305, y_box + 16, font="F1", size=8, r=0.35, g=0.4, b=0.45)

    # 3. Fiscale Informatie Balk
    y_fisc = 642
    pdf.rgb(0.93, 0.95, 0.99)
    pdf.stroke_rgb(0.75, 0.82, 0.95)
    pdf.rect(40, y_fisc, 515, 20, fill=True, stroke=True, line_width=0.8)
    pdf.text("Fiscale Behandeling:", 48, y_fisc + 6, font="F2", size=8, r=0.1, g=0.25, b=0.6)
    pdf.text("Artikel 7-ter DPR 633/1972 • Btw-verlegd (Inversione contabile / Natura N6) • Vrijgesteld van Italiaanse btw", 145, y_fisc + 6, font="F1", size=8, r=0.15, g=0.3, b=0.65)

    # 4. Rittenspecificatie Tabel
    y_table = 612
    pdf.rgb(0.12, 0.16, 0.24)
    pdf.rect(40, y_table, 515, 20, fill=True)
    pdf.text("Dossier / Rit", 48, y_table + 6, font="F2", size=8, r=1, g=1, b=1)
    pdf.text("Traject (Van -> Naar) & Lading / CMR", 130, y_table + 6, font="F2", size=8, r=1, g=1, b=1)
    pdf.text("Vrachtbedrag", 400, y_table + 6, font="F2", size=8, r=1, g=1, b=1)
    pdf.text("Provisie (€)", 485, y_table + 6, font="F2", size=8, r=1, g=1, b=1)

    y_row = y_table - 22
    if orders:
        for idx, o in enumerate(orders[:12]):
            bg_r = 0.98 if idx % 2 == 0 else 1.0
            pdf.rgb(bg_r, bg_r, bg_r)
            pdf.stroke_rgb(0.9, 0.92, 0.94)
            pdf.rect(40, y_row, 515, 22, fill=True, stroke=True, line_width=0.5)

            pdf.text(str(o.get("order_number", "-")), 48, y_row + 7, font="F5", size=8, r=0.1, g=0.15, b=0.25)

            orig = f"{o.get('origin_country', '')} {o.get('origin_city', '')}"
            dest = f"{o.get('destination_country', '')} {o.get('destination_city', '')}"
            cmr = f" (CMR: {o.get('cmr_number')})" if o.get('cmr_number') else ""
            route_str = f"{orig} -> {dest}{cmr}"
            pdf.text(route_str[:48], 130, y_row + 7, font="F1", size=8, r=0.2, g=0.25, b=0.3)

            freight_str = f"€ {float(o.get('freight_price', 0)):.2f}"
            pdf.text(freight_str, 400, y_row + 7, font="F1", size=8, r=0.3, g=0.35, b=0.4)

            comm_str = f"€ {float(o.get('commission_amount', 0)):.2f}"
            pdf.text(comm_str, 485, y_row + 7, font="F2", size=8, r=0.05, g=0.45, b=0.25)

            y_row -= 22
    else:
        pdf.rgb(1, 1, 1)
        pdf.stroke_rgb(0.9, 0.92, 0.94)
        pdf.rect(40, y_row, 515, 24, fill=True, stroke=True, line_width=0.5)
        pdf.text("Bemiddelingsvergoeding en provisies transport conform overeenkomst", 50, y_row + 8, font="F1", size=9, r=0.2, g=0.25, b=0.3)
        pdf.text(f"€ {subtotal:.2f}", 485, y_row + 8, font="F2", size=9, r=0.05, g=0.45, b=0.25)
        y_row -= 24

    # 5. Totaalblok & Betalingsinstructies
    y_totals = max(180, y_row - 25)
    
    # Betalingscondities Links
    pdf.rgb(0.96, 0.98, 1.0)
    pdf.stroke_rgb(0.75, 0.85, 0.98)
    pdf.rect(40, y_totals - 60, 310, 80, fill=True, stroke=True, line_width=0.8)
    pdf.text("BETALINGSINSTRUCTIES:", 50, y_totals + 8, font="F2", size=8, r=0.1, g=0.25, b=0.6)
    pdf.text(f"IBAN: {iban}", 50, y_totals - 5, font="F5", size=8, r=0.05, g=0.1, b=0.2)
    pdf.text(f"BIC / SWIFT: {swift}   •   Bank: Cassa di Risparmio di Bolzano", 50, y_totals - 18, font="F1", size=8, r=0.25, g=0.3, b=0.4)
    pdf.text(f"Ten name van: {comp_name}", 50, y_totals - 31, font="F1", size=8, r=0.25, g=0.3, b=0.4)
    pdf.text(f"Betalingskenmerk: {inv_num}", 50, y_totals - 44, font="F2", size=8, r=0.1, g=0.2, b=0.5)
    pdf.text(f"Vervaldatum betaling: {due_date}", 50, y_totals - 55, font="F2", size=8, r=0.8, g=0.3, b=0.1)

    # Totalenblok Rechts
    pdf.rgb(0.98, 0.99, 1.0)
    pdf.stroke_rgb(0.8, 0.85, 0.9)
    pdf.rect(365, y_totals - 60, 190, 80, fill=True, stroke=True, line_width=0.8)
    
    pdf.text("Subtotaal provisie:", 375, y_totals + 5, font="F1", size=8, r=0.3, g=0.35, b=0.4)
    pdf.text(f"€ {subtotal:.2f}", 490, y_totals + 5, font="F5", size=8, r=0.1, g=0.15, b=0.2)

    pdf.text("Btw (0% - Art. 7-ter):", 375, y_totals - 10, font="F1", size=8, r=0.3, g=0.35, b=0.4)
    pdf.text("€ 0,00", 490, y_totals - 10, font="F5", size=8, r=0.3, g=0.35, b=0.4)

    pdf.line(375, y_totals - 20, 545, y_totals - 20, line_width=1, r=0.7, g=0.75, b=0.8)

    pdf.text("TOTAAL TE VOLDOEN:", 375, y_totals - 35, font="F2", size=9, r=0.05, g=0.1, b=0.2)
    pdf.text(f"€ {total:.2f}", 465, y_totals - 48, font="F2", size=13, r=0.02, g=0.45, b=0.2)

    # 6. Footer met officiële verklaring
    pdf.line(40, 60, 555, 60, line_width=0.8, r=0.85, g=0.88, b=0.92)
    pdf.text(f"{comp_name} • Capitale Sociale € 100.000,00 i.v. • REA BZ-241598 • P.IVA {comp_vat}", 110, 48, font="F1", size=7, r=0.5, g=0.55, b=0.6)
    pdf.text("Copia di cortesia ai sensi dell'art. 1 D.Lgs. 127/2015. L'originale informatico fiscalmente rilevante è trasmesso al Sistema di Interscambio (SDI).", 62, 36, font="F3", size=6.5, r=0.55, g=0.6, b=0.65)

    return pdf.build_pdf()


def generate_quote_pdf(order: dict, company: dict) -> bytes:
    """
    Genereert een officiële A4 PDF Vrachtofferte (Preventivo di Trasporto) voor de verlader.
    """
    pdf = PdfBuilder()

    num_part = (order.get("order_number") or "").split("-")[-1] or "001"
    quote_num = f"OFF-2026-{num_part}"
    today = (order.get("created_at") or datetime.now().strftime("%Y-%m-%d")).split(" ")[0]
    freight = float(order.get("freight_price", 0.0))

    comp_name = company.get("name", "Transito Intermediazioni S.r.l.")
    comp_vat = company.get("vat_number", "IT09876543210")
    comp_cf = company.get("fiscal_code", "09876543210")
    comp_rea = company.get("rea_number", "BZ-241598")
    comp_email = company.get("smtp_sender_email") or company.get("pec") or "info@transito.it"

    principal_name = company.get("principal_name", "Veldhoven International Transport B.V.")

    client_name = order.get("client_name") or "Opdrachtgever / Verlader"
    client_city = f"{order.get('client_city') or ''} ({order.get('client_country') or ''})"
    client_vat = order.get("client_vat") or order.get("client_cf") or "—"

    # Header balk
    pdf.rgb(0.96, 0.62, 0.04)  # Amber #f59e0b
    pdf.rect(0, 755, 595.28, 86.89, fill=True)

    # Logo
    pdf.rgb(0.1, 0.15, 0.25)
    pdf.rect(40, 775, 46, 46, fill=True)
    pdf.text("T", 54, 788, font="F2", size=26, r=1, g=1, b=1)

    pdf.text(comp_name, 96, 805, font="F2", size=15, r=0.1, g=0.15, b=0.25)
    pdf.text("Intermediazione Trasporti • Vrachtbemiddeling & Expeditie", 96, 792, font="F2", size=9, r=0.2, g=0.25, b=0.35)
    pdf.text(f"P.IVA: {comp_vat} • C.F.: {comp_cf} • REA: {comp_rea} • E-mail: {comp_email}", 96, 780, font="F1", size=8, r=0.25, g=0.3, b=0.4)

    # Titel rechts
    pdf.rgb(0.1, 0.15, 0.25)
    pdf.rect(370, 775, 185, 46, fill=True)
    pdf.text("OFFERTE VRACHTBEMIDDELING", 380, 805, font="F2", size=8.5, r=1, g=0.8, b=0.4)
    pdf.text(quote_num, 380, 788, font="F5", size=13, r=1, g=1, b=1)
    pdf.text(f"Datum: {today}  •  Geldig: 14 dagen", 380, 778, font="F1", size=8, r=0.9, g=0.9, b=0.9)

    # Verlader & Vervoerder box
    y_box = 665
    pdf.rgb(0.98, 0.98, 0.99)
    pdf.stroke_rgb(0.85, 0.88, 0.92)
    pdf.rect(40, y_box, 515, 75, fill=True, stroke=True, line_width=1)

    pdf.text("OPDRACHTGEVER / VERLADER (Committente):", 52, y_box + 58, font="F2", size=8, r=0.3, g=0.4, b=0.55)
    pdf.text(client_name, 52, y_box + 44, font="F2", size=10, r=0.1, g=0.15, b=0.25)
    pdf.text(f"Vestiging: {client_city}", 52, y_box + 31, font="F1", size=8, r=0.3, g=0.35, b=0.4)
    pdf.text(f"BTW / P.IVA: {client_vat}", 52, y_box + 18, font="F1", size=8, r=0.3, g=0.35, b=0.4)

    pdf.line(295, y_box + 5, 295, y_box + 70, line_width=0.8, r=0.85, g=0.88, b=0.92)
    pdf.text("UITVOERENDE HOOFDVERVOERDER:", 305, y_box + 58, font="F2", size=8, r=0.3, g=0.4, b=0.55)
    pdf.text(principal_name, 305, y_box + 44, font="F2", size=10, r=0.1, g=0.15, b=0.25)
    pdf.text("Nederland (NL) • Transportlaan 14, Veldhoven", 305, y_box + 31, font="F1", size=8, r=0.3, g=0.35, b=0.4)
    pdf.text("Transito bemiddelt namens bovenstaande vervoerder.", 305, y_box + 18, font="F3", size=7.5, r=0.4, g=0.45, b=0.5)

    # Traject
    y_route = 580
    pdf.rgb(0.1, 0.15, 0.25)
    pdf.rect(40, y_route, 515, 20, fill=True)
    pdf.text("Traject & Geplande Route", 50, y_route + 6, font="F2", size=8, r=1, g=1, b=1)
    pdf.text("Rechtstreeks transport zonder overslag", 380, y_route + 6, font="F1", size=7.5, r=0.8, g=0.85, b=0.9)

    pdf.rgb(1, 1, 1)
    pdf.stroke_rgb(0.85, 0.88, 0.92)
    pdf.rect(40, y_route - 50, 515, 50, fill=True, stroke=True, line_width=0.8)

    pdf.text("LAADLOCATIE (Carico):", 52, y_route - 16, font="F2", size=8, r=0.15, g=0.4, b=0.8)
    pdf.text(f"{order.get('origin_country')} - {order.get('origin_city')}", 52, y_route - 30, font="F2", size=10, r=0.1, g=0.15, b=0.25)
    pdf.text(f"Geplande laaddatum: {order.get('pickup_date') or 'In overleg'}", 52, y_route - 42, font="F1", size=8, r=0.3, g=0.35, b=0.4)

    pdf.line(295, y_route - 48, 295, y_route - 2, line_width=0.8, r=0.85, g=0.88, b=0.92)
    pdf.text("LOSLOCATIE (Scarico):", 305, y_route - 16, font="F2", size=8, r=0.05, g=0.55, b=0.3)
    pdf.text(f"{order.get('destination_country')} - {order.get('destination_city')}", 305, y_route - 30, font="F2", size=10, r=0.1, g=0.15, b=0.25)
    pdf.text(f"Geplande leverdatum: {order.get('delivery_date') or 'Conform rijtijd'}", 305, y_route - 42, font="F1", size=8, r=0.3, g=0.35, b=0.4)

    # Lading & Specificaties
    y_goods = y_route - 75
    pdf.rgb(0.1, 0.15, 0.25)
    pdf.rect(40, y_goods, 515, 20, fill=True)
    pdf.text("Omschrijving Goederen & Lading", 50, y_goods + 6, font="F2", size=8, r=1, g=1, b=1)
    pdf.text("Gewicht", 340, y_goods + 6, font="F2", size=8, r=1, g=1, b=1)
    pdf.text("Tarief", 480, y_goods + 6, font="F2", size=8, r=1, g=1, b=1)

    pdf.rgb(1, 1, 1)
    pdf.stroke_rgb(0.85, 0.88, 0.92)
    pdf.rect(40, y_goods - 32, 515, 32, fill=True, stroke=True, line_width=0.8)
    pdf.text(str(order.get("goods_description") or "Handelsgoederen"), 52, y_goods - 18, font="F2", size=9, r=0.1, g=0.15, b=0.25)
    w_str = f"{float(order.get('weight_kg', 0)):.0f} kg" if order.get("weight_kg") else "FTL"
    pdf.text(w_str, 340, y_goods - 18, font="F1", size=9, r=0.2, g=0.25, b=0.3)
    pdf.text(f"€ {freight:.2f}", 480, y_goods - 18, font="F2", size=11, r=0.8, g=0.4, b=0.0)

    # Condities & Prijs Totaal
    y_cond = y_goods - 105
    pdf.rgb(0.98, 0.96, 0.92)
    pdf.stroke_rgb(0.9, 0.8, 0.6)
    pdf.rect(40, y_cond, 320, 60, fill=True, stroke=True, line_width=0.8)
    pdf.text("INBEGREPEN TRANSPORTCONDITIES:", 48, y_cond + 46, font="F2", size=7.5, r=0.5, g=0.3, b=0.1)
    pdf.text("• Vervoer geschiedt onder de bepalingen van het CMR-verdrag.", 48, y_cond + 33, font="F1", size=7.5, r=0.3, g=0.3, b=0.35)
    pdf.text("• Inclusief geldende dieselolietoeslag (BAF) en tolgelden.", 48, y_cond + 22, font="F1", size=7.5, r=0.3, g=0.3, b=0.35)
    pdf.text("• 2 uur laadtijd en 2 uur lostijd zijn inbegrepen.", 48, y_cond + 11, font="F1", size=7.5, r=0.3, g=0.3, b=0.35)

    # Totaal Prijs Box
    pdf.rgb(0.1, 0.15, 0.25)
    pdf.rect(375, y_cond, 180, 60, fill=True)
    pdf.text("GEOFFREERD VRACHTTARIEF:", 385, y_cond + 44, font="F2", size=7.5, r=1, g=0.8, b=0.4)
    pdf.text(f"€ {freight:.2f}", 385, y_cond + 20, font="F2", size=16, r=1, g=1, b=1)
    pdf.text("Excl. BTW (Art. 7-ter / CMR)", 385, y_cond + 8, font="F1", size=7.5, r=0.8, g=0.85, b=0.9)

    # Akkoordverklaring verlader
    y_sign = y_cond - 90
    pdf.stroke_rgb(0.8, 0.8, 0.8)
    pdf.rect(40, y_sign, 515, 75, stroke=True, line_width=0.8)
    pdf.text("AKKOORDVERKLARING VERLADER (Per Conferma d'Ordine):", 50, y_sign + 60, font="F2", size=8, r=0.2, g=0.25, b=0.35)
    pdf.text("Voor akkoord met het geoffreerde vrachttarief, de CMR-condities en 30 dagen betalingstermijn:", 50, y_sign + 48, font="F1", size=7.5, r=0.4, g=0.45, b=0.5)
    pdf.text("Datum: .......................................", 50, y_sign + 20, font="F1", size=8, r=0.3, g=0.35, b=0.4)
    pdf.text("Naam ondertekenaar: .......................................", 50, y_sign + 8, font="F1", size=8, r=0.3, g=0.35, b=0.4)
    pdf.text("Handtekening & Stempel Verlader: .....................................................", 280, y_sign + 14, font="F1", size=8, r=0.3, g=0.35, b=0.4)

    # Footer
    pdf.line(40, 50, 555, 50, line_width=0.8, r=0.85, g=0.88, b=0.92)
    pdf.text(f"{comp_name} • Capitale Sociale € 100.000,00 i.v. • REA BZ-241598 • P.IVA {comp_vat}", 125, 38, font="F1", size=7, r=0.5, g=0.55, b=0.6)
    pdf.text("Offerte uitgebracht onder voorbehoud van materieelbeschikbaarheid op het moment van definitieve boeking.", 85, 27, font="F3", size=6.5, r=0.55, g=0.6, b=0.65)

    return pdf.build_pdf()
