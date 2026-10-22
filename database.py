"""
Database Module voor Transito Intermediair & Italiaanse Boekhouding (Contabilità Italiana).
Volledig ingericht volgens de Italiaanse wetgeving en boekhoudnormen:
- Piano dei Conti (Rekeningschema conform OIC en Codice Civile)
- Registri IVA Vendite e Acquisti (artt. 23 e 25 DPR 633/1972)
- Liquidazione Periodica IVA (LIPE) met Modello F24 berekening
- Conto Economico & Stato Patrimoniale (artt. 2424-2425 Codice Civile)
- Dubbel boekhouden (Libro Giornale ex art. 2214 Codice Civile)
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta

DB_FILE = os.path.join(os.path.dirname(__file__), "transito_tms.db")


def safe_float(val, default=0.0):
    if val is None or val == "":
        return default
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().replace("€", "").replace("EUR", "").replace("$", "").replace(" ", "")
    if not s:
        return default
    if "," in s and "." in s:
        if s.find(".") < s.find(","):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except Exception:
        return default


def safe_int(val, default=0):
    if val is None or val == "":
        return default
    try:
        if isinstance(val, int):
            return val
        s = str(val).split(".")[0].split(",")[0].strip()
        return int(s)
    except Exception:
        return default


def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Eigen onderneming (de Italiaanse Intermediair / Makelaar)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS company_settings (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        legal_form TEXT DEFAULT 'S.r.l.',
        vat_number TEXT NOT NULL,
        fiscal_code TEXT NOT NULL,
        address TEXT NOT NULL,
        zip TEXT NOT NULL,
        city TEXT NOT NULL,
        province TEXT NOT NULL,
        country TEXT DEFAULT 'IT',
        pec TEXT NOT NULL,
        sdi_code TEXT DEFAULT '0000000',
        regime_fiscale TEXT DEFAULT 'RF01',
        iban TEXT NOT NULL,
        swift TEXT,
        rea_number TEXT,
        capital REAL DEFAULT 100000.00,
        sdi_provider TEXT DEFAULT 'Aruba / Fatture in Cloud API Gateway',
        test_mode INTEGER DEFAULT 1,
        
        -- Gegevens van het vaste Partner Transportbedrijf namens wie wordt opgetreden
        principal_name TEXT NOT NULL DEFAULT 'Veldhoven International Transport B.V.',
        principal_country TEXT NOT NULL DEFAULT 'NL',
        principal_vat TEXT NOT NULL DEFAULT 'NL854729381B01',
        principal_address TEXT NOT NULL DEFAULT 'Transportlaan 14',
        principal_zip TEXT NOT NULL DEFAULT '5504 KR',
        principal_city TEXT NOT NULL DEFAULT 'Veldhoven',
        principal_pec TEXT DEFAULT '',
        principal_sdi TEXT DEFAULT 'XXXXXXX',
        default_commission_type TEXT DEFAULT 'percentage',
        default_commission_rate REAL DEFAULT 10.0,
        default_commission_fixed REAL DEFAULT 200.0,

        -- E-mail & Mailkoppeling instellingen
        smtp_host TEXT DEFAULT 'smtp.gmail.com',
        smtp_port INTEGER DEFAULT 587,
        smtp_security TEXT DEFAULT 'tls', -- 'tls', 'ssl', 'none'
        smtp_user TEXT DEFAULT '',
        smtp_pass TEXT DEFAULT '',
        smtp_sender_name TEXT DEFAULT 'Transito Intermediazioni S.r.l.',
        smtp_sender_email TEXT DEFAULT '',
        principal_email TEXT DEFAULT 'administratie@veldhoventransport.nl',
        accountant_email TEXT DEFAULT 'studio.rossi@commercialisti.it'
    )
    """)

    # 2. Relaties: Klanten / Verladers
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS parties (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT NOT NULL DEFAULT 'client',
        name TEXT NOT NULL,
        country TEXT NOT NULL,
        vat_number TEXT,
        fiscal_code TEXT,
        sdi_code TEXT DEFAULT '0000000',
        pec TEXT,
        email TEXT,
        phone TEXT,
        address TEXT,
        zip TEXT,
        city TEXT,
        province TEXT,
        is_eu INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 3. Bemiddelde Opdrachten (Orders)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_number TEXT UNIQUE NOT NULL,
        client_id INTEGER REFERENCES parties(id),
        origin_country TEXT NOT NULL,
        origin_city TEXT NOT NULL,
        origin_address TEXT,
        destination_country TEXT NOT NULL,
        destination_city TEXT NOT NULL,
        destination_address TEXT,
        goods_description TEXT,
        weight_kg REAL,
        palettes INTEGER,
        loading_meters REAL,
        cmr_number TEXT,
        pickup_date TEXT,
        delivery_date TEXT,
        freight_price REAL NOT NULL,
        carrier_price REAL DEFAULT 0.0,
        commission_type TEXT DEFAULT 'percentage', -- 'percentage', 'fixed', 'margin', 'custom'
        commission_rate REAL DEFAULT 10.0,
        commission_amount REAL NOT NULL,
        status TEXT DEFAULT 'Aangemeld',
        commission_invoice_id INTEGER REFERENCES invoices(id),
        transport_type TEXT NOT NULL DEFAULT 'international',
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 4. Provisiefacturen (Uitgaand - Registro IVA Vendite)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_number TEXT UNIQUE NOT NULL,
        doc_type TEXT DEFAULT 'TD01',
        order_ids_json TEXT,
        party_name TEXT NOT NULL,
        party_country TEXT NOT NULL,
        party_vat TEXT NOT NULL,
        party_sdi TEXT,
        date TEXT NOT NULL,
        due_date TEXT NOT NULL,
        subtotal REAL NOT NULL,
        vat_rate REAL DEFAULT 0.0,
        vat_amount REAL DEFAULT 0.0,
        total_amount REAL NOT NULL,
        vat_nature TEXT,
        normative_ref TEXT,
        sdi_status TEXT DEFAULT 'Gegenereerd',
        sdi_identifier TEXT,
        sdi_response_message TEXT,
        xml_content TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ==================== BOEKHOUDMODULE (CONTABILITÀ ITALIANA) ====================

    # 5. Piano dei Conti (Italiaans Rekeningschema)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chart_of_accounts (
        code TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT NOT NULL, -- 'Attivo', 'Passivo', 'Costi', 'Ricavi'
        subcategory TEXT,
        tax_deductibility_pct REAL DEFAULT 100.0,
        vat_deductibility_pct REAL DEFAULT 100.0
    )
    """)

    # 6. Kosten en Inkoopfacturen (Registro IVA Acquisti ex art. 25 DPR 633/1972)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        supplier_name TEXT NOT NULL,
        supplier_vat TEXT,
        invoice_number TEXT,
        description TEXT NOT NULL,
        account_code TEXT REFERENCES chart_of_accounts(code),
        imponibile REAL NOT NULL, -- Bedrag exclusief btw
        vat_rate REAL DEFAULT 22.0, -- Standaard Italiaanse IVA 22%
        vat_amount REAL NOT NULL,
        total_amount REAL NOT NULL,
        vat_nature TEXT, -- Leeg voor 22%, of 'N1', 'N2', 'N4' etc.
        vat_deductible_pct REAL DEFAULT 100.0, -- Btw-aftrekbaarheid
        payment_status TEXT DEFAULT 'Betaald', -- 'Betaald', 'Te Betalen'
        payment_method TEXT DEFAULT 'Bonifico Bancario (MP05)',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 7. Libro Giornale (Journaalposten - Partita Doppia ex art. 2214 c.c.)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS journal_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entry_number TEXT NOT NULL,
        date TEXT NOT NULL,
        description TEXT NOT NULL,
        account_code TEXT NOT NULL,
        account_name TEXT NOT NULL,
        debit REAL DEFAULT 0.0,
        credit REAL DEFAULT 0.0,
        doc_reference TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()

    # Migraties voor flexibele commissie (indien kolommen ontbreken in bestaande db)
    try:
        cursor.execute("ALTER TABLE orders ADD COLUMN carrier_price REAL DEFAULT 0.0")
    except Exception:
        pass

    # Migraties voor E-mailkoppeling & SMTP instellingen
    smtp_cols = [
        ("smtp_host", "TEXT DEFAULT 'smtp.gmail.com'"),
        ("smtp_port", "INTEGER DEFAULT 587"),
        ("smtp_security", "TEXT DEFAULT 'tls'"),
        ("smtp_user", "TEXT DEFAULT ''"),
        ("smtp_pass", "TEXT DEFAULT ''"),
        ("smtp_sender_name", "TEXT DEFAULT 'Transito Intermediazioni S.r.l.'"),
        ("smtp_sender_email", "TEXT DEFAULT ''"),
        ("principal_email", "TEXT DEFAULT 'administratie@veldhoventransport.nl'"),
        ("accountant_email", "TEXT DEFAULT 'studio.rossi@commercialisti.it'")
    ]
    for col_name, col_def in smtp_cols:
        try:
            cursor.execute(f"ALTER TABLE company_settings ADD COLUMN {col_name} {col_def}")
        except Exception:
            pass

    inv_cols = [
        ("email_sent_at", "TEXT"),
        ("email_sent_to", "TEXT")
    ]
    for col_name, col_def in inv_cols:
        try:
            cursor.execute(f"ALTER TABLE invoices ADD COLUMN {col_name} {col_def}")
        except Exception:
            pass

    # Migraties voor Auth Sessies en Pincode
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS auth_sessions (
        token TEXT PRIMARY KEY,
        expires_at REAL NOT NULL,
        device_info TEXT
    )
    """)
    for col_name, col_def in [
        ("auth_pin_hash", "TEXT"),
        ("auth_pin_salt", "TEXT"),
        ("auth_enabled", "INTEGER DEFAULT 0")
    ]:
        try:
            cursor.execute(f"ALTER TABLE company_settings ADD COLUMN {col_name} {col_def}")
        except Exception:
            pass

    # Zet auth_enabled standaard op 0 zodat gebruikers nooit per ongeluk geblokkeerd worden
    try:
        cursor.execute("UPDATE company_settings SET auth_enabled = 0 WHERE id = 1")
    except Exception:
        pass

    # Controleer of er al data aanwezig is
    cursor.execute("SELECT COUNT(*) FROM company_settings")
    if cursor.fetchone()[0] == 0:
        seed_sample_data(conn)
    else:
        # Controleer of rekeningschema gevuld is
        cursor.execute("SELECT COUNT(*) FROM chart_of_accounts")
        if cursor.fetchone()[0] == 0:
            seed_accounting_data(conn)

    conn.close()


