#!/usr/bin/env python3
"""
NSE Admin Review Server
Run: python review_server.py
Serves at http://localhost:8090

Endpoints:
  POST /api/auth           -> verify admin password
  GET  /api/records        -> returns financials with review status merged
  POST /api/review         -> update review status + comments for a record
  GET  *                   -> serve static files from frontend/

Auth: Set ADMIN_PASSWORD env var (default: "nse-admin-2024" for dev).
"""
import json
import hashlib
import os
import secrets
from http.server import HTTPServer, SimpleHTTPRequestHandler
from datetime import datetime, timezone

REPO_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
FRONTEND_DIR = os.path.join(REPO_ROOT, 'frontend')
FINANCIALS_PATH = os.path.join(REPO_ROOT, 'data', 'nse', 'financials_complete.json')
REVIEW_STATE_PATH = os.path.join(REPO_ROOT, 'data', 'nse', 'review_state.json')

ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'Ntigz')

# Simple token store (in-memory, resets on restart)
valid_tokens = set()


def generate_token():
    token = secrets.token_hex(32)
    valid_tokens.add(token)
    return token


def verify_token(token):
    return token in valid_tokens


def load_financials():
    try:
        with open(FINANCIALS_PATH, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def load_review_state():
    try:
        with open(REVIEW_STATE_PATH, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save_review_state(data):
    os.makedirs(os.path.dirname(REVIEW_STATE_PATH), exist_ok=True)
    with open(REVIEW_STATE_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def make_record_key(record):
    """Create a unique key for a financial record."""
    ticker = record.get('ticker', 'UNK')
    year = record.get('year') or 'none'
    period_type = record.get('period_type') or 'unknown'
    period_end = record.get('period_end_date') or ''
    return f"{ticker}|{year}|{period_type}|{period_end}"


def detect_issues(record):
    """Flag records with potential data quality issues."""
    issues = []

    # Missing critical fields
    critical = ['ticker', 'year', 'period_end_date', 'period_type']
    for field in critical:
        if not record.get(field):
            issues.append(f"Missing {field}")

    # Company name looks like parsing artifact
    company = record.get('company', '')
    if company == company.upper() and len(company) > 30:
        issues.append("Company name may be a parsing artifact")
    if 'GROUP COMPANY GROUP COMPANY' in company:
        issues.append("Duplicate company name pattern")

    # Check for suspiciously large or negative values
    numeric_fields = [
        'revenue', 'profit_after_tax', 'total_assets', 'total_equity',
        'net_interest_income', 'customer_deposits', 'loans_and_advances'
    ]
    for field in numeric_fields:
        val = record.get(field)
        if val is not None:
            if val < 0 and field not in ('profit_after_tax', 'operating_cash_flow'):
                issues.append(f"Negative {field}: {val}")

    # EPS sanity
    eps = record.get('basic_eps')
    if eps is not None and abs(eps) > 500:
        issues.append(f"Unusually high EPS: {eps}")

    # All financial fields null
    financial_fields = ['revenue', 'profit_after_tax', 'basic_eps', 'total_assets',
                        'net_interest_income', 'customer_deposits']
    all_null = all(record.get(f) is None for f in financial_fields)
    if all_null:
        issues.append("All key financial fields are null")

    return issues


class ReviewHandler(SimpleHTTPRequestHandler):

    def translate_path(self, path):
        """Serve files from the frontend directory."""
        if path.startswith('/api/'):
            return path
        # Strip query params
        path = path.split('?')[0]
        return os.path.join(FRONTEND_DIR, path.lstrip('/'))

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors_headers()
        self.end_headers()

    def do_GET(self):
        path = self.path.split('?')[0]

        if path == '/api/records':
            self._require_auth_and(self._handle_get_records)
        elif path.startswith('/api/'):
            self._send_json(404, {'error': 'Not found'})
        else:
            super().do_GET()

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length)) if length > 0 else {}
        except Exception as e:
            self._send_json(400, {'error': f'Bad request: {e}'})
            return

        path = self.path.split('?')[0]

        if path == '/api/auth':
            self._handle_auth(body)
        elif path == '/api/review':
            self._require_auth_and(lambda: self._handle_review(body))
        else:
            self._send_json(404, {'error': 'Not found'})

    def _handle_auth(self, body):
        password = body.get('password', '')
        if password == ADMIN_PASSWORD:
            token = generate_token()
            self._send_json(200, {'ok': True, 'token': token})
        else:
            self._send_json(401, {'error': 'Invalid password'})

    def _require_auth_and(self, handler):
        auth = self.headers.get('Authorization', '')
        token = auth.replace('Bearer ', '') if auth.startswith('Bearer ') else ''
        if not verify_token(token):
            self._send_json(401, {'error': 'Unauthorized'})
            return
        handler()

    def _handle_get_records(self):
        financials = load_financials()
        review_state = load_review_state()

        records = []
        for rec in financials:
            key = make_record_key(rec)
            review = review_state.get(key, {})
            issues = detect_issues(rec)

            records.append({
                'key': key,
                'ticker': rec.get('ticker', ''),
                'company': rec.get('company', ''),
                'sector': rec.get('sector', ''),
                'year': rec.get('year'),
                'period': rec.get('period', ''),
                'period_type': rec.get('period_type', ''),
                'period_end_date': rec.get('period_end_date', ''),
                'source_file': rec.get('source_file', ''),
                'url': rec.get('url', ''),
                'data': {
                    'revenue': rec.get('revenue'),
                    'profit_before_tax': rec.get('profit_before_tax'),
                    'profit_after_tax': rec.get('profit_after_tax'),
                    'basic_eps': rec.get('basic_eps'),
                    'dividend_per_share': rec.get('dividend_per_share'),
                    'net_interest_income': rec.get('net_interest_income'),
                    'total_assets': rec.get('total_assets'),
                    'total_equity': rec.get('total_equity'),
                    'customer_deposits': rec.get('customer_deposits'),
                    'loans_and_advances': rec.get('loans_and_advances'),
                    'operating_cash_flow': rec.get('operating_cash_flow'),
                    'capex': rec.get('capex'),
                    'ebitda': rec.get('ebitda'),
                    'mpesa_revenue': rec.get('mpesa_revenue'),
                },
                'issues': issues,
                'review_status': review.get('status', 'unreviewed'),
                'review_comment': review.get('comment', ''),
                'reviewed_by': review.get('reviewed_by', ''),
                'reviewed_at': review.get('reviewed_at', ''),
            })

        self._send_json(200, {'records': records, 'total': len(records)})

    def _handle_review(self, body):
        key = body.get('key', '')
        status = body.get('status', '')
        comment = body.get('comment', '')

        if not key:
            self._send_json(400, {'error': 'Missing record key'})
            return

        valid_statuses = ('unreviewed', 'in_progress', 'approved', 'needs_fix')
        if status not in valid_statuses:
            self._send_json(400, {'error': f'Invalid status. Must be one of: {valid_statuses}'})
            return

        review_state = load_review_state()

        if status == 'unreviewed':
            # Remove review entry to reset
            review_state.pop(key, None)
        else:
            review_state[key] = {
                'status': status,
                'comment': comment,
                'reviewed_by': 'admin',
                'reviewed_at': datetime.now(timezone.utc).isoformat(),
            }

        save_review_state(review_state)
        print(f"  Review: {key} -> {status}")

        self._send_json(200, {'ok': True, 'key': key, 'status': status})

    def _send_json(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self._cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')

    def log_message(self, fmt, *args):
        print(f"[{self.log_date_time_string()}] {fmt % args}")


if __name__ == '__main__':
    os.chdir(FRONTEND_DIR)
    port = int(os.environ.get('REVIEW_PORT', 8090))
    server = HTTPServer(('localhost', port), ReviewHandler)
    print(f"NSE Review Server running at http://localhost:{port}")
    print(f"  Admin Panel:  http://localhost:{port}/admin_review.html")
    print(f"  Public Site:  http://localhost:{port}/index.html")
    print(f"  Password:     (set ADMIN_PASSWORD env var, default for dev)")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
