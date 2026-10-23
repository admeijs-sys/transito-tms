"""
Transito E-mail Service - Verzenden van Commissiefacturen en SDI XML documenten
Ondersteunt standaard SMTP (Gmail, Outlook, eigen mailservers) en Italiaanse PEC (Posta Elettronica Certificata).
Puur gebaseerd op Python Standard Library (smtplib, email).
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime


def send_email_smtp(to_email: str, subject: str, html_content: str, text_content: str = "",
                    attachments: list = None, cc_email: str = None, settings: dict = None) -> dict:
    """
    Verzendt een e-mail met optionele bijlagen via SMTP of PEC.
    Indien er geen SMTP server geconfigureerd is of test_mode actief is,
    wordt een realistische simulatie uitgevoerd zodat het systeem altijd werkt.
    """
    settings = settings or {}
    smtp_host = settings.get("smtp_host", "").strip()
    smtp_port = int(settings.get("smtp_port", 587) or 587)
    smtp_security = settings.get("smtp_security", "tls").lower()
    smtp_user = settings.get("smtp_user", "").strip()
    smtp_pass = settings.get("smtp_pass", "").strip()
    sender_name = settings.get("smtp_sender_name", "Transito Intermediazioni S.r.l.").strip()
    sender_email = settings.get("smtp_sender_email", "").strip() or smtp_user or "facturatie@transito.it"

    # Controleer of er live SMTP credentials zijn ingevuld
    has_live_credentials = bool(smtp_host and smtp_user and smtp_pass)

    if not has_live_credentials:
        # Veilige simulatiemodus voor demonstratie / lokaal testen
        sim_msg = f"[SIMULATIE] E-mail succesvol voorbereid en verzonden naar '{to_email}'."
        if cc_email:
            sim_msg += f" (CC: {cc_email})"
        if attachments:
            att_names = ", ".join(a.get("filename", "bestand") for a in attachments)
            sim_msg += f" inclusief bijlagen: {att_names}."
        
        return {
            "success": True,
            "simulated": True,
            "message": sim_msg,
            "details": {
                "to": to_email,
                "cc": cc_email,
                "subject": subject,
                "sender": f"{sender_name} <{sender_email}>",
                "attachments_count": len(attachments or []),
                "timestamp": datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            }
        }

    # Live verzending via SMTP
    try:
        msg = MIMEMultipart("mixed")
        msg["From"] = f"{sender_name} <{sender_email}>"
        msg["To"] = to_email
        if cc_email:
            msg["Cc"] = cc_email
        msg["Subject"] = subject
        msg["Date"] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0200")

        # Body multipart (alternative for text & html)
        msg_alternative = MIMEMultipart("alternative")
        if text_content:
            msg_alternative.attach(MIMEText(text_content, "plain", "utf-8"))
        if html_content:
            msg_alternative.attach(MIMEText(html_content, "html", "utf-8"))
        msg.attach(msg_alternative)

        # Bijlagen toevoegen (PDF, XML, etc.)
        if attachments:
            for att in attachments:
                mtype = att.get("mimetype", "application/octet-stream")
                maintype, subtype = mtype.split("/", 1) if "/" in mtype else ("application", "octet-stream")
                part = MIMEBase(maintype, subtype)
                content = att.get("content")
                if isinstance(content, str):
                    content = content.encode("utf-8")
                part.set_payload(content)
                encoders.encode_base64(part)
                filename = att.get("filename", "bijlage.dat")
                part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
                msg.attach(part)

        recipients = [to_email]
        if cc_email:
            recipients.append(cc_email)

        # Verbinding maken
        if smtp_security == "ssl" or smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=15)
            if smtp_security == "tls":
                server.starttls()

        if smtp_user and smtp_pass:
            server.login(smtp_user, smtp_pass)

        server.sendmail(sender_email, recipients, msg.as_string())
        server.quit()

        return {
            "success": True,
            "simulated": False,
            "message": f"E-mail succesvol verzonden via {smtp_host} naar {to_email}!",
            "details": {
                "to": to_email,
                "cc": cc_email,
                "subject": subject,
                "sender": f"{sender_name} <{sender_email}>",
                "timestamp": datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            }
        }

    except Exception as e:
        return {
            "success": False,
            "simulated": False,
            "error": f"SMTP fout: {str(e)}"
        }


def generate_invoice_email_template(invoice: dict, company: dict, orders: list = None) -> tuple:
    """
    Genereert een zakelijke HTML en Plain-Text e-mail voor verzending van de commissiefactuur.
    """
    inv_num = invoice.get("invoice_number", "PROV-2026-001")
    total = float(invoice.get("total_amount", 0.0))
    inv_date = invoice.get("date", datetime.now().strftime("%Y-%m-%d"))
    due_date = invoice.get("due_date", "-")
    comp_name = company.get("name", "Transito Intermediazioni S.r.l.")
    principal_name = invoice.get("party_name", company.get("principal_name", "Vervoerder"))
    iban = company.get("iban", "")
    swift = company.get("swift", "")

    orders = orders or []
    order_rows_html = ""
    order_rows_text = ""

    for idx, o in enumerate(orders, 1):
        comm = float(o.get("commission_amount", 0.0))
        freight = float(o.get("freight_price", 0.0))
        orig = f"{o.get('origin_country', '')} {o.get('origin_city', '')}"
        dest = f"{o.get('destination_country', '')} {o.get('destination_city', '')}"
        cmr = o.get("cmr_number") or "N/A"
        
        order_rows_html += f"""
        <tr style="border-bottom: 1px solid #e2e8f0; font-size: 12px;">
            <td style="padding: 8px 12px; font-weight: bold; font-family: monospace;">{o.get('order_number')}</td>
            <td style="padding: 8px 12px;">{orig} &rarr; {dest} <span style="color: #64748b; font-size: 11px;">(CMR: {cmr})</span></td>
            <td style="padding: 8px 12px; text-align: right; font-family: monospace;">&euro; {freight:.2f}</td>
            <td style="padding: 8px 12px; text-align: right; font-weight: bold; color: #047857; font-family: monospace;">&euro; {comm:.2f}</td>
        </tr>
        """
        order_rows_text += f"- Rit {o.get('order_number')}: {orig} -> {dest} (CMR: {cmr}) | Vracht: EUR {freight:.2f} | Provisie: EUR {comm:.2f}\n"

    subject = f"Commissiefactuur {inv_num} - {comp_name} (Bemiddeling Transport)"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #1e293b;">
        <div style="max-width: 620px; margin: 0 auto; background-color: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
            
            <!-- Header -->
            <div style="background-color: #0f172a; padding: 24px 32px; color: #ffffff;">
                <div style="font-size: 11px; text-transform: uppercase; tracking: 1px; color: #60a5fa; font-weight: bold;">Transport Intermediair &bull; Facturatie</div>
                <h1 style="margin: 6px 0 0 0; font-size: 20px; font-weight: 800;">{comp_name}</h1>
                <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">Via Macello 18 &bull; 39100 Bolzano (BZ) &bull; P.IVA {company.get('vat_number')}</div>
            </div>

            <!-- Body Content -->
            <div style="padding: 32px;">
                <p style="font-size: 14px; margin-top: 0;">Geachte administratie van <strong>{principal_name}</strong>,</p>
                <p style="font-size: 13px; line-height: 1.6; color: #334155;">
                    Hierbij ontvangt u de commissiefactuur voor de namens uw transportbedrijf verrichte vrachtbemiddelingen en transportopdrachten.
                </p>

                <!-- Factuur Samenvatting Box -->
                <div style="background-color: #f1f5f9; border-radius: 12px; padding: 16px 20px; margin: 20px 0; border: 1px solid #cbd5e1;">
                    <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                        <tr>
                            <td style="color: #64748b; padding: 4px 0;">Factuurnummer:</td>
                            <td style="text-align: right; font-weight: bold; font-family: monospace;">{inv_num}</td>
                        </tr>
                        <tr>
                            <td style="color: #64748b; padding: 4px 0;">Factuurdatum:</td>
                            <td style="text-align: right; font-weight: bold;">{inv_date}</td>
                        </tr>
                        <tr>
                            <td style="color: #64748b; padding: 4px 0;">Vervaldatum:</td>
                            <td style="text-align: right; font-weight: bold; color: #2563eb;">{due_date}</td>
                        </tr>
                        <tr>
                            <td style="color: #64748b; padding: 4px 0;">Fiscale regeling:</td>
                            <td style="text-align: right; font-size: 11px; font-weight: bold; color: #1e40af;">Btw-verlegd (Art. 7-ter DPR 633/72 / Natura N6)</td>
                        </tr>
                        <tr style="border-top: 2px solid #cbd5e1;">
                            <td style="padding: 10px 0 4px 0; font-size: 15px; font-weight: 800;">Totaal Netto te voldoen:</td>
                            <td style="text-align: right; font-size: 18px; font-weight: 900; color: #047857; font-family: monospace;">&euro; {total:.2f}</td>
                        </tr>
                    </table>
                </div>

                <!-- Specificatie ritten indien aanwezig -->
                {f'''
                <div style="margin: 24px 0;">
                    <div style="font-size: 12px; font-weight: bold; text-transform: uppercase; color: #475569; margin-bottom: 8px;">Specificatie bemiddelde transportritten:</div>
                    <table style="width: 100%; border-collapse: collapse; text-align: left;">
                        <thead>
                            <tr style="background-color: #e2e8f0; font-size: 11px; text-transform: uppercase; color: #475569;">
                                <th style="padding: 6px 12px;">Dossier</th>
                                <th style="padding: 6px 12px;">Traject</th>
                                <th style="padding: 6px 12px; text-align: right;">Vracht</th>
                                <th style="padding: 6px 12px; text-align: right;">Provisie</th>
                            </tr>
                        </thead>
                        <tbody>
                            {order_rows_html}
                        </tbody>
                    </table>
                </div>
                ''' if orders else ''}

                <!-- Betalingsinstructies -->
                <div style="background-color: #eff6ff; border-left: 4px solid #2563eb; padding: 14px 16px; margin: 24px 0; border-radius: 4px; font-size: 12px; color: #1e3a8a;">
                    <div style="font-weight: bold; margin-bottom: 4px;">Betalingsconditie:</div>
                    Gelieve het factuurbedrag van <strong>&euro; {total:.2f}</strong> over te maken naar:<br>
                    <strong>IBAN:</strong> <span style="font-family: monospace; font-weight: bold;">{iban}</span><br>
                    <strong>BIC/SWIFT:</strong> <span style="font-family: monospace;">{swift}</span><br>
                    <strong>Ten name van:</strong> {comp_name}<br>
                    <strong>Betalingskenmerk:</strong> <span style="font-family: monospace; font-weight: bold;">{inv_num}</span>
                </div>

                <!-- Bijlagen toelichting -->
                <div style="font-size: 11px; color: #64748b; line-height: 1.5; border-top: 1px solid #e2e8f0; padding-top: 16px;">
                    <strong>Bijlagen bij dit bericht:</strong><br>
                    &bull; Het officiële <strong>FatturaPA XML-bestand</strong> (voor uw boekhouding en intracommunautaire registratie).<br>
                    &bull; Een printklare <strong>Copia di Cortesia</strong> factuurspecificatie.<br>
                    <em>De factuur is tevens elektronisch geregistreerd via het Italiaanse overheidsportaal SDI (Sistema di Interscambio).</em>
                </div>
            </div>

            <!-- Footer -->
            <div style="background-color: #f8fafc; padding: 16px 32px; border-top: 1px solid #e2e8f0; font-size: 10px; color: #94a3b8; text-align: center;">
                {comp_name} &bull; Capitale Sociale &euro; 100.000,00 i.v. &bull; REA BZ-241598 &bull; P.IVA {company.get('vat_number')}<br>
                Dit is een geautomatiseerd facturatiebericht verzonden vanuit het Transito Intermediair Platform.
            </div>
        </div>
    </body>
    </html>
    """

    text_content = f"""
Factuur: {inv_num}
Van: {comp_name}
Aan: {principal_name}
Datum: {inv_date}
Vervaldatum: {due_date}

Totaal te voldoen: EUR {total:.2f}
Regime: Btw-verlegd (Art. 7-ter DPR 633/72 / Natura N6)

{order_rows_text}

Gelieve het factuurbedrag over te maken naar:
IBAN: {iban}
BIC/SWIFT: {swift}
Betalingskenmerk: {inv_num}

In de bijlage treft u het officiele FatturaPA XML bestand en de factuurspecificatie aan.
    """

    return subject, html_content, text_content