def seed_sample_data(conn):
    cursor = conn.cursor()

    # 1. Eigen intermediair onderneming + Exclusief Partner Transportbedrijf
    cursor.execute("""
    INSERT INTO company_settings (
        id, name, legal_form, vat_number, fiscal_code, address, zip, city, province, country,
        pec, sdi_code, regime_fiscale, iban, swift, rea_number, capital, sdi_provider, test_mode,
        principal_name, principal_country, principal_vat, principal_address, principal_zip, principal_city,
        principal_pec, principal_sdi, default_commission_type, default_commission_rate, default_commission_fixed
    ) VALUES (
        1, 'Transito Intermediazioni S.r.l.', 'S.r.l.', 'IT09876543210', '09876543210',
        'Via Macello 18 / Schlachthofstraße 18', '39100', 'Bolzano', 'BZ', 'IT',
        'transito.intermediazioni@legalmail.it', 'M5UXCR1', 'RF01',
        'IT60X0542811101000000123456', 'CRBZIT2B', 'BZ-241598', 100000.00,
        'Aruba / Fatture in Cloud API Gateway', 1,
        'Veldhoven International Transport B.V.', 'NL', 'NL854729381B01', 'Transportlaan 14', '5504 KR', 'Veldhoven',
        'administratie@veldhoventransport.nl', 'XXXXXXX', 'percentage', 10.0, 200.0
    )
    """)

    # 2. Relaties: Klanten / Verladers
    clients = [
        ('client', 'Heineken Supply Chain B.V.', 'NL', 'NL005837264B01', 'NL005837264B01', 'XXXXXXX', 'logistics@heineken.com', 'supply@heineken.com', '+31 20 523 9239', 'Burgemeester Smeetsweg 1', '2382 PH', 'Zoeterwoude', '', 1),
        ('client', 'Barilla G. e R. Fratelli S.p.A.', 'IT', 'IT01650310340', '01650310340', 'SUBM70N', 'barilla.logistica@pec.it', 'spedizioni@barilla.it', '+39 0521 2621', 'Via Mantova 166', '43122', 'Parma', 'PR', 1),
        ('client', 'Bayerische Motoren Werke AG (BMW)', 'DE', 'DE129273398', 'DE129273398', '0000000', 'logistik@bmwgroup.com', 'freight@bmw.de', '+49 89 382 0', 'Petuelring 130', '80788', 'München', '', 1),
        ('client', 'Ferrero Commerciale Italia S.r.l.', 'IT', 'IT03629040048', '03629040048', 'A4707H7', 'ferrero.italia@pec.it', 'trasporti@ferrero.com', '+39 0173 2951', 'Piazzale Pietro Ferrero 1', '12051', 'Alba', 'CN', 1)
    ]

    for c in clients:
        cursor.execute("""
        INSERT INTO parties (type, name, country, vat_number, fiscal_code, sdi_code, pec, email, phone, address, zip, city, province, is_eu)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, c)

    # 3. Bemiddelde Opdrachten (Orders)
    today = datetime.now()
    d1 = (today - timedelta(days=5)).strftime("%Y-%m-%d")
    d2 = (today - timedelta(days=2)).strftime("%Y-%m-%d")
    d3 = (today + timedelta(days=1)).strftime("%Y-%m-%d")
    d4 = (today + timedelta(days=3)).strftime("%Y-%m-%d")

    orders_data = [
        ('BEM-2026-001', 1, 'NL', 'Zoeterwoude', 'Brouwerijweg 4', 'IT', 'Verona', 'Interporto Quadrante Europa',
         'Geconditioneerd bier op pallets (33 plts)', 22500, 33, 13.6, 'CMR-NL-90214', d1, d2, 2450.00, 'percentage', 10.0, 245.00, 'Geleverd', 'international',
         'Bemiddeld namens Veldhoven Transport. Verlader gefactureerd door Veldhoven Transport B.V.'),
        
        ('BEM-2026-002', 2, 'IT', 'Parma', 'Stabilimento Pedrignano', 'DE', 'München', 'Grossmarkthalle Halle 3',
         'Levensmiddelen droog (droge pasta)', 21000, 30, 13.6, 'CMR-IT-55102', d2, d3, 1850.00, 'percentage', 10.0, 185.00, 'Onderweg', 'international',
         'Bemiddeld voor Veldhoven Transport. Vaste retourlading naar Zuid-Duitsland.'),
        
        ('BEM-2026-003', 3, 'DE', 'München', 'BMW Werk 1.1', 'IT', 'Modena', 'Stabilimento Componenti',
         'Automotive componenten in gitterboxen', 16800, 24, 11.2, 'CMR-DE-77812', d3, d4, 2150.00, 'percentage', 10.0, 215.00, 'Bevestigd door Vervoerder', 'intra_eu',
         'Directe boeking via verlader BMW. Goedgekeurd door disponent Veldhoven Transport.'),

        ('BEM-2026-004', 4, 'IT', 'Alba', 'Piazzale Pietro Ferrero 1', 'NL', 'Breda', 'Logistiek Centrum Hazeldonk',
         'Chocolade en zoetwaren (temperatuurgecontroleerd 16°C)', 20000, 32, 13.6, 'CMR-IT-99201', d3, d4, 2600.00, 'percentage', 10.0, 260.00, 'Aangemeld', 'international',
         'Verse productie transport. Verlader Ferrero betaalt rechtstreeks aan Veldhoven Transport.')
    ]

    for o in orders_data:
        cursor.execute("""
        INSERT INTO orders (order_number, client_id, origin_country, origin_city, origin_address,
                            destination_country, destination_city, destination_address, goods_description, weight_kg,
                            palettes, loading_meters, cmr_number, pickup_date, delivery_date, freight_price,
                            commission_type, commission_rate, commission_amount, status, transport_type, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, o)

    conn.commit()
    seed_accounting_data(conn)


def seed_accounting_data(conn):
    cursor = conn.cursor()

    # 1. Rekeningschema (Piano dei Conti) in het Nederlands met Italiaanse referentie
    accounts = [
        # ACTIVA (Attivo)
        ('1001', 'Kas contanten (*Cassa contanti*)', 'Activa', 'Liquide middelen', 100.0, 100.0),
        ('1002', 'Bankrekening courant (*Banca c/c ordinario*)', 'Activa', 'Liquide middelen', 100.0, 100.0),
        ('1101', 'Te ontvangen provisies van vervoerder (*Crediti v/Mandanti*)', 'Activa', 'Vorderingen', 100.0, 100.0),
        ('1201', 'Te verrekenen btw / Voorbelasting (*Erario c/IVA a credito*)', 'Activa', 'Belastingvorderingen', 100.0, 100.0),
        
        # PASSIVA & EIGEN VERMOGEN (Passivo e Patrimonio Netto)
        ('2001', 'Gestort Aandelenkapitaal (*Capitale Sociale € 100.000*)', 'Passiva', 'Eigen Vermogen', 100.0, 100.0),
        ('2101', 'Crediteuren / Te betalen leveranciers (*Debiti v/Fornitori*)', 'Passiva', 'Schulden', 100.0, 100.0),
        ('2201', 'Verschuldigde btw (*Erario c/IVA a debito*)', 'Passiva', 'Belastingschulden', 100.0, 100.0),
        ('2202', 'Belastingschuld IRES & IRAP (*Debiti tributari*)', 'Passiva', 'Belastingschulden', 100.0, 100.0),
        
        # OPBRENGSTEN (Ricavi)
        ('4001', 'Bemiddelingsprovisies transport (*Ricavi provvigioni attive*)', 'Opbrengsten', 'Bedrijfsopbrengsten', 100.0, 100.0),
        ('4002', 'Doorbelaste kosten en overige opbrengsten', 'Opbrengsten', 'Overige opbrengsten', 100.0, 100.0),
        
        # BEDRIJFSKOSTEN (Costi della Produzione ex art. 2425 c.c.)
        ('5001', 'Kosten Boekhouder & Fiscaal Adviseur (*Commercialista*)', 'Kosten', 'Zakelijke dienstverlening', 100.0, 100.0),
        ('5002', 'Software, PEC en SDI Elektronische Facturatie', 'Kosten', 'IT & Software', 100.0, 100.0),
        ('5003', 'Telefoon- en Internetkosten (80% fiscaal aftrekbaar TUIR)', 'Kosten', 'Communicatie', 80.0, 100.0),
        ('5004', 'Kantoorhuur en Huisvestingskosten', 'Kosten', 'Huisvesting', 100.0, 100.0),
        ('5005', 'Reis- en Representatiekosten', 'Kosten', 'Algemene kosten', 75.0, 100.0),
        ('5006', 'Bankkosten en Betalingsverkeer (Btw-vrijgesteld art. 10)', 'Kosten', 'Financiële lasten', 100.0, 0.0),
        ('5007', 'Beroepsaansprakelijkheidsverzekering Intermediair (RC)', 'Kosten', 'Verzekeringen', 100.0, 0.0)
    ]

    for a in accounts:
        cursor.execute("""
        INSERT OR REPLACE INTO chart_of_accounts (code, name, category, subcategory, tax_deductibility_pct, vat_deductibility_pct)
        VALUES (?, ?, ?, ?, ?, ?)
        """, a)

    # 2. Voorbeeld kostenfacturen in het Nederlands (Registro IVA Acquisti)
    today = datetime.now()
    d1 = (today - timedelta(days=20)).strftime("%Y-%m-%d")
    d2 = (today - timedelta(days=12)).strftime("%Y-%m-%d")
    d3 = (today - timedelta(days=5)).strftime("%Y-%m-%d")
    d4 = (today - timedelta(days=2)).strftime("%Y-%m-%d")

    expenses_data = [
        (d1, 'Studio Commercialista Dott. Rossi & Associati', 'IT01245780211', 'FT-2026/89', 'Kwartaaladministratie, belastingaangifte en jaarrekening', '5001', 450.00, 22.0, 99.00, 549.00, 100.0, 'Betaald', 'Bankoverschrijving (MP05)'),
        (d2, 'Aruba S.p.A. / SDI Facturatie Hub', 'IT01573850516', 'AR-992147', 'Jaarabonnement SDI-koppeling, wettelijke archivering en PEC e-mail', '5002', 120.00, 22.0, 26.40, 146.40, 100.0, 'Betaald', 'Creditcard'),
        (d3, 'TIM S.p.A. - Telecom Italia Zakelijk', 'IT00488410010', 'TIM-041829', 'Glasvezel internet kantoor en zakelijke mobiele abonnementen', '5003', 85.00, 22.0, 18.70, 103.70, 100.0, 'Betaald', 'Automatische incasso'),
        (d4, 'Cassa di Risparmio di Bolzano - Sparkasse', 'IT00152980215', 'STR-092026', 'Kosten zakelijke betaalrekening en SEPA-overschrijvingen', '5006', 28.50, 0.0, 0.00, 28.50, 100.0, 'Betaald', 'Directe bankafschrijving')
    ]

    for exp in expenses_data:
        cursor.execute("""
        INSERT OR REPLACE INTO expenses (id, date, supplier_name, supplier_vat, invoice_number, description, account_code,
                              imponibile, vat_rate, vat_amount, total_amount, vat_deductible_pct, payment_status, payment_method)
        VALUES ((SELECT id FROM expenses WHERE invoice_number = ?), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (exp[3], exp[0], exp[1], exp[2], exp[3], exp[4], exp[5], exp[6], exp[7], exp[8], exp[9], exp[10], exp[11], exp[12]))

    conn.commit()


def get_company_settings():
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM company_settings WHERE id = 1").fetchone()
    conn.close()
    return dict(row) if row else {}


def update_company_settings(data: dict):
    conn = get_db_connection()
    current = conn.execute("SELECT * FROM company_settings WHERE id = 1").fetchone()
    current_dict = dict(current) if current else {}

    for k, v in data.items():
        if v is not None:
            current_dict[k] = v

    conn.execute("""
    UPDATE company_settings SET
        name = ?, legal_form = ?, vat_number = ?, fiscal_code = ?, address = ?, zip = ?,
        city = ?, province = ?, country = ?, pec = ?, sdi_code = ?, regime_fiscale = ?,
        iban = ?, swift = ?, rea_number = ?, capital = ?, sdi_provider = ?, test_mode = ?,
        principal_name = ?, principal_country = ?, principal_vat = ?, principal_address = ?,
        principal_zip = ?, principal_city = ?, principal_pec = ?, principal_sdi = ?,
        default_commission_type = ?, default_commission_rate = ?, default_commission_fixed = ?,
        smtp_host = ?, smtp_port = ?, smtp_security = ?, smtp_user = ?, smtp_pass = ?,
        smtp_sender_name = ?, smtp_sender_email = ?, principal_email = ?, accountant_email = ?
    WHERE id = 1
    """, (
        current_dict.get("name"), current_dict.get("legal_form"), current_dict.get("vat_number"), current_dict.get("fiscal_code"),
        current_dict.get("address"), current_dict.get("zip"), current_dict.get("city"), current_dict.get("province"),
        current_dict.get("country") or "IT", current_dict.get("pec") or "", current_dict.get("sdi_code") or "0000000", current_dict.get("regime_fiscale") or "RF01",
        current_dict.get("iban") or "", current_dict.get("swift") or "", current_dict.get("rea_number") or "", safe_float(current_dict.get("capital"), 100000.0),
        current_dict.get("sdi_provider") or "Aruba / Fatture in Cloud API Gateway", safe_int(current_dict.get("test_mode"), 1),
        current_dict.get("principal_name") or "Veldhoven International Transport B.V.", current_dict.get("principal_country") or "NL", current_dict.get("principal_vat") or "NL854729381B01",
        current_dict.get("principal_address") or "Transportlaan 14", current_dict.get("principal_zip") or "5504 KR", current_dict.get("principal_city") or "Veldhoven",
        current_dict.get("principal_pec") or "", current_dict.get("principal_sdi") or "XXXXXXX",
        current_dict.get("default_commission_type") or "percentage",
        safe_float(current_dict.get("default_commission_rate"), 10.0),
        safe_float(current_dict.get("default_commission_fixed"), 200.0),
        current_dict.get("smtp_host") or "smtp.gmail.com", safe_int(current_dict.get("smtp_port"), 587),
        current_dict.get("smtp_security") or "tls", current_dict.get("smtp_user") or "",
        current_dict.get("smtp_pass") or "", current_dict.get("smtp_sender_name") or "Transito Intermediazioni S.r.l.",
        current_dict.get("smtp_sender_email") or "", current_dict.get("principal_email") or "administratie@veldhoventransport.nl",
        current_dict.get("accountant_email") or ""
    ))
    conn.commit()
    conn.close()


def get_stats():
    conn = get_db_connection()
    c = conn.cursor()
    
    # 1. Totaal bemiddeld vrachtvolume en totale provisie
    c.execute("SELECT COUNT(*), COALESCE(SUM(freight_price), 0), COALESCE(SUM(commission_amount), 0) FROM orders")
    row = c.fetchone()
    total_orders = row[0]
    total_freight_volume = round(row[1], 2)
    total_earned_commissions = round(row[2], 2)
    avg_commission = round(total_earned_commissions / total_orders, 2) if total_orders > 0 else 0

    c.execute("SELECT COUNT(*) FROM orders WHERE status IN ('Aangemeld', 'Bevestigd door Vervoerder', 'Onderweg')")
    active_orders = c.fetchone()[0]

    c.execute("SELECT COALESCE(SUM(commission_amount), 0) FROM orders WHERE status != 'Commissie Gefactureerd'")
    unbilled_commissions = round(c.fetchone()[0], 2)

    c.execute("SELECT COUNT(*) FROM invoices")
    total_commission_invoices = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM invoices WHERE sdi_status = 'Geaccepteerd (Consegnata)'")
    sdi_accepted = c.fetchone()[0]

    # 2. Boekhoudkundige Totalen (Kosten, BTW en Winst)
    c.execute("SELECT COALESCE(SUM(imponibile), 0), COALESCE(SUM(vat_amount), 0), COALESCE(SUM(total_amount), 0) FROM expenses")
    exp_row = c.fetchone()
    total_expenses_excl = round(exp_row[0], 2)
    vat_purchases_credito = round(exp_row[1], 2)
    total_expenses_incl = round(exp_row[2], 2)

    # Omzet (Ricavi) uit uitgevoerde opdrachten of facturen
    c.execute("SELECT COALESCE(SUM(subtotal), 0), COALESCE(SUM(vat_amount), 0) FROM invoices")
    inv_row = c.fetchone()
    invoiced_revenue = round(inv_row[0], 2)
    vat_sales_debito = round(inv_row[1], 2)

    # Bruto Bedrijfsresultaat (EBITDA / Risultato Operativo)
    gross_operating_profit = round(total_earned_commissions - total_expenses_excl, 2)

    # Geschatte Italiaanse Belastingen (IRES 24% + IRAP ~3.9% over winst)
    estimated_tax_rate = 27.9 # 24% IRES + 3.9% IRAP
    estimated_taxes = round(max(0, gross_operating_profit * (estimated_tax_rate / 100.0)), 2)
    net_profit = round(gross_operating_profit - estimated_taxes, 2)

    # BTW Saldo (Liquidazione IVA): Debito - Credito
    vat_balance = round(vat_sales_debito - vat_purchases_credito, 2)

    company = conn.execute("SELECT principal_name, default_commission_rate FROM company_settings WHERE id = 1").fetchone()
    principal_name = company["principal_name"] if company else "Partner Transportbedrijf"
    default_rate = company["default_commission_rate"] if company else 10.0

    conn.close()
    return {
        "total_orders": total_orders,
        "active_orders": active_orders,
        "total_freight_volume": total_freight_volume,
        "total_earned_commissions": total_earned_commissions,
        "avg_commission": avg_commission,
        "unbilled_commissions": unbilled_commissions,
        "total_commission_invoices": total_commission_invoices,
        "sdi_accepted": sdi_accepted,
        "principal_name": principal_name,
        "default_commission_rate": default_rate,
        
        # Boekhouding velden
        "total_expenses_excl": total_expenses_excl,
        "total_expenses_incl": total_expenses_incl,
        "gross_operating_profit": gross_operating_profit,
        "estimated_taxes": estimated_taxes,
        "net_profit": net_profit,
        "vat_sales_debito": vat_sales_debito,
        "vat_purchases_credito": vat_purchases_credito,
        "vat_balance": vat_balance
    }


def get_accounting_summary():
    """Genereert de volledige Italiaanse winst-en-verliesrekening en balans (Conto Economico & Stato Patrimoniale)."""
    conn = get_db_connection()

    # 1. Ricavi per Provvigioni (Valore della produzione A.1)
    orders_rev = conn.execute("SELECT COALESCE(SUM(commission_amount), 0) FROM orders").fetchone()[0]
    invoices_rev = conn.execute("SELECT COALESCE(SUM(subtotal), 0) FROM invoices").fetchone()[0]
    total_ricavi = round(max(orders_rev, invoices_rev), 2)

    # 2. Costi della produzione B.7, B.8, B.14 per subcategorie
    expenses_rows = conn.execute("""
    SELECT e.*, c.name as account_name, c.subcategory, c.code as account_code
    FROM expenses e
    LEFT JOIN chart_of_accounts c ON e.account_code = c.code
    ORDER BY e.date DESC
    """).fetchall()
    expenses = [dict(r) for r in expenses_rows]

    total_costi_servizi = 0.0
    total_costi_godimento = 0.0
    total_oneri_diversi = 0.0
    vat_a_credito = 0.0

    for exp in expenses:
        sub = exp.get("subcategory") or ""
        imp = float(exp["imponibile"])
        vat = float(exp["vat_amount"])
        vat_a_credito += vat

        if any(k in sub.lower() for k in ["godimento", "ufficio", "huisvesting", "huur"]):
            total_costi_godimento += imp
        elif any(k in sub.lower() for k in ["oneri", "finanziari", "financiële", "bank", "algemene"]):
            total_oneri_diversi += imp
        else:
            total_costi_servizi += imp

    total_costi = round(total_costi_servizi + total_costi_godimento + total_oneri_diversi, 2)
    ebitda = round(total_ricavi - total_costi, 2)

    # Belastingen
    ires = round(max(0, ebitda * 0.24), 2) # IRES 24%
    irap = round(max(0, (total_ricavi - total_costi_servizi) * 0.039), 2) # IRAP ~3.9%
    total_imposte = round(ires + irap, 2)
    utile_netto = round(ebitda - total_imposte, 2)

    # BTW Afrekening (Liquidazione IVA)
    vat_a_debito = conn.execute("SELECT COALESCE(SUM(vat_amount), 0) FROM invoices").fetchone()[0]
    saldo_iva = round(vat_a_debito - vat_a_credito, 2)

    # Balans (Stato Patrimoniale)
    company = conn.execute("SELECT capital FROM company_settings WHERE id = 1").fetchone()
    capitale_sociale = company["capital"] if company else 100000.0

    # Cassa en Banken
    disponibilita_liquide = round(capitale_sociale + total_ricavi - total_costi - total_imposte, 2)
    crediti_clienti = round(conn.execute("SELECT COALESCE(SUM(commission_amount), 0) FROM orders WHERE status != 'Commissie Gefactureerd'").fetchone()[0], 2)

    conn.close()

    return {
        "conto_economico": {
            "ricavi_provvigioni": total_ricavi,
            "costi_servizi": round(total_costi_servizi, 2),
            "costi_godimento": round(total_costi_godimento, 2),
            "oneri_diversi": round(total_oneri_diversi, 2),
            "totale_costi_produzione": total_costi,
            "differenza_a_b": ebitda,
            "ires_24": ires,
            "irap_3_9": irap,
            "totale_imposte": total_imposte,
            "utile_netto": utile_netto
        },
        "stato_patrimoniale": {
            "attivo_circolante": {
                "disponibilita_liquide": disponibilita_liquide,
                "crediti_mandanti": crediti_clienti,
                "crediti_iva": round(abs(saldo_iva), 2) if saldo_iva < 0 else 0.0
            },
            "patrimonio_netto": {
                "capitale_sociale": capitale_sociale,
                "utile_esercizio": utile_netto
            },
            "debiti": {
                "debiti_fornitori": round(sum(e["total_amount"] for e in expenses if e["payment_status"] != "Betaald"), 2),
                "debiti_tributari_iva": round(saldo_iva, 2) if saldo_iva > 0 else 0.0,
                "debiti_imposte_ires_irap": total_imposte
            }
        },
        "liquidazione_iva": {
            "iva_vendite_debito": round(vat_a_debito, 2),
            "iva_acquisti_credito": round(vat_a_credito, 2),
            "saldo_iva": saldo_iva,
            "tipo_saldo": "Te betalen btw (af te dragen via Modello F24)" if saldo_iva > 0 else "Btw-tegoed / Voorbelasting (te verrekenen met volgend kwartaal)",
            "codice_tributo_f24": "6031" if saldo_iva > 0 else "-"
        },
        "expenses": expenses
    }


def verify_app_pin(entered_pin: str) -> bool:
    """Controleert of de ingevoerde pincode overeenkomt met de hash in de database."""
    import hashlib
    if not entered_pin:
        return False
    conn = get_db_connection()
    row = conn.execute("SELECT auth_pin_hash, auth_pin_salt FROM company_settings WHERE id = 1").fetchone()
    conn.close()
    if not row:
        return entered_pin.strip() == "2026"
    
    salt = row["auth_pin_salt"] or ""
    expected_hash = row["auth_pin_hash"] or ""
    
    # Als er nog geen hash is ingesteld, accepteer default 2026
    if not expected_hash:
        return entered_pin.strip() == "2026"
        
    computed = hashlib.sha256((salt + entered_pin.strip()).encode("utf-8")).hexdigest()
    return computed == expected_hash


def set_app_pin(new_pin: str) -> bool:
    """Stelt een nieuwe pincode in en slaat deze gehasht op met een unieke salt."""
    import hashlib
    import os
    if not new_pin or len(new_pin.strip()) < 4:
        return False
    salt = os.urandom(16).hex()
    pin_hash = hashlib.sha256((salt + new_pin.strip()).encode("utf-8")).hexdigest()
    conn = get_db_connection()
    conn.execute("""
        UPDATE company_settings
        SET auth_pin_hash = ?, auth_pin_salt = ?, auth_enabled = 1
        WHERE id = 1
    """, (pin_hash, salt))
    conn.commit()
    conn.close()
    return True


def toggle_app_auth(enabled: bool) -> bool:
    """Schakelt de pincodebeveiliging in of uit."""
    conn = get_db_connection()
    conn.execute("UPDATE company_settings SET auth_enabled = ? WHERE id = 1", (1 if enabled else 0,))
    conn.commit()
    conn.close()
    return True


def is_auth_enabled() -> bool:
    """Geeft aan of pincodebeveiliging actief is."""
    conn = get_db_connection()
    row = conn.execute("SELECT auth_enabled FROM company_settings WHERE id = 1").fetchone()
    conn.close()
    if not row:
        return False
    return bool(row["auth_enabled"])


def create_auth_session(token: str, expires_in_seconds: int = 30 * 86400, device_info: str = "") -> bool:
    """Slaat een nieuwe inlogsessie op in de database."""
    import time
    expires_at = time.time() + expires_in_seconds
    conn = get_db_connection()
    conn.execute("INSERT OR REPLACE INTO auth_sessions (token, expires_at, device_info) VALUES (?, ?, ?)",
                 (token, expires_at, device_info))
    conn.commit()
    conn.close()
    return True


def validate_auth_session(token: str) -> bool:
    """Controleert of een sessietoken geldig en niet verlopen is."""
    import time
    if not token:
        return False
    conn = get_db_connection()
    row = conn.execute("SELECT expires_at FROM auth_sessions WHERE token = ?", (token,)).fetchone()
    conn.close()
    if not row:
        return False
    return float(row["expires_at"]) > time.time()


def delete_auth_session(token: str) -> bool:
    """Verwijdert een sessietoken bij uitloggen."""
    conn = get_db_connection()
    conn.execute("DELETE FROM auth_sessions WHERE token = ?", (token,))
    conn.commit()
    conn.close()
    return True

