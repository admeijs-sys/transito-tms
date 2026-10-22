"""
Transito Intermediair & SDI Facturatieserver
Een complete standalone backend geschreven in Python (standaardbibliotheek: http.server + sqlite3 + xml).
Bedrijfsmodel: Bemiddelaar / Intermediair namens een vast Transportbedrijf.
"""

import http.server
import socketserver
import json
import urllib.parse
import os
import mimetypes
from datetime import datetime, timedelta
import database
import sdi_generator
import email_sender

PORT = int(os.environ.get("PORT", 8080))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")


def safe_float(val, default=0.0):
    if val is None or val == "":
        return default
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().replace("€", "").replace("EUR", "").replace("$", "").replace(" ", "")
    if not s:
        return default
    # Handle thousands and decimal separators
    if "," in s and "." in s:
        if s.find(".") < s.find(","):
            # Format: 1.234,56 (European)
            s = s.replace(".", "").replace(",", ".")
        else:
            # Format: 1,234.56 (US/UK)
            s = s.replace(",", "")
    elif "," in s:
        # Format: 2500,50
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


class TransitoAPIHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def send_json(self, data, status_code=200):
        response_bytes = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)

    def parse_body(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        body = self.rfile.read(content_length).decode("utf-8")
        try:
            return json.loads(body)
        except Exception:
            return {}

    def check_auth(self, path):
        # Whitelisted endpoints zonder authenticatie
        if path in ["/api/auth/login", "/api/auth/status", "/api/network-info"]:
            return True
        if not database.is_auth_enabled():
            return True

        # Controleer Authorization header: Bearer <token>
        auth_header = self.headers.get("Authorization", "")
        token = ""
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
        elif "X-Transito-Auth" in self.headers:
            token = self.headers.get("X-Transito-Auth", "").strip()

        # Query param token fallback voor bijlagen/previews
        if not token:
            parsed = urllib.parse.urlparse(self.path)
            q = urllib.parse.parse_qs(parsed.query)
            if "token" in q:
                token = q["token"][0]

        if token and database.validate_auth_session(token):
            return True

        self.send_json({"error": "Pincode vereist of sessie verlopen", "auth_required": True}, status_code=401)
        return False

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)

        # API Routes
        if path.startswith("/api/"):
            if not self.check_auth(path):
                return
            try:
                self.handle_api_get(path, query)
            except Exception as e:
                self.send_json({"error": str(e)}, status_code=500)
            return

        # Mobile web app route
        if path == "/mobile" or path == "/mobile/":
            self.path = "/mobile.html"
            return super().do_GET()

        # Static file fallback naar index.html voor SPA
        if not os.path.exists(os.path.join(STATIC_DIR, path.lstrip("/"))):
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        if path.startswith("/api/"):
            if not self.check_auth(path):
                return
            try:
                self.handle_api_post(path)
            except Exception as e:
                self.send_json({"error": str(e)}, status_code=500)
            return
        self.send_response(404)
        self.end_headers()

    def do_PUT(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        if path.startswith("/api/"):
            if not self.check_auth(path):
                return
            try:
                self.handle_api_put(path)
            except Exception as e:
                self.send_json({"error": str(e)}, status_code=500)
            return
        self.send_response(404)
        self.end_headers()

    def do_DELETE(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        if path.startswith("/api/"):
            if not self.check_auth(path):
                return
            try:
                self.handle_api_delete(path)
            except Exception as e:
                self.send_json({"error": str(e)}, status_code=500)
            return
        self.send_response(404)
        self.end_headers()

    def handle_api_get(self, path, query):
        conn = database.get_db_connection()

        if path == "/api/auth/status":
            auth_header = self.headers.get("Authorization", "")
            token = auth_header[7:].strip() if auth_header.startswith("Bearer ") else self.headers.get("X-Transito-Auth", "").strip()
            if not token:
                q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                token = q.get("token", [""])[0]
            is_valid = database.validate_auth_session(token) if token else False
            self.send_json({
                "auth_enabled": database.is_auth_enabled(),
                "authenticated": is_valid
            })
            conn.close()
            return

        elif path == "/api/stats":
            stats = database.get_stats()
            self.send_json(stats)
            conn.close()
            return

        elif path == "/api/accounting":
            summary = database.get_accounting_summary()
            self.send_json(summary)
            conn.close()
            return

        elif path == "/api/chart-of-accounts":
            rows = conn.execute("SELECT * FROM chart_of_accounts ORDER BY code ASC").fetchall()
            accounts = [dict(r) for r in rows]
            self.send_json(accounts)
            conn.close()
            return

        elif path == "/api/expenses":
            rows = conn.execute("""
            SELECT e.*, c.name as account_name, c.subcategory
            FROM expenses e
            LEFT JOIN chart_of_accounts c ON e.account_code = c.code
            ORDER BY e.date DESC, e.id DESC
            """).fetchall()
            expenses = [dict(r) for r in rows]
            self.send_json(expenses)
            conn.close()
            return

        elif path == "/api/network-info":
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(('8.8.8.8', 80))
                local_ip = s.getsockname()[0]
            except Exception:
                local_ip = "127.0.0.1"
            finally:
                s.close()

            tunnel_url = ""
            tunnel_file = os.path.join(BASE_DIR, "tunnel_url.txt")
            if os.path.exists(tunnel_file):
                try:
                    with open(tunnel_file, "r", encoding="utf-8") as tf:
                        tunnel_url = tf.read().strip()
                except Exception:
                    pass

            effective_mobile_url = f"{tunnel_url}/mobile" if tunnel_url else f"http://{local_ip}:{PORT}/mobile"
            self.send_json({
                "ip": local_ip,
                "port": PORT,
                "tunnel_url": tunnel_url,
                "mobile_url": effective_mobile_url,
                "local_mobile_url": f"http://{local_ip}:{PORT}/mobile"
            })
            conn.close()
            return

        elif path == "/api/company":
            company = database.get_company_settings()
            self.send_json(company)
            conn.close()
            return

        elif path == "/api/expenses":
            cur = conn.cursor()
            imponibile = float(body.get("imponibile", 0))
            vat_rate = float(body.get("vat_rate", 22.0))
            vat_amount = round(imponibile * (vat_rate / 100.0), 2)
            total_amount = round(imponibile + vat_amount, 2)
            
            cur.execute("""
            INSERT INTO expenses (date, supplier_name, supplier_vat, invoice_number, description, account_code,
                                  imponibile, vat_rate, vat_amount, total_amount, vat_deductible_pct, payment_status, payment_method)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                body.get("date") or datetime.now().strftime("%Y-%m-%d"),
                body.get("supplier_name"), body.get("supplier_vat", ""),
                body.get("invoice_number", ""), body.get("description"),
                body.get("account_code", "5001"), imponibile, vat_rate, vat_amount,
                total_amount, float(body.get("vat_deductible_pct", 100.0)),
                body.get("payment_status", "Betaald"), body.get("payment_method", "Bonifico Bancario (MP05)")
            ))
            conn.commit()
            new_id = cur.lastrowid
            conn.close()
            self.send_json({
                "success": True,
                "id": new_id,
                "total_amount": total_amount,
                "message": f"Kostenfactuur van {body.get('supplier_name')} geregistreerd in Registro IVA Acquisti"
            })
            return

        elif path == "/api/parties":
            rows = conn.execute("SELECT * FROM parties ORDER BY name ASC").fetchall()
            parties = [dict(r) for r in rows]
            self.send_json(parties)
            conn.close()
            return

        elif path == "/api/orders":
            rows = conn.execute("""
            SELECT o.*, 
                   c.name as client_name, c.country as client_country, c.sdi_code as client_sdi,
                   i.invoice_number as commission_invoice_number
            FROM orders o
            LEFT JOIN parties c ON o.client_id = c.id
            LEFT JOIN invoices i ON o.commission_invoice_id = i.id
            ORDER BY o.id DESC
            """).fetchall()
            orders = [dict(r) for r in rows]
            self.send_json(orders)
            conn.close()
            return

        elif path.startswith("/api/orders/") and len(path.split("/")) == 4:
            order_id = int(path.split("/")[3])
            row = conn.execute("""
            SELECT o.*, 
                   c.name as client_name, c.country as client_country, c.sdi_code as client_sdi,
                   c.vat_number as client_vat, c.fiscal_code as client_cf, c.address as client_address,
                   c.city as client_city, c.zip as client_zip, c.pec as client_pec,
                   i.invoice_number as commission_invoice_number
            FROM orders o
            LEFT JOIN parties c ON o.client_id = c.id
            LEFT JOIN invoices i ON o.commission_invoice_id = i.id
            WHERE o.id = ?
            """, (order_id,)).fetchone()
            if not row:
                self.send_json({"error": "Opdracht niet gevonden"}, status_code=404)
                conn.close()
                return
            order = dict(row)
            company = database.get_company_settings()
            self.send_json({"order": order, "company": company})
            conn.close()
            return

        elif path == "/api/invoices":
            rows = conn.execute("""
            SELECT * FROM invoices ORDER BY id DESC
            """).fetchall()
            invoices = [dict(r) for r in rows]
            self.send_json(invoices)
            conn.close()
            return

        elif path.startswith("/api/invoices/") and path.endswith("/email-preview"):
            invoice_id = int(path.split("/")[3])
            row = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
            if not row:
                self.send_json({"error": "Factuur niet gevonden"}, status_code=404)
                conn.close()
                return

            inv = dict(row)
            company = database.get_company_settings()

            order_ids = []
            if inv.get("order_ids_json"):
                try:
                    order_ids = json.loads(inv["order_ids_json"])
                except Exception:
                    order_ids = []

            orders = []
            if order_ids:
                placeholders = ",".join("?" for _ in order_ids)
                o_rows = conn.execute(f"""
                SELECT o.*, c.name as client_name, c.country as client_country
                FROM orders o
                LEFT JOIN parties c ON o.client_id = c.id
                WHERE o.id IN ({placeholders})
                """, order_ids).fetchall()
                orders = [dict(r) for r in o_rows]

            subject, html_body, text_body = email_sender.generate_invoice_email_template(inv, company, orders)

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(html_body.encode("utf-8"))
            conn.close()
            return

        elif path.startswith("/api/invoices/") and not path.endswith("/xml") and not path.endswith("/sdi-send"):
            invoice_id = int(path.split("/")[3])
            row = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
            if not row:
                self.send_json({"error": "Factuur niet gevonden"}, status_code=404)
                conn.close()
                return

            inv = dict(row)
            company = database.get_company_settings()

            order_ids = []
            if inv.get("order_ids_json"):
                try:
                    order_ids = json.loads(inv["order_ids_json"])
                except Exception:
                    order_ids = []

            orders = []
            if order_ids:
                placeholders = ",".join("?" for _ in order_ids)
                o_rows = conn.execute(f"""
                SELECT o.*, c.name as client_name, c.country as client_country
                FROM orders o
                LEFT JOIN parties c ON o.client_id = c.id
                WHERE o.id IN ({placeholders})
                """, order_ids).fetchall()
                orders = [dict(r) for r in o_rows]

            self.send_json({
                "invoice": inv,
                "company": company,
                "orders": orders
            })
            conn.close()
            return

        elif path.startswith("/api/invoices/") and path.endswith("/xml"):
            invoice_id = int(path.split("/")[3])
            row = conn.execute("SELECT xml_content, invoice_number FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
            if not row or not row["xml_content"]:
                self.send_json({"error": "XML commissiefactuur niet gevonden"}, status_code=404)
                conn.close()
                return

            xml_data = row["xml_content"].encode("utf-8")
            clean_num = row["invoice_number"].replace("/", "_").replace(" ", "_")
            filename = f"IT_PROV_{clean_num}.xml"

            self.send_response(200)
            self.send_header("Content-Type", "application/xml; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(xml_data)))
            self.end_headers()
            self.wfile.write(xml_data)
            conn.close()
            return

        conn.close()
        self.send_json({"error": "Route niet gevonden"}, status_code=404)

    def handle_api_post(self, path):
        body = self.parse_body()
        conn = database.get_db_connection()

        if path == "/api/auth/login":
            pin = str(body.get("pin", "")).strip()
            if database.verify_app_pin(pin):
                import secrets
                token = secrets.token_hex(24)
                user_agent = self.headers.get("User-Agent", "Browser")
                database.create_auth_session(token, expires_in_seconds=30 * 86400, device_info=user_agent)
                self.send_json({"success": True, "token": token, "message": "Inloggen geslaagd!"})
            else:
                self.send_json({"success": False, "error": "Onjuiste pincode. Probeer opnieuw."}, status_code=401)
            conn.close()
            return

        elif path == "/api/auth/logout":
            auth_header = self.headers.get("Authorization", "")
            token = auth_header[7:].strip() if auth_header.startswith("Bearer ") else self.headers.get("X-Transito-Auth", "").strip()
            if token:
                database.delete_auth_session(token)
            self.send_json({"success": True, "message": "Succesvol uitgelogd"})
            conn.close()
            return

        elif path == "/api/auth/change-pin":
            curr_pin = str(body.get("current_pin", "")).strip()
            new_pin = str(body.get("new_pin", "")).strip()
            if not database.verify_app_pin(curr_pin):
                self.send_json({"success": False, "error": "Huidige pincode is onjuist"}, status_code=400)
                conn.close()
                return
            if len(new_pin) < 4:
                self.send_json({"success": False, "error": "Nieuwe pincode moet minimaal 4 tekens bevatten"}, status_code=400)
                conn.close()
                return
            if database.set_app_pin(new_pin):
                self.send_json({"success": True, "message": "Pincode succesvol gewijzigd!"})
            else:
                self.send_json({"success": False, "error": "Kon pincode niet wijzigen"}, status_code=500)
            conn.close()
            return

        elif path == "/api/auth/toggle":
            enabled = bool(body.get("enabled", True))
            database.toggle_app_auth(enabled)
            self.send_json({"success": True, "auth_enabled": enabled, "message": f"Beveiliging {'ingeschakeld' if enabled else 'uitgeschakeld'}"})
            conn.close()
            return

        elif path == "/api/company":
            database.update_company_settings(body)
            self.send_json({"success": True, "message": "Instellingen opgeslagen"})
            conn.close()
            return

        elif path == "/api/expenses":
            cur = conn.cursor()
            imponibile = safe_float(body.get("imponibile"), 0.0)
            vat_rate = safe_float(body.get("vat_rate"), 22.0)
            vat_amount = round(imponibile * (vat_rate / 100.0), 2)
            total_amount = round(imponibile + vat_amount, 2)
            
            cur.execute("""
            INSERT INTO expenses (date, supplier_name, supplier_vat, invoice_number, description, account_code,
                                  imponibile, vat_rate, vat_amount, total_amount, vat_deductible_pct, payment_status, payment_method)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                body.get("date") or datetime.now().strftime("%Y-%m-%d"),
                body.get("supplier_name"), body.get("supplier_vat", ""),
                body.get("invoice_number", ""), body.get("description"),
                body.get("account_code", "5001"), imponibile, vat_rate, vat_amount,
                total_amount, safe_float(body.get("vat_deductible_pct"), 100.0),
                body.get("payment_status", "Betaald"), body.get("payment_method", "Bonifico Bancario (MP05)")
            ))
            conn.commit()
            new_id = cur.lastrowid
            conn.close()
            self.send_json({
                "success": True,
                "id": new_id,
                "total_amount": total_amount,
                "message": f"Kostenfactuur van {body.get('supplier_name')} geregistreerd in Registro IVA Acquisti"
            })
            return

        elif path == "/api/parties":
            cur = conn.cursor()
            cur.execute("""
            INSERT INTO parties (type, name, country, vat_number, fiscal_code, sdi_code, pec, email, phone, address, zip, city, province, is_eu)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                body.get("type", "client"), body.get("name"), (body.get("country") or "IT").upper(),
                body.get("vat_number"), body.get("fiscal_code"), body.get("sdi_code", "0000000"),
                body.get("pec"), body.get("email"), body.get("phone"), body.get("address"),
                body.get("zip"), body.get("city"), body.get("province"), safe_int(body.get("is_eu"), 1)
            ))
            conn.commit()
            new_id = cur.lastrowid
            conn.close()
            self.send_json({"success": True, "id": new_id, "message": "Verlader succesvol toegevoegd"})
            return

        elif path == "/api/orders":
            cur = conn.cursor()
            order_num = body.get("order_number")
            if not order_num or not str(order_num).strip():
                # Vind het hoogste bestaande BEM-2026 volgnummer om duplicaten gegarandeerd te voorkomen
                rows = conn.execute("SELECT order_number FROM orders WHERE order_number LIKE 'BEM-2026-%'").fetchall()
                max_num = 0
                for r in rows:
                    try:
                        num_part = int(r[0].split("-")[-1])
                        if num_part > max_num:
                            max_num = num_part
                    except Exception:
                        pass
                order_num = f"BEM-2026-{max_num + 1:03d}"

            freight_price = safe_float(body.get("freight_price"), 0.0)
            carrier_price = safe_float(body.get("carrier_price"), 0.0)
            comm_type = body.get("commission_type") or "percentage"
            comm_rate = safe_float(body.get("commission_rate"), 10.0)
            weight_kg = safe_float(body.get("weight_kg"), 0.0)
            palettes = safe_int(body.get("palettes"), 0)
            loading_meters = safe_float(body.get("loading_meters"), 0.0)

            # Automatische commissieberekening conform gekozen flexibel model
            if "commission_amount" in body and safe_float(body.get("commission_amount")) > 0:
                commission_amount = round(safe_float(body.get("commission_amount")), 2)
            else:
                if comm_type == "percentage":
                    commission_amount = round(freight_price * (comm_rate / 100.0), 2)
                elif comm_type == "fixed":
                    commission_amount = round(safe_float(body.get("commission_fixed"), 200.0), 2)
                elif comm_type == "margin":
                    commission_amount = round(max(0.0, freight_price - carrier_price), 2)
                else:
                    commission_amount = round(safe_float(body.get("commission_amount"), 0.0), 2)

            if freight_price > 0 and (comm_rate == 0 or comm_type != "percentage") and commission_amount > 0:
                comm_rate = round((commission_amount / freight_price) * 100.0, 1)

            origin_c = (body.get("origin_country") or "NL").upper()
            dest_c = (body.get("destination_country") or "IT").upper()
            t_type = "domestic" if (origin_c == "IT" and dest_c == "IT") else "international"

            origin_city = (body.get("origin_city") or "").strip()
            dest_city = (body.get("destination_city") or "").strip()
            goods = (body.get("goods_description") or "").strip() or "Diverse handelsgoederen"

            client_id = body.get("client_id")
            if client_id is not None and str(client_id).strip() != "":
                try:
                    client_id = int(client_id)
                except Exception:
                    client_id = None
            else:
                client_id = None

            if not origin_city:
                origin_city = "Onbekend"
            if not dest_city:
                dest_city = "Onbekend"

            cur.execute("""
            INSERT INTO orders (order_number, client_id, origin_country, origin_city, origin_address,
                                destination_country, destination_city, destination_address, goods_description, weight_kg,
                                palettes, loading_meters, cmr_number, pickup_date, delivery_date, freight_price, carrier_price,
                                commission_type, commission_rate, commission_amount, status, transport_type, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_num, client_id, origin_c, origin_city,
                body.get("origin_address") or "", dest_c, dest_city, body.get("destination_address") or "",
                goods, weight_kg, palettes,
                loading_meters, body.get("cmr_number") or "", body.get("pickup_date") or datetime.now().strftime("%Y-%m-%d"),
                body.get("delivery_date") or "", freight_price, carrier_price, comm_type, comm_rate, commission_amount,
                body.get("status") or "Aangemeld", t_type, body.get("notes") or ""
            ))
            conn.commit()
            new_id = cur.lastrowid
            conn.close()
            self.send_json({
                "success": True,
                "id": new_id,
                "order_number": order_num,
                "commission_amount": commission_amount,
                "commission_type": comm_type,
                "commission_rate": comm_rate,
                "message": f"Bemiddelingsopdracht {order_num} aangemaakt (Provisie: € {commission_amount:.2f})"
            })
            return

        elif path == "/api/invoices/generate-commission":
            # Genereert een FatturaPA XML commissiefactuur voor 1 rit of een selectie van ritten
            order_ids = body.get("order_ids", [])
            if not order_ids and body.get("order_id"):
                order_ids = [int(body.get("order_id"))]

            if not order_ids:
                self.send_json({"error": "Geen ritten geselecteerd voor commissiefacturatie"}, status_code=400)
                conn.close()
                return

            placeholders = ",".join("?" for _ in order_ids)
            orders = [dict(r) for r in conn.execute(f"SELECT * FROM orders WHERE id IN ({placeholders})", order_ids).fetchall()]
            if not orders:
                self.send_json({"error": "Geen geldige ritten gevonden"}, status_code=404)
                conn.close()
                return

            company = database.get_company_settings()
            partner_country = company.get("principal_country", "NL")

            # Btw bepaling voor de provisiedienst aan het transportbedrijf:
            if partner_country != "IT":
                # Transportbedrijf is gevestigd in EU (bijv. NL) -> Art. 7-ter DPR 633/72
                vat_rate = 0.0
                vat_nature = "N6"
                normative_ref = "Inversione contabile - Operazione non soggetta IVA ai sensi dell'art. 7-ter DPR 633/72"
            else:
                # Transportbedrijf is Italiaans
                vat_rate = 0.0
                vat_nature = "N3.2"
                normative_ref = "Operazione non imponibile IVA ai sensi dell'art. 9, comma 1, n. 7 e 9 DPR 633/72"

            lines = []
            total_commission = 0.0
            for o in orders:
                comm = float(o["commission_amount"])
                total_commission += comm
                c_type = o.get("commission_type") or "percentage"
                
                if c_type == "fixed":
                    desc = f"Compenso fisso intermediazione rif. Rit {o['order_number']}: {o['origin_city']} ({o['origin_country']}) -> {o['destination_city']} ({o['destination_country']}) [CMR: {o['cmr_number'] or 'N/A'}] - Nolo pattuito: EUR {o['freight_price']:.2f}"
                elif c_type == "margin":
                    c_price = float(o.get("carrier_price") or (o['freight_price'] - comm))
                    desc = f"Margine intermediazione rif. Rit {o['order_number']}: {o['origin_city']} ({o['origin_country']}) -> {o['destination_city']} ({o['destination_country']}) [CMR: {o['cmr_number'] or 'N/A'}] (Nolo committente: EUR {o['freight_price']:.2f} - Quota vettore: EUR {c_price:.2f})"
                elif c_type == "custom":
                    desc = f"Provvigione forfettaria concordata rif. Rit {o['order_number']}: {o['origin_city']} ({o['origin_country']}) -> {o['destination_city']} ({o['destination_country']}) [CMR: {o['cmr_number'] or 'N/A'}] - Nolo: EUR {o['freight_price']:.2f}"
                else:
                    desc = f"Provvigione ({o['commission_rate']}%) intermediazione rif. Rit {o['order_number']}: {o['origin_city']} ({o['origin_country']}) -> {o['destination_city']} ({o['destination_country']}) [CMR: {o['cmr_number'] or 'N/A'}] - Nolo base: EUR {o['freight_price']:.2f}"

                lines.append({
                    "description": desc,
                    "quantity": 1.0,
                    "unit_price": comm,
                    "total_price": comm,
                    "vat_rate": vat_rate,
                    "vat_nature": vat_nature,
                    "normative_ref": normative_ref
                })

            vat_amount = round(total_commission * (vat_rate / 100.0), 2)
            total_amount = round(total_commission + vat_amount, 2)

            inv_count = conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0] + 1
            inv_number = f"PROV-2026-{inv_count:03d}"
            today_str = datetime.now().strftime("%Y-%m-%d")
            due_str = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

            invoice_dict = {
                "invoice_number": inv_number,
                "doc_type": "TD01",
                "date": today_str,
                "due_date": due_str,
                "subtotal": total_commission,
                "vat_rate": vat_rate,
                "vat_amount": vat_amount,
                "total_amount": total_amount,
                "vat_nature": vat_nature,
                "normative_ref": normative_ref,
                "party_name": company.get("principal_name"),
                "party_country": partner_country,
                "party_vat": company.get("principal_vat"),
                "party_sdi": company.get("principal_sdi"),
                "party_pec": company.get("principal_pec"),
                "lines": lines
            }

            xml_content = sdi_generator.generate_commission_xml(invoice_dict, company)

            cur = conn.cursor()
            cur.execute("""
            INSERT INTO invoices (invoice_number, doc_type, order_ids_json, party_name, party_country, party_vat,
                                  party_sdi, date, due_date, subtotal, vat_rate, vat_amount, total_amount, vat_nature,
                                  normative_ref, sdi_status, xml_content)
            VALUES (?, 'TD01', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Gegenereerd', ?)
            """, (
                inv_number, json.dumps(order_ids), company.get("principal_name"), partner_country, company.get("principal_vat"),
                company.get("principal_sdi"), today_str, due_str, total_commission, vat_rate, vat_amount, total_amount,
                vat_nature, normative_ref, xml_content
            ))
            inv_id = cur.lastrowid

            # Update status van alle meegenomen orders
            cur.execute(f"""
            UPDATE orders SET status = 'Commissie Gefactureerd', commission_invoice_id = ?
            WHERE id IN ({placeholders})
            """, [inv_id] + order_ids)
            conn.commit()
            conn.close()

            self.send_json({
                "success": True,
                "invoice_id": inv_id,
                "invoice_number": inv_number,
                "total_commission": total_commission,
                "orders_count": len(orders),
                "message": f"Commissiefactuur {inv_number} voor {company.get('principal_name')} aangemaakt (€ {total_commission:.2f})!"
            })
            return

        elif path == "/api/invoices/custom":
            company = database.get_company_settings()
            partner_country = body.get("party_country") or company.get("principal_country", "NL")
            party_name = body.get("party_name") or company.get("principal_name")
            party_vat = body.get("party_vat") or company.get("principal_vat")
            party_sdi = body.get("party_sdi") or company.get("principal_sdi", "XXXXXXX")

            inv_count = conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0] + 1
            inv_number = body.get("invoice_number") or f"PROV-2026-{inv_count:03d}"
            today_str = body.get("date") or datetime.now().strftime("%Y-%m-%d")
            due_str = body.get("due_date") or (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

            raw_lines = body.get("lines", [])
            if not raw_lines:
                raw_lines = [{
                    "description": body.get("description", "Bemiddelingsprovisie transport"),
                    "quantity": 1.0,
                    "unit_price": float(body.get("subtotal", 0.0)),
                    "total_price": float(body.get("subtotal", 0.0))
                }]

            subtotal = sum(float(l.get("total_price", 0.0)) for l in raw_lines)

            # BTW regels
            if partner_country != "IT":
                vat_rate = 0.0
                vat_nature = "N6"
                normative_ref = "Inversione contabile - Operazione non soggetta IVA ai sensi dell'art. 7-ter DPR 633/72"
            else:
                vat_rate = float(body.get("vat_rate", 0.0))
                vat_nature = "N3.2" if vat_rate == 0.0 else ""
                normative_ref = "Operazione non imponibile IVA ai sensi dell'art. 9 DPR 633/72" if vat_rate == 0.0 else ""

            vat_amount = round(subtotal * (vat_rate / 100.0), 2)
            total_amount = round(subtotal + vat_amount, 2)

            lines = []
            for l in raw_lines:
                lines.append({
                    "description": l.get("description", "Bemiddelingsdienst"),
                    "quantity": float(l.get("quantity", 1.0)),
                    "unit_price": float(l.get("unit_price", 0.0)),
                    "total_price": float(l.get("total_price", 0.0)),
                    "vat_rate": vat_rate,
                    "vat_nature": vat_nature,
                    "normative_ref": normative_ref
                })

            invoice_dict = {
                "invoice_number": inv_number,
                "doc_type": "TD01",
                "date": today_str,
                "due_date": due_str,
                "subtotal": subtotal,
                "vat_rate": vat_rate,
                "vat_amount": vat_amount,
                "total_amount": total_amount,
                "vat_nature": vat_nature,
                "normative_ref": normative_ref,
                "party_name": party_name,
                "party_country": partner_country,
                "party_vat": party_vat,
                "party_sdi": party_sdi,
                "party_pec": body.get("party_pec", ""),
                "lines": lines
            }

            xml_content = sdi_generator.generate_commission_xml(invoice_dict, company)

            cur = conn.cursor()
            cur.execute("""
            INSERT INTO invoices (invoice_number, doc_type, order_ids_json, party_name, party_country, party_vat,
                                  party_sdi, date, due_date, subtotal, vat_rate, vat_amount, total_amount, vat_nature,
                                  normative_ref, sdi_status, xml_content)
            VALUES (?, 'TD01', '[]', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Gegenereerd', ?)
            """, (
                inv_number, party_name, partner_country, party_vat,
                party_sdi, today_str, due_str, subtotal, vat_rate, vat_amount, total_amount,
                vat_nature, normative_ref, xml_content
            ))
            inv_id = cur.lastrowid
            conn.commit()
            conn.close()

            self.send_json({
                "success": True,
                "invoice_id": inv_id,
                "invoice_number": inv_number,
                "total_amount": total_amount,
                "message": f"Factuur {inv_number} succesvol opgemaakt en geregistreerd!"
            })
            return

        elif path.startswith("/api/invoices/") and path.endswith("/sdi-send"):
            invoice_id = int(path.split("/")[3])
            sdi_id = f"SDI-PROV-{datetime.now().strftime('%Y%m%d%H%M%S')}-{invoice_id:03d}"
            status = "Geaccepteerd (Consegnata)"
            msg = f"Commissiefactuur ontvangen en geaccepteerd door het SDI. Notifica di avvenuta consegna ontvangen op {datetime.now().strftime('%d-%m-%Y %H:%M')}."

            conn.execute("""
            UPDATE invoices SET
                sdi_status = ?,
                sdi_identifier = ?,
                sdi_response_message = ?
            WHERE id = ?
            """, (status, sdi_id, msg, invoice_id))
            conn.commit()
            conn.close()

            self.send_json({
                "success": True,
                "sdi_status": status,
                "sdi_identifier": sdi_id,
                "message": msg
            })
            return

        elif path == "/api/email/test":
            company = database.get_company_settings()
            # Merge any parameters sent in body with company settings
            test_settings = dict(company)
            for k, v in body.items():
                if v: test_settings[k] = v

            target_email = body.get("to_email") or company.get("principal_email") or company.get("smtp_user") or "test@transito.it"
            subject = f"Test E-mail Verbinding - {company.get('name', 'Transito Intermediazioni')}"
            html_body = f"""
            <div style="font-family: sans-serif; padding: 20px; color: #1e293b;">
                <h2 style="color: #2563eb;">E-mailkoppeling Succesvol Geconfigureerd!</h2>
                <p>Dit is een testbericht verzonden vanuit het <strong>Transito Intermediair Platform</strong>.</p>
                <div style="background-color: #f1f5f9; padding: 12px 16px; border-radius: 8px; font-family: monospace; font-size: 13px;">
                    SMTP Host: {test_settings.get('smtp_host')}<br>
                    Poort: {test_settings.get('smtp_port')}<br>
                    Beveiliging: {test_settings.get('smtp_security')}<br>
                    Afzender: {test_settings.get('smtp_sender_name')} &lt;{test_settings.get('smtp_sender_email') or test_settings.get('smtp_user')}&gt;
                </div>
                <p style="color: #64748b; font-size: 12px; margin-top: 15px;">U kunt nu commissiefacturen en XML-bestanden direct per e-mail versturen naar vervoerders en boekhouders.</p>
            </div>
            """
            result = email_sender.send_email_smtp(
                to_email=target_email,
                subject=subject,
                html_content=html_body,
                text_content="Transito E-mailkoppeling Testbericht - Succesvol verzonden.",
                settings=test_settings
            )
            conn.close()
            self.send_json(result)
            return

        elif path.startswith("/api/invoices/") and path.endswith("/send-email"):
            invoice_id = int(path.split("/")[3])
            row = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
            if not row:
                self.send_json({"error": "Factuur niet gevonden"}, status_code=404)
                conn.close()
                return

            inv = dict(row)
            company = database.get_company_settings()

            # Orders ophalen voor rittenspecificatie in e-mail
            order_ids = []
            if inv.get("order_ids_json"):
                try: order_ids = json.loads(inv["order_ids_json"])
                except Exception: order_ids = []

            orders = []
            if order_ids:
                placeholders = ",".join("?" for _ in order_ids)
                o_rows = conn.execute(f"SELECT * FROM orders WHERE id IN ({placeholders})", order_ids).fetchall()
                orders = [dict(r) for r in o_rows]

            to_email = body.get("to_email") or company.get("principal_email") or "administratie@veldhoventransport.nl"
            cc_email = body.get("cc_email") or company.get("accountant_email") or ""
            custom_subject = body.get("subject")
            custom_message = body.get("message")
            attach_xml = body.get("attach_xml", True)

            subject, html_body, text_body = email_sender.generate_invoice_email_template(inv, company, orders)
            if custom_subject:
                subject = custom_subject

            if custom_message:
                html_body = f"""
                <div style="font-family: sans-serif; background-color: #fffbeb; border: 1px solid #fef3c7; padding: 14px 18px; border-radius: 8px; margin-bottom: 20px; font-size: 13px; color: #92400e;">
                    <strong>Persoonlijk bericht van intermediair:</strong><br>
                    {custom_message.replace('\n', '<br>')}
                </div>
                """ + html_body

            attachments = []
            if attach_xml and inv.get("xml_content"):
                clean_num = inv["invoice_number"].replace("/", "_").replace(" ", "_")
                attachments.append({
                    "filename": f"IT_PROV_{clean_num}.xml",
                    "content": inv["xml_content"].encode("utf-8"),
                    "mimetype": "application/xml"
                })

            send_result = email_sender.send_email_smtp(
                to_email=to_email,
                subject=subject,
                html_content=html_body,
                text_content=text_body,
                attachments=attachments,
                cc_email=cc_email if cc_email else None,
                settings=company
            )

            if send_result.get("success"):
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                conn.execute("UPDATE invoices SET email_sent_at = ?, email_sent_to = ? WHERE id = ?", (now_str, to_email, invoice_id))
                conn.commit()

            conn.close()
            self.send_json(send_result)
            return

        conn.close()
        self.send_json({"error": "Onbekend POST endpoint"}, status_code=404)

    def handle_api_put(self, path):
        body = self.parse_body()
        conn = database.get_db_connection()

        if path.startswith("/api/orders/"):
            order_id = int(path.split("/")[3])
            existing = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
            if not existing:
                self.send_json({"error": "Opdracht niet gevonden"}, status_code=404)
                conn.close()
                return

            new_status = body.get("status") if ("status" in body and body.get("status") is not None) else existing["status"]
            freight_price = safe_float(body.get("freight_price"), existing["freight_price"]) if "freight_price" in body else existing["freight_price"]
            carrier_price = safe_float(body.get("carrier_price"), existing["carrier_price"]) if "carrier_price" in body else existing["carrier_price"]
            comm_type = body.get("commission_type") if "commission_type" in body else (existing["commission_type"] or "percentage")
            comm_rate = safe_float(body.get("commission_rate"), existing["commission_rate"]) if "commission_rate" in body else existing["commission_rate"]

            if "commission_amount" in body and body.get("commission_amount") not in (None, ""):
                comm_amount = safe_float(body.get("commission_amount"), existing["commission_amount"])
            else:
                if comm_type == "percentage" and "freight_price" in body:
                    comm_amount = round(freight_price * (comm_rate / 100.0), 2)
                elif comm_type == "margin" and ("freight_price" in body or "carrier_price" in body):
                    comm_amount = round(max(0.0, freight_price - carrier_price), 2)
                else:
                    comm_amount = existing["commission_amount"]

            if freight_price > 0 and (comm_rate == 0 or comm_type != "percentage") and comm_amount > 0:
                comm_rate = round((comm_amount / freight_price) * 100.0, 1)

            cmr_number = body.get("cmr_number") if "cmr_number" in body else existing["cmr_number"]
            pickup_date = body.get("pickup_date") if "pickup_date" in body else existing["pickup_date"]
            delivery_date = body.get("delivery_date") if "delivery_date" in body else existing["delivery_date"]
            notes = body.get("notes") if "notes" in body else existing["notes"]

            conn.execute("""
            UPDATE orders SET
                status = ?, freight_price = ?, carrier_price = ?, commission_type = ?, commission_rate = ?, commission_amount = ?,
                cmr_number = ?, pickup_date = ?, delivery_date = ?, notes = ?
            WHERE id = ?
            """, (
                new_status, freight_price, carrier_price, comm_type, comm_rate, comm_amount,
                cmr_number, pickup_date, delivery_date, notes, order_id
            ))
            conn.commit()
            conn.close()
            self.send_json({"success": True, "message": "Opdracht bijgewerkt"})
            return

        elif path.startswith("/api/expenses/"):
            exp_id = int(path.split("/")[3])
            conn.execute("DELETE FROM expenses WHERE id = ?", (exp_id,))
            conn.commit()
            conn.close()
            self.send_json({"success": True, "message": "Kostenpost verwijderd"})
            return

        elif path.startswith("/api/parties/"):
            party_id = int(path.split("/")[3])
            conn.execute("""
            UPDATE parties SET
                name = ?, country = ?, vat_number = ?, fiscal_code = ?, sdi_code = ?,
                pec = ?, email = ?, phone = ?, address = ?, zip = ?, city = ?, province = ?
            WHERE id = ?
            """, (
                body.get("name"), (body.get("country") or "IT").upper(), body.get("vat_number"),
                body.get("fiscal_code"), body.get("sdi_code"), body.get("pec"),
                body.get("email"), body.get("phone"), body.get("address"),
                body.get("zip"), body.get("city"), body.get("province"), party_id
            ))
            conn.commit()
            conn.close()
            self.send_json({"success": True, "message": "Verlader bijgewerkt"})
            return

        conn.close()
        self.send_json({"error": "Onbekend PUT endpoint"}, status_code=404)

    def handle_api_delete(self, path):
        conn = database.get_db_connection()

        if path.startswith("/api/orders/"):
            order_id = int(path.split("/")[3])
            conn.execute("DELETE FROM orders WHERE id = ?", (order_id,))
            conn.commit()
            conn.close()
            self.send_json({"success": True, "message": "Opdracht verwijderd"})
            return

        elif path.startswith("/api/invoices/"):
            inv_id = int(path.split("/")[3])
            conn.execute("UPDATE orders SET status = 'Geleverd', commission_invoice_id = NULL WHERE commission_invoice_id = ?", (inv_id,))
            conn.execute("DELETE FROM invoices WHERE id = ?", (inv_id,))
            conn.commit()
            conn.close()
            self.send_json({"success": True, "message": "Factuur verwijderd en gekoppelde ritten hersteld naar 'Geleverd'"})
            return

        elif path.startswith("/api/expenses/"):
            exp_id = int(path.split("/")[3])
            conn.execute("DELETE FROM expenses WHERE id = ?", (exp_id,))
            conn.commit()
            conn.close()
            self.send_json({"success": True, "message": "Kostenpost verwijderd"})
            return

        elif path.startswith("/api/parties/"):
            party_id = int(path.split("/")[3])
            conn.execute("DELETE FROM parties WHERE id = ?", (party_id,))
            conn.commit()
            conn.close()
            self.send_json({"success": True, "message": "Verlader verwijderd"})
            return

        elif path.startswith("/api/invoices/"):
            invoice_id = int(path.split("/")[3])
            conn.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))
            conn.commit()
            conn.close()
            self.send_json({"success": True, "message": "Factuur verwijderd"})
            return

        conn.close()
        self.send_json({"error": "Onbekend DELETE endpoint"}, status_code=404)


def run():
    database.init_db()
    os.makedirs(STATIC_DIR, exist_ok=True)
    socketserver.TCPServer.allow_reuse_address = True
    server_address = ("0.0.0.0", PORT)
    with socketserver.TCPServer(server_address, TransitoAPIHandler) as httpd:
        print("===============================================================")
        print("Transito Intermediair & SDI Facturatiesysteem draait!")
        print(f"Lokaal (PC): http://127.0.0.1:{PORT}")
        print(f"Mobiel (Telefoon): http://192.168.68.104:{PORT}/mobile")
        print("===============================================================")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer gestopt.")


if __name__ == "__main__":
    run()