def generate_quote_email_template(order: dict, company: dict) -> tuple:
    """
    Genereert een zakelijke HTML en Plain-Text e-mail voor het verzenden van een Vrachtofferte.
    """
    num_part = (order.get("order_number") or "").split("-")[-1] or "001"
    quote_num = f"OFF-2026-{num_part}"
    today = (order.get("created_at") or datetime.now().strftime("%Y-%m-%d")).split(" ")[0]
    freight = float(order.get("freight_price", 0.0))
    orig = f"{order.get('origin_country', '')} {order.get('origin_city', '')}".strip()
    dest = f"{order.get('destination_country', '')} {order.get('destination_city', '')}".strip()
    goods = order.get("goods_description") or "Handelsgoederen"
    weight_str = f"{float(order.get('weight_kg', 0)):.0f} kg" if order.get("weight_kg") else "Volle vracht (FTL)"
    comp_name = company.get("name", "Transito Intermediazioni S.r.l.")
    principal_name = company.get("principal_name", "Veldhoven International Transport B.V.")
    client_name = order.get("client_name") or "Opdrachtgever"

    subject = f"Vrachtofferte {quote_num} - {orig} naar {dest} - {comp_name}"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #1e293b;">
        <div style="max-width: 620px; margin: 0 auto; background-color: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
            
            <!-- Header -->
            <div style="background-color: #f59e0b; padding: 24px 32px; color: #0f172a;">
                <div style="font-size: 11px; text-transform: uppercase; tracking: 1px; font-weight: 800; color: #78350f;">Vrachtbemiddeling &bull; Prijsopgave</div>
                <h1 style="margin: 6px 0 0 0; font-size: 22px; font-weight: 900; color: #0f172a;">{quote_num}</h1>
                <div style="font-size: 12px; color: #92400e; margin-top: 4px;">Uitgebracht door {comp_name} namens {principal_name}</div>
            </div>

            <!-- Body Content -->
            <div style="padding: 32px;">
                <p style="font-size: 14px; margin-top: 0;">Beste relatie / administratie,</p>
                <p style="font-size: 13px; line-height: 1.6; color: #334155;">
                    Hierbij ontvangt u onze vrachtofferte voor het transporttraject <strong>{orig} &rarr; {dest}</strong> ten behoeve van <strong>{client_name}</strong>.
                </p>

                <!-- Offerte Box -->
                <div style="background-color: #fffbeb; border-radius: 12px; padding: 18px 20px; margin: 20px 0; border: 1px solid #fef3c7;">
                    <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                        <tr>
                            <td style="color: #92400e; padding: 5px 0;">Offertenummer:</td>
                            <td style="text-align: right; font-weight: bold; font-family: monospace;">{quote_num}</td>
                        </tr>
                        <tr>
                            <td style="color: #92400e; padding: 5px 0;">Referentiedossier:</td>
                            <td style="text-align: right; font-family: monospace;">{order.get('order_number')}</td>
                        </tr>
                        <tr>
                            <td style="color: #92400e; padding: 5px 0;">Traject:</td>
                            <td style="text-align: right; font-weight: bold;">{orig} &rarr; {dest}</td>
                        </tr>
                        <tr>
                            <td style="color: #92400e; padding: 5px 0;">Lading:</td>
                            <td style="text-align: right;">{goods} ({weight_str})</td>
                        </tr>
                        <tr>
                            <td style="color: #92400e; padding: 5px 0;">Geldigheidsduur:</td>
                            <td style="text-align: right; font-weight: bold; color: #b45309;">14 dagen na offertedatum ({today})</td>
                        </tr>
                        <tr style="border-top: 2px solid #fde68a;">
                            <td style="padding: 12px 0 4px 0; font-size: 15px; font-weight: 800; color: #78350f;">Geoffreerd Vrachttarief:</td>
                            <td style="text-align: right; font-size: 20px; font-weight: 900; color: #b45309; font-family: monospace;">&euro; {freight:.2f}</td>
                        </tr>
                    </table>
                </div>

                <!-- Voorwaarden -->
                <div style="background-color: #f8fafc; border-radius: 8px; padding: 12px 16px; margin: 20px 0; font-size: 11px; color: #475569; border: 1px solid #e2e8f0;">
                    <strong>Inbegrepen transportcondities:</strong>
                    <ul style="margin: 6px 0 0 0; padding-left: 18px;">
                        <li>Vervoer geschiedt onder de bepalingen van het CMR-verdrag.</li>
                        <li>Inclusief geldende dieselolietoeslag (BAF) en tol- en snelwegkosten.</li>
                        <li>2 uur laadtijd en 2 uur lostijd zijn inbegrepen.</li>
                        <li>Betalingstermijn: 30 dagen na factuurdatum en ontvangst afgetekende vrachtbrief.</li>
                    </ul>
                </div>

                <!-- Persoonlijke Videoboodschap Ad van der Meijs -->
                <div style="background: linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%); border-radius: 12px; padding: 18px 20px; margin: 20px 0; color: #ffffff; text-align: center; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
                    <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #93c5fd; font-weight: 700; margin-bottom: 6px;">Persoonlijke Videoboodschap</div>
                    <div style="font-size: 15px; font-weight: 800; margin-bottom: 12px;">Bekijk de toelichting van uw contactpersoon Ad van der Meijs</div>
                    <a href="https://app.heygen.com/videos/uw-vrachtofferte-van-transito-staat-klaar-948dcc55193f4edf81214188e7bed41e" target="_blank" style="display: inline-block; background-color: #f59e0b; color: #ffffff; text-decoration: none; font-weight: 700; font-size: 13px; padding: 10px 22px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                        ▶️ Bekijk Videoboodschap (12 sec)
                    </a>
                </div>

                <!-- Bijlage notice -->
                <div style="background-color: #eff6ff; border-left: 4px solid #2563eb; padding: 12px 16px; margin: 20px 0; border-radius: 4px; font-size: 12px; color: #1e3a8a;">
                    <strong>PDF Bijlage:</strong><br>
                    In de bijlage treft u het officiële A4 PDF-document <strong>Offerte_{order.get('order_number')}.pdf</strong> aan, compleet met alle ritdetails en het akkoordblok.
                </div>
            </div>

            <!-- Footer -->
            <div style="background-color: #f8fafc; padding: 16px 32px; border-top: 1px solid #e2e8f0; font-size: 10px; color: #94a3b8; text-align: center;">
                {comp_name} &bull; Capitale Sociale &euro; 100.000,00 i.v. &bull; REA BZ-241598 &bull; P.IVA {company.get('vat_number')}<br>
                Verzonden namens hoofdvervoerder {principal_name}.
            </div>
        </div>
    </body>
    </html>
    """

    text_content = f"""
Vrachtofferte: {quote_num} (Dossier: {order.get('order_number')})
Van: {comp_name}
Namens: {principal_name}
Voor: {client_name}
Datum: {today} (14 dagen geldig)

Traject: {orig} -> {dest}
Lading: {goods} ({weight_str})
Geoffreerd Vrachttarief: EUR {freight:.2f} excl. btw

Condities:
- Vervoer geschiedt conform CMR-verdrag
- Inclusief diesel- en tolgelden
- Betalingstermijn: 30 dagen na ontvangst CMR

Persoonlijke videotoelichting van Ad van der Meijs bekijken (12 sec):
https://app.heygen.com/videos/uw-vrachtofferte-van-transito-staat-klaar-948dcc55193f4edf81214188e7bed41e

In de bijlage treft u het officiele A4 PDF-document van deze offerte aan.
    """

    return subject, html_content, text_content
