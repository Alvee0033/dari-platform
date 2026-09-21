#!/usr/bin/env python3
"""
SPA Server for DARI Document Verification & Admin Operations Center
Handles:
  - /admin and /en/admin
  - /en?app/verify-document
  - /en/app/verify-document
  - /app/verify-document
  - Static assets and JSON APIs (/api/documents, /api/audit)
"""
import http.server
import json
import os
import sys
import threading
import time
import urllib.parse

import db

PORT = 8080
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

_contract_locks = {}
_locks_mutex = threading.Lock()

def get_contract_lock(contract_num):
    with _locks_mutex:
        c_str = str(contract_num)
        if c_str not in _contract_locks:
            _contract_locks[c_str] = threading.Lock()
        return _contract_locks[c_str]

def generate_contract_for_number(contract_num, custom_data=None, force=False):
    """Loads base template, merges with registry document data or custom_data, and generates contract bundle."""
    c_str = str(contract_num)
    lock = get_contract_lock(c_str)
    with lock:
        doc_gen_dir = os.path.join(DIRECTORY, "doc_gen")
        output_dir = os.path.join(doc_gen_dir, "output", c_str)
        complete_marker = os.path.join(output_dir, ".complete")

        # If already fully generated and not forced, return cached metadata
        if not force and not custom_data and os.path.exists(complete_marker):
            all_pages_exist = all(os.path.exists(os.path.join(output_dir, f"{i}.png")) for i in range(1, 9))
            pdf_path = os.path.join(output_dir, f"{c_str}.pdf")
            if all_pages_exist and os.path.exists(pdf_path):
                return {
                    "contractNumber": c_str,
                    "pageCount": 8,
                    "pdfPath": pdf_path,
                    "outputDir": output_dir,
                    "pages": [f"/api/contracts/{c_str}/{i}.png" for i in range(1, 9)],
                    "cached": True
                }

        from doc_gen.generate_contract import generate_contract_bundle

        sample_json = os.path.join(doc_gen_dir, "sample_contract.json")
        contract_data = {}
        if os.path.exists(sample_json):
            with open(sample_json, "r", encoding="utf-8") as f:
                contract_data = json.load(f)

        # Check database / documents.json
        docs_file = os.path.join(DIRECTORY, "documents.json")
        matched_doc = None
        try:
            docs = db.get_documents_db(docs_file)
            for d in docs:
                if str(d.get("documentNumber")) == str(contract_num) or str(d.get("id")) == str(contract_num):
                    matched_doc = d
                    break
        except Exception:
            pass

        # If custom_data passed, merge
        if custom_data and isinstance(custom_data, dict):
            if "contract" in custom_data:
                contract_data.setdefault("contract", {}).update(custom_data["contract"])
            if "tenant" in custom_data:
                contract_data.setdefault("tenant", {}).update(custom_data["tenant"])
            if "lessor" in custom_data:
                contract_data.setdefault("lessor", {}).update(custom_data["lessor"])
            if "property" in custom_data:
                contract_data.setdefault("property", {}).update(custom_data["property"])
            if "units" in custom_data:
                contract_data["units"] = custom_data["units"]
            if "occupants" in custom_data:
                contract_data["occupants"] = custom_data["occupants"]

        if matched_doc:
            contract = contract_data.setdefault("contract", {})
            contract["contractNumber"] = matched_doc.get("documentNumber", str(contract_num))
            if matched_doc.get("startDate"):
                contract["startDate"] = matched_doc["startDate"]
            if matched_doc.get("issueDate"):
                contract["issueDate"] = str(matched_doc["issueDate"])
            elif matched_doc.get("startDate"):
                contract["issueDate"] = str(matched_doc["startDate"])
            if matched_doc.get("approvalDateTime"):
                contract["approvalDateTime"] = str(matched_doc["approvalDateTime"])
            if matched_doc.get("endDate"):
                contract["endDate"] = matched_doc["endDate"]
            if matched_doc.get("status"):
                contract["status"] = matched_doc["status"]
            if matched_doc.get("annualRent"):
                contract["annualRent"] = str(matched_doc["annualRent"])
            if matched_doc.get("contractValue"):
                contract["contractValue"] = str(matched_doc["contractValue"])
            if matched_doc.get("securityDeposit"):
                contract["securityDeposit"] = str(matched_doc["securityDeposit"])
            if matched_doc.get("paymentMethodEn"):
                contract["paymentMethodEn"] = str(matched_doc["paymentMethodEn"])
            if matched_doc.get("paymentMethodAr"):
                contract["paymentMethodAr"] = str(matched_doc["paymentMethodAr"])
            if matched_doc.get("numberOfPayments"):
                contract["numberOfPayments"] = str(matched_doc["numberOfPayments"])
            if matched_doc.get("contractTermEn"):
                contract["contractTermEn"] = str(matched_doc["contractTermEn"])
            if matched_doc.get("contractTermAr"):
                contract["contractTermAr"] = str(matched_doc["contractTermAr"])
            if matched_doc.get("waterBillEn"):
                contract["waterElectricityBillEn"] = str(matched_doc["waterBillEn"])
            if matched_doc.get("petsAllowedEn"):
                contract["petsAllowedEn"] = str(matched_doc["petsAllowedEn"])

            # Tenant Details
            tenant = contract_data.setdefault("tenant", {})
            if matched_doc.get("partyName") or matched_doc.get("tenantNameEn"):
                tenant["fullNameEn"] = matched_doc.get("tenantNameEn") or matched_doc.get("partyName")
            if matched_doc.get("tenantNameAr"):
                tenant["fullNameAr"] = matched_doc["tenantNameAr"]
            if matched_doc.get("tenantEmiratesId"):
                tenant["emiratesId"] = str(matched_doc["tenantEmiratesId"])
            if matched_doc.get("tenantNationalityEn"):
                tenant["nationalityEn"] = matched_doc["tenantNationalityEn"]
            if matched_doc.get("tenantNationalityAr"):
                tenant["nationalityAr"] = matched_doc["tenantNationalityAr"]
            if matched_doc.get("tenantMobile"):
                tenant["mobileNo"] = str(matched_doc["tenantMobile"])
            if matched_doc.get("tenantEmail"):
                tenant["email"] = matched_doc["tenantEmail"]

            # Lessor Details
            lessor = contract_data.setdefault("lessor", {})
            if matched_doc.get("lessorCompanyEn"):
                lessor["companyNameEn"] = matched_doc["lessorCompanyEn"]
            if matched_doc.get("lessorCompanyAr"):
                lessor["companyNameAr"] = matched_doc["lessorCompanyAr"]
            if matched_doc.get("lessorLicenseNo"):
                lessor["licenseNo"] = str(matched_doc["lessorLicenseNo"])
            if matched_doc.get("lessorMobile"):
                lessor["mobileNo"] = str(matched_doc["lessorMobile"])
            if matched_doc.get("lessorEmail"):
                lessor["email"] = matched_doc["lessorEmail"]

            contact = lessor.setdefault("contactPerson", {})
            if matched_doc.get("lessorContactEn"):
                contact["fullNameEn"] = matched_doc["lessorContactEn"]
            if matched_doc.get("lessorContactAr"):
                contact["fullNameAr"] = matched_doc["lessorContactAr"]
            if matched_doc.get("contactMobile") or matched_doc.get("lessorContactMobile") or matched_doc.get("lessorMobile"):
                contact["mobileNo"] = str(matched_doc.get("contactMobile") or matched_doc.get("lessorContactMobile") or matched_doc.get("lessorMobile"))
            if matched_doc.get("contactEmail") or matched_doc.get("lessorContactEmail") or matched_doc.get("lessorEmail"):
                contact["email"] = matched_doc.get("contactEmail") or matched_doc.get("lessorContactEmail") or matched_doc.get("lessorEmail")

            # Units Details
            units = contract_data.setdefault("units", [{}])
            if units and isinstance(units, list):
                u0 = units[0]
                if matched_doc.get("premiseNo"):
                    u0["premiseNo"] = str(matched_doc["premiseNo"])
                if matched_doc.get("unitOrPlot") or matched_doc.get("unitNo"):
                    u0["unitNo"] = matched_doc.get("unitNo") or matched_doc.get("unitOrPlot")
                if matched_doc.get("unitRegNo"):
                    u0["unitRegNo"] = str(matched_doc["unitRegNo"])
                if matched_doc.get("noOfRooms"):
                    u0["noOfRooms"] = str(matched_doc["noOfRooms"])
                if matched_doc.get("area"):
                    u0["area"] = str(matched_doc["area"])
                if matched_doc.get("unitUsageEn"):
                    u0["unitUsageEn"] = matched_doc["unitUsageEn"]
                if matched_doc.get("unitUsageAr"):
                    u0["unitUsageAr"] = matched_doc["unitUsageAr"]
                if matched_doc.get("unitTypeEn"):
                    u0["unitTypeEn"] = matched_doc["unitTypeEn"]
                if matched_doc.get("unitTypeAr"):
                    u0["unitTypeAr"] = matched_doc["unitTypeAr"]

            # Property Details
            prop = contract_data.setdefault("property", {})
            if matched_doc.get("propertyNameEn"):
                prop["propertyNameEn"] = matched_doc["propertyNameEn"]
            if matched_doc.get("plotNo"):
                prop["plotNo"] = matched_doc["plotNo"]
            if matched_doc.get("sectorEn"):
                prop["sectorEn"] = matched_doc["sectorEn"]

            # Occupants Details
            occupants = contract_data.setdefault("occupants", [{}])
            if occupants and isinstance(occupants, list):
                occ0 = occupants[0]
                occ0["fullName"] = matched_doc.get("occupantName") or tenant.get("fullNameEn", "")
                occ0["emiratesId"] = str(matched_doc.get("occupantEmiratesId") or tenant.get("emiratesId", ""))
                occ0["fullNameAr"] = matched_doc.get("occupantNameAr") or matched_doc.get("tenantNameAr", "")
        else:
            contract_data.setdefault("contract", {})["contractNumber"] = str(contract_num)

        res = generate_contract_bundle(contract_data, output_dir=output_dir)
        try:
            with open(complete_marker, "w", encoding="utf-8") as f:
                f.write(str(time.time()))
        except Exception:
            pass
        return res

class DariSPARequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        parsed = urllib.parse.urlparse(self.path)
        clean = parsed.path.lower()
        # Add high-performance edge & browser caching for static assets
        if clean.startswith('/assets/') or clean.endswith(('.css', '.js', '.svg', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.woff2', '.ttf', '.woff', '.ico')):
            if not clean.endswith(('documents.json', 'audit_log.json', 'bottom_nav_data.json')):
                self.send_header('Cache-Control', 'public, max-age=604800, stale-while-revalidate=86400')
        elif clean.startswith('/api/contracts/') and clean.endswith(('.png', '.pdf')):
            self.send_header('Cache-Control', 'public, max-age=3600, stale-while-revalidate=86400')
        super().end_headers()

    def normalize_path(self):
        parsed = urllib.parse.urlparse(self.path)
        clean_path = parsed.path.rstrip('/')

        # 1. API Endpoints (Always handled dynamically via database)
        if clean_path in ['/api/documents', '/documents.json'] or clean_path.endswith('/documents.json'):
            return '/api/documents'
        if clean_path in ['/api/audit', '/audit_log.json'] or clean_path.endswith('/audit_log.json'):
            return '/api/audit'
        if clean_path in ['/api/generate-contract', '/api/auth/login', '/api/auth/logout', '/api/auth/me']:
            return clean_path
        if clean_path.startswith('/api/contracts'):
            return clean_path

        # 2. Login Route
        if clean_path in ['/login', '/en/login', '/auth/login']:
            self.path = '/login.html'
            return None

        # 3. Admin Dashboard Routes (Enforce authentication)
        if clean_path in ['/admin', '/en/admin']:
            session_token = self.get_session_token()
            user = db.validate_session(session_token)
            if not user:
                # Redirect to separate login page
                self.send_response(302)
                self.send_header('Location', '/login')
                self.end_headers()
                return 'REDIRECTED'
            self.path = '/admin.html'
            return None

        # 4. Static asset remapping (assets/ or root CSS/JS files)
        if '/assets/' in parsed.path:
            asset_rel = parsed.path[parsed.path.index('/assets/') + 1:]
            self.path = '/' + asset_rel
            if parsed.query:
                self.path += '?' + parsed.query
            return None

        for filename in ['style.css', 'script.js', 'admin.css', 'admin.js', 'login.html', 'bottom_nav_data.json', 'favicon.ico']:
            if parsed.path.endswith('/' + filename):
                self.path = '/' + filename
                if parsed.query:
                    self.path += '?' + parsed.query
                return None

        # 5. SPA Document Verification public routes
        spa_routes = {
            '',
            '/',
            '/index.html',
            '/en',
            '/en/',
            '/ar',
            '/ar/',
            '/app',
            '/app/',
            '/en/app',
            '/en/app/',
            '/app/verify-document',
            '/app/verify-document/',
            '/en/app/verify-document',
            '/en/app/verify-document/',
            '/ar/app/verify-document',
            '/ar/app/verify-document/',
            '/app/verify-tenant-contract',
            '/app/verify-tenant-contract/',
            '/en/app/verify-tenant-contract',
            '/en/app/verify-tenant-contract/',
            '/ar/app/verify-tenant-contract',
            '/ar/app/verify-tenant-contract/',
        }

        if clean_path in spa_routes or clean_path.startswith('/en/app') or clean_path.startswith('/ar/app') or clean_path.startswith('/app'):
            self.path = '/index.html'
            if parsed.query:
                self.path += '?' + parsed.query
            return None

        return None

    def get_session_token(self):
        cookie_header = self.headers.get('Cookie', '')
        if 'adrec_session=' in cookie_header:
            parts = cookie_header.split(';')
            for part in parts:
                if 'adrec_session=' in part:
                    return part.strip().split('adrec_session=')[1].split(';')[0].strip()
        auth_header = self.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            return auth_header[7:].strip()
        return None

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        api_target = self.normalize_path()
        if api_target == 'REDIRECTED':
            return
        if api_target == '/api/auth/me':
            token = self.get_session_token()
            user = db.validate_session(token)
            if user:
                self.send_json_data({"status": "success", "authenticated": True, "user": user})
            else:
                self.send_response(401)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b'{"status": "error", "authenticated": false, "message": "Not authenticated"}')
            return
        elif api_target == '/api/documents':
            docs = db.get_documents_db(os.path.join(DIRECTORY, 'documents.json'))
            self.send_json_data(docs)
            return
        elif api_target == '/api/audit':
            audit = db.get_audit_db(os.path.join(DIRECTORY, 'audit_log.json'))
            self.send_json_data(audit)
            return
        elif api_target and api_target.startswith('/api/contracts'):
            self.handle_get_contract(api_target)
            return

        return super().do_GET()

    def handle_get_contract(self, api_path):
        """Streams generated contract PDFs and preview PNGs, auto-generating on-the-fly if missing."""
        sub = api_path[len('/api/contracts/'):].strip('/')
        if not sub:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status":"error","message":"Missing contract reference"}')
            return

        # Check for status query: /api/contracts/202401452705/status
        if sub.endswith('/status'):
            contract_num = sub.split('/')[0]
            output_dir = os.path.join(DIRECTORY, "doc_gen", "output", contract_num)
            complete_marker = os.path.join(output_dir, ".complete")
            is_ready = os.path.exists(complete_marker) and all(
                os.path.exists(os.path.join(output_dir, f"{i}.png")) for i in range(1, 9)
            )
            resp = {
                "status": "success",
                "contractNumber": contract_num,
                "ready": is_ready,
                "pageCount": 8
            }
            out_bytes = json.dumps(resp).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(out_bytes)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.end_headers()
            self.wfile.write(out_bytes)
            return

        # Check for /api/contracts/202401452705.pdf vs /api/contracts/202401452705/1.png
        if sub.endswith('.pdf') and '/' not in sub:
            contract_num = sub[:-4]
            filename = f"{contract_num}.pdf"
            target_path = os.path.join(DIRECTORY, "doc_gen", "output", contract_num, filename)
        else:
            parts = sub.split('/')
            contract_num = parts[0]
            if len(parts) > 1:
                filename = parts[1]
                if filename.startswith('page_') and filename.endswith('.png'):
                    filename = filename.replace('page_', '')
            else:
                filename = f"{contract_num}.pdf"
            target_path = os.path.join(DIRECTORY, "doc_gen", "output", contract_num, filename)

        lock = get_contract_lock(contract_num)
        with lock:
            if not os.path.exists(target_path):
                try:
                    generate_contract_for_number(contract_num)
                except Exception as e:
                    self.send_response(500)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "error", "message": f"Generation failed: {str(e)}"}).encode('utf-8'))
                    return

            if not os.path.exists(target_path):
                self.send_response(404)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": f"Contract file not found: {sub}"}).encode('utf-8'))
                return

            if target_path.endswith('.pdf'):
                content_type = 'application/pdf'
                disposition = f'inline; filename="{os.path.basename(target_path)}"'
            elif target_path.endswith('.png'):
                content_type = 'image/png'
                disposition = 'inline'
            elif target_path.endswith('.json'):
                content_type = 'application/json'
                disposition = 'inline'
            else:
                content_type = 'application/octet-stream'
                disposition = f'attachment; filename="{os.path.basename(target_path)}"'

            try:
                with open(target_path, 'rb') as f:
                    data = f.read()
                self.send_response(200)
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Disposition', disposition)
                self.send_header('Content-Length', str(len(data)))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.send_header('Pragma', 'no-cache')
                self.send_header('Expires', '0')
                self.end_headers()
                self.wfile.write(data)
            except Exception as e:
                self.send_response(500)
                self.end_headers()

    def do_HEAD(self):
        api_target = self.normalize_path()
        if api_target in ['/api/documents', '/api/audit']:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            return
        elif api_target and api_target.startswith('/api/contracts'):
            self.do_GET()
            return

        return super().do_HEAD()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        clean_path = parsed.path.rstrip('/')

        if clean_path == '/api/auth/login':
            content_len = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_len) if content_len > 0 else b'{}'
            try:
                data = json.loads(post_body.decode('utf-8'))
                ident = data.get('identifier') or data.get('email') or data.get('username') or ''
                pwd = data.get('password', '')
                user = db.authenticate_user(ident, pwd)
                if user:
                    token = db.create_session(user['id'])
                    cookie_val = f"adrec_session={token}; Path=/; Max-Age=604800; SameSite=Lax; HttpOnly"
                    resp = json.dumps({"status": "success", "token": token, "user": user}).encode('utf-8')
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(len(resp)))
                    self.send_header('Set-Cookie', cookie_val)
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(resp)
                    return
                else:
                    self.send_response(401)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(b'{"status": "error", "message": "Invalid officer credentials or password"}')
                    return
            except Exception as e:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))
                return

        if clean_path == '/api/auth/logout':
            token = self.get_session_token()
            if token:
                db.destroy_session(token)
            cookie_val = "adrec_session=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT; HttpOnly"
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Set-Cookie', cookie_val)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(b'{"status": "success"}')
            return

        if clean_path in ['/api/documents', '/documents.json', '/api/audit', '/audit_log.json']:
            content_len = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_len)
            try:
                data = json.loads(post_body.decode('utf-8'))
                if clean_path in ['/api/documents', '/documents.json']:
                    db.save_documents_db(data, os.path.join(DIRECTORY, 'documents.json'))
                else:
                    db.save_audit_db(data, os.path.join(DIRECTORY, 'audit_log.json'))

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.end_headers()
                self.wfile.write(b'{"status":"success"}')
                return
            except Exception as e:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.end_headers()
                self.wfile.write(json.dumps({"status":"error", "message": str(e)}).encode('utf-8'))
                return

        if clean_path == '/api/generate-contract':
            content_len = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_len) if content_len > 0 else b'{}'
            try:
                body = json.loads(post_body.decode('utf-8')) if post_body else {}
                contract_num = body.get('documentNumber') or body.get('contractNumber') or '202401452705'
                force = body.get('force', False)
                res = generate_contract_for_number(contract_num, custom_data=body, force=force)
                c_num = res['contractNumber']
                p_count = res.get('pageCount', 8)
                pages = [f"/api/contracts/{c_num}/{i}.png" for i in range(1, p_count + 1)]
                resp = {
                    "status": "success",
                    "ready": True,
                    "contractNumber": c_num,
                    "pdfUrl": f"/api/contracts/{c_num}/{c_num}.pdf",
                    "downloadUrl": f"/api/contracts/{c_num}.pdf",
                    "pageCount": p_count,
                    "pages": pages
                }
                out_bytes = json.dumps(resp).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(out_bytes)))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.end_headers()
                self.wfile.write(out_bytes)
                return
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))
                return

        self.send_response(404)
        self.end_headers()

    def send_json_data(self, data):
        content = json.dumps(data, indent=2).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        self.end_headers()
        self.wfile.write(content)

if __name__ == '__main__':
    db.init_db()
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    server_address = ('', port)
    http.server.ThreadingHTTPServer.allow_reuse_address = True
    httpd = http.server.ThreadingHTTPServer(server_address, DariSPARequestHandler)
    print(f"Serving DARI SPA & Admin with ThreadingHTTPServer on port {port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
