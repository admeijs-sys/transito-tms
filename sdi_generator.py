"""
SDI Generator - FatturaPA FPR12 Provisie- en Commissiefactuur
Conform de richtlijnen van de Agenzia delle Entrate en de Italiaanse BTW-wetgeving (DPR 633/1972).
Specifiek ontworpen voor transportintermediairs / makelaars die provisies factureren
aan een (buitenlands of binnenlands) transportbedrijf.
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime


def prettify_xml(elem: ET.Element) -> str:
    """Genereert een netjes geformatteerde XML-string met declaratie."""
    rough_string = ET.tostring(elem, encoding="utf-8")
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ", encoding="UTF-8").decode("utf-8")


def generate_commission_xml(invoice: dict, company: dict) -> str:
    """
    Genereert een officiële FatturaPA B2B XML (formaat FPR12) voor bemiddelingsprovisies.
    
    Partijen:
    - CedentePrestatore: Jouw Italiaanse intermediaire onderneming.
    - CessionarioCommittente: Het Partner Transportbedrijf namens wie je bemiddelt.
    
    Fiscale regels:
    - Buitenlands EU transportbedrijf (bijv. Nederland): Art. 7-ter DPR 633/1972 -> Natura N6 (Reverse charge).
    - Italiaans transportbedrijf voor internationaal transport: Art. 9 DPR 633/1972 -> Natura N3.2.
    - Binnenlands Italië algemeen: 22% IVA.
    """
    root = ET.Element(
        "p:FatturaElettronica",
        {
            "versione": "FPR12",
            "xmlns:p": "http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2",
            "xmlns:ds": "http://www.w3.org/2000/09/xmldsig#",
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "xsi:schemaLocation": "http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2 http://www.fatturapa.gov.it/export/fatturazione/sdi/fatturapa/v1.2/Schema_del_file_xml_FatturaPA_versione_1.2.xsd"
        }
    )

    # 1. HEADER
    header = ET.SubElement(root, "FatturaElettronicaHeader")

    # 1.1 DatiTrasmissione
    dati_trasm = ET.SubElement(header, "DatiTrasmissione")
    id_trasm = ET.SubElement(dati_trasm, "IdTrasmittente")
    ET.SubElement(id_trasm, "IdPaese").text = company.get("country", "IT")
    ET.SubElement(id_trasm, "IdCodice").text = company.get("vat_number", "IT01234567890").replace("IT", "")
    
    clean_num = invoice.get("invoice_number", "1").replace("/", "").replace("-", "").replace(" ", "")[-5:]
    ET.SubElement(dati_trasm, "ProgressivoInvio").text = f"{clean_num:0>5}"
    ET.SubElement(dati_trasm, "FormatoTrasmissione").text = "FPR12"
    
    # Codice Destinatario van het transportbedrijf (bijv. XXXXXXX voor EU of 7 tekens voor IT)
    recipient_code = (invoice.get("party_sdi") or company.get("principal_sdi") or "XXXXXXX").strip()
    if not recipient_code:
        recipient_code = "XXXXXXX" if invoice.get("party_country") != "IT" else "0000000"
    ET.SubElement(dati_trasm, "CodiceDestinatario").text = recipient_code
    
    if invoice.get("party_pec") and recipient_code in ("0000000", "XXXXXXX"):
        ET.SubElement(dati_trasm, "PECDestinatario").text = invoice.get("party_pec")

    # 1.2 CedentePrestatore (De Italiaanse Intermediair / Jouw onderneming)
    cedente = ET.SubElement(header, "CedentePrestatore")
    dati_anag_ced = ET.SubElement(cedente, "DatiAnagrafici")
    
    id_fisc_ced = ET.SubElement(dati_anag_ced, "IdFiscaleIVA")
    ET.SubElement(id_fisc_ced, "IdPaese").text = company.get("country", "IT")
    ET.SubElement(id_fisc_ced, "IdCodice").text = company.get("vat_number", "01234567890").replace("IT", "")
    
    ET.SubElement(dati_anag_ced, "CodiceFiscale").text = company.get("fiscal_code", "01234567890")
    
    anag_ced = ET.SubElement(dati_anag_ced, "Anagrafica")
    ET.SubElement(anag_ced, "Denominazione").text = company.get("name", "Transito Intermediazioni S.r.l.")
    ET.SubElement(dati_anag_ced, "RegimeFiscale").text = company.get("regime_fiscale", "RF01")

    sede_ced = ET.SubElement(cedente, "Sede")
    ET.SubElement(sede_ced, "Indirizzo").text = company.get("address", "Via Macello 18")
    ET.SubElement(sede_ced, "CAP").text = company.get("zip", "39100")
    ET.SubElement(sede_ced, "Comune").text = company.get("city", "Bolzano")
    ET.SubElement(sede_ced, "Provincia").text = company.get("province", "BZ")
    ET.SubElement(sede_ced, "Nazione").text = company.get("country", "IT")

    # 1.3 CessionarioCommittente (Het Transportbedrijf namens wie je optreedt)
    committente = ET.SubElement(header, "CessionarioCommittente")
    dati_anag_com = ET.SubElement(committente, "DatiAnagrafici")
    
    partner_country = invoice.get("party_country") or company.get("principal_country", "NL")
    partner_vat = invoice.get("party_vat") or company.get("principal_vat", "NL854729381B01")
    partner_name = invoice.get("party_name") or company.get("principal_name", "Veldhoven International Transport B.V.")
    
    id_fisc_com = ET.SubElement(dati_anag_com, "IdFiscaleIVA")
    ET.SubElement(id_fisc_com, "IdPaese").text = partner_country
    ET.SubElement(id_fisc_com, "IdCodice").text = partner_vat.replace(partner_country, "")
    
    anag_com = ET.SubElement(dati_anag_com, "Anagrafica")
    ET.SubElement(anag_com, "Denominazione").text = partner_name

    sede_com = ET.SubElement(committente, "Sede")
    ET.SubElement(sede_com, "Indirizzo").text = company.get("principal_address", "Transportlaan 14")
    ET.SubElement(sede_com, "CAP").text = company.get("principal_zip", "5504 KR")
    ET.SubElement(sede_com, "Comune").text = company.get("principal_city", "Veldhoven")
    ET.SubElement(sede_com, "Nazione").text = partner_country

    # 2. BODY
    body = ET.SubElement(root, "FatturaElettronicaBody")
    dati_gen = ET.SubElement(body, "DatiGenerali")
    dati_doc = ET.SubElement(dati_gen, "DatiGeneraliDocumento")
    
    ET.SubElement(dati_doc, "TipoDocumento").text = "TD01"  # Reguliere B2B factuur
    ET.SubElement(dati_doc, "Divisa").text = "EUR"
    
    inv_date = invoice.get("date") or datetime.now().strftime("%Y-%m-%d")
    ET.SubElement(dati_doc, "Data").text = inv_date
    ET.SubElement(dati_doc, "Numero").text = str(invoice.get("invoice_number", "PROV-2026-001"))
    
    subtotal = float(invoice.get("subtotal", 0.0))
    vat_rate = float(invoice.get("vat_rate", 0.0))
    vat_amount = round(subtotal * (vat_rate / 100.0), 2)
    total_amount = round(subtotal + vat_amount, 2)
    
    ET.SubElement(dati_doc, "ImportoTotaleDocumento").text = f"{total_amount:.2f}"
    
    causale = f"Provvigioni per servizi di intermediazione e procacciamento trasporti per conto di {partner_name}"
    ET.SubElement(dati_doc, "Causale").text = causale[:200]

    # 2.1 Goederen & Diensten (DatiBeniServizi)
    dati_beni = ET.SubElement(body, "DatiBeniServizi")
    lines = invoice.get("lines", [])
    
    if not lines:
        lines = [{
            "description": f"Provvigioni di intermediazione trasporti relative al periodo {inv_date}",
            "quantity": 1.0,
            "unit_price": subtotal,
            "total_price": subtotal,
            "vat_rate": vat_rate,
            "vat_nature": invoice.get("vat_nature", "N6"),
            "normative_ref": invoice.get("normative_ref", "Operazione non soggetta IVA art. 7-ter DPR 633/72")
        }]

    for idx, line in enumerate(lines, start=1):
        linea = ET.SubElement(dati_beni, "DettaglioLinee")
        ET.SubElement(linea, "NumeroLinea").text = str(idx)
        ET.SubElement(linea, "Descrizione").text = line.get("description", "Provvigione intermediazione")[:1000]
        ET.SubElement(linea, "Quantita").text = f"{float(line.get('quantity', 1.0)):.2f}"
        ET.SubElement(linea, "PrezzoUnitario").text = f"{float(line.get('unit_price', 0.0)):.2f}"
        ET.SubElement(linea, "PrezzoTotale").text = f"{float(line.get('total_price', 0.0)):.2f}"
        ET.SubElement(linea, "AliquotaIVA").text = f"{float(line.get('vat_rate', 0.0)):.2f}"
        
        nature = line.get("vat_nature") or invoice.get("vat_nature")
        if nature and float(line.get("vat_rate", 0.0)) == 0.0:
            ET.SubElement(linea, "Natura").text = nature
            norm_ref = line.get("normative_ref") or invoice.get("normative_ref")
            if norm_ref:
                ET.SubElement(linea, "RiferimentoNormativo").text = norm_ref

    # 2.2 DatiRiepilogo
    riepilogo = ET.SubElement(dati_beni, "DatiRiepilogo")
    ET.SubElement(riepilogo, "AliquotaIVA").text = f"{vat_rate:.2f}"
    
    nature = invoice.get("vat_nature")
    if nature and vat_rate == 0.0:
        ET.SubElement(riepilogo, "Natura").text = nature
        
    ET.SubElement(riepilogo, "ImponibileImporto").text = f"{subtotal:.2f}"
    ET.SubElement(riepilogo, "Imposta").text = f"{vat_amount:.2f}"
    
    if nature and vat_rate == 0.0:
        norm_ref = invoice.get("normative_ref", "Operazione non soggetta ad IVA ai sensi dell'art. 7-ter DPR 633/72")
        ET.SubElement(riepilogo, "RiferimentoNormativo").text = norm_ref
    else:
        ET.SubElement(riepilogo, "EsigibilitaIVA").text = "I"

    # 2.3 Betalingsgegevens
    if company.get("iban"):
        pagamento = ET.SubElement(body, "DatiPagamento")
        ET.SubElement(pagamento, "CondizioniPagamento").text = "TP02"
        dett_pag = ET.SubElement(pagamento, "DettaglioPagamento")
        ET.SubElement(dett_pag, "ModalitaPagamento").text = "MP05"  # Bonifico bancario
        ET.SubElement(dett_pag, "DataScadenzaPagamento").text = invoice.get("due_date", inv_date)
        ET.SubElement(dett_pag, "ImportoPagamento").text = f"{total_amount:.2f}"
        ET.SubElement(dett_pag, "IBAN").text = company.get("iban", "").replace(" ", "")

    return prettify_xml(root)
