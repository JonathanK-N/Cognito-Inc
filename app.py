from flask import Flask, Response, render_template, request, jsonify, session, redirect, url_for, g
import os
from datetime import datetime
import sqlite3
import re
import json
import time
import urllib.parse
from functools import wraps
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from itsdangerous import URLSafeSerializer, BadSignature

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-change-this-secret')
email_token_serializer = URLSafeSerializer(app.secret_key, salt='go-email')

# --- Configuration ---
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID   = os.environ.get('TELEGRAM_CHAT_ID')
RESEND_API_KEY     = os.environ.get('RESEND_API_KEY')
RESEND_FROM_EMAIL  = os.environ.get('RESEND_FROM_EMAIL', 'Cognito Inc. <contact@cognito-inc.ca>')
ADMIN_PASSWORD     = os.environ.get('ADMIN_PASSWORD', '')
NVIDIA_API_KEY     = os.environ.get('NVIDIA_API_KEY')
NVIDIA_MODEL       = os.environ.get('NVIDIA_MODEL', 'meta/llama-3.1-8b-instruct')
DATABASE_PATH      = os.environ.get('DATABASE_PATH', 'cognito.db')
TARIF_URL          = os.environ.get('TARIF_URL', 'https://tarif.cognito-inc.ca')

# --- Coordonnées Cognito Inc. ---
SITE_EMAIL         = 'contact@cognito-inc.ca'
SITE_PHONE_DISPLAY = '+1 (819) 272-5034'
SITE_PHONE_TEL     = '+18192725034'

SERVICE_LABELS = {
    'innovation': 'Innovation technologique',
    'development': 'Développement sur mesure',
    'ai': 'Intelligence artificielle',
    'consulting': 'Conseil stratégique',
    'partnership': 'Partenariat'
}

COGNITO_SYSTEM = (
    "Tu es l'assistant IA de Cognito Inc., une startup technologique basée à Sherbrooke, Canada "
    "(Sherweb - Startup Campus). Cognito Inc. est spécialisée dans trois domaines : "
    "Innovation technologique, Développement logiciel sur mesure et Intelligence artificielle. "
    "Elle accompagne des entreprises de toutes tailles dans leur transformation numérique, "
    "des startups aux grandes entreprises, avec des solutions adaptées à chaque budget. "
    f"Contact : {SITE_EMAIL} | {SITE_PHONE_DISPLAY}. "
    "Ton ton est professionnel, chaleureux et orienté solutions. Réponds toujours en français."
)

# ==================== BASE DE DONNÉES ====================

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db_dir = os.path.dirname(DATABASE_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS projects (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            title      TEXT NOT NULL,
            slug       TEXT UNIQUE NOT NULL,
            category   TEXT,
            short_desc TEXT,
            long_desc  TEXT,
            tech_tags  TEXT,
            status     TEXT DEFAULT 'completed',
            link       TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS social_links (
            key TEXT PRIMARY KEY,
            url TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS contact_messages (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT,
            email      TEXT,
            phone      TEXT,
            company    TEXT,
            service    TEXT,
            message    TEXT,
            ai_draft   TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS testimonials (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT NOT NULL,
            role         TEXT,
            company      TEXT,
            rating       INTEGER DEFAULT 5,
            project_type TEXT,
            comment      TEXT NOT NULL,
            status       TEXT DEFAULT 'pending',
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS page_views (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            path       TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')

    existing_columns = {row[1] for row in conn.execute('PRAGMA table_info(contact_messages)')}
    if 'phone' not in existing_columns:
        conn.execute('ALTER TABLE contact_messages ADD COLUMN phone TEXT')
    if 'email_sent_at' not in existing_columns:
        conn.execute('ALTER TABLE contact_messages ADD COLUMN email_sent_at TIMESTAMP')

    # Remove the sample records from the original starter site. They were never
    # verified customer work or authorized testimonials.
    conn.execute("DELETE FROM projects WHERE slug IN ('ia-predictive', 'mobile-app', 'saas-platform', 'chatbot-ai', 'iot-system', 'blockchain', 'lms-platform')")
    conn.execute("DELETE FROM testimonials WHERE company IN ('TechStart', 'InnovCorp', 'DigitalPro', 'AnalyticsCorp', 'GlobalTech', 'IndustrialSmart')")

    conn.commit()
    conn.close()

init_db()

# ==================== SUIVI DES VISITES ====================

TRACKING_EXCLUDED_PREFIXES = ('/admin', '/static', '/go/')

@app.before_request
def track_visit():
    if request.method != 'GET' or request.path.startswith(TRACKING_EXCLUDED_PREFIXES):
        return
    try:
        db = get_db()
        db.execute('INSERT INTO page_views (path) VALUES (?)', (request.path,))
        db.commit()
    except Exception:
        pass

# ==================== CONTEXT PROCESSOR ====================

@app.context_processor
def inject_social_links():
    if request.path.startswith('/admin'):
        return {}
    try:
        db = get_db()
        rows = db.execute('SELECT key, url FROM social_links').fetchall()
        return {'social_links': {r['key']: r['url'] for r in rows}}
    except Exception:
        return {'social_links': {'linkedin': '#', 'twitter': '#', 'github': '#', 'youtube': '#'}}

@app.context_processor
def inject_current_year():
    return {'current_year': datetime.now().year}

# ==================== HELPERS ====================

def slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    return re.sub(r'-+', '-', text)

def whatsapp_link(phone, text=None):
    digits = re.sub(r'\D', '', phone or '')
    if not digits:
        return None
    url = f'https://wa.me/{digits}'
    if text:
        url += f'?text={urllib.parse.quote(text)}'
    return url

DRAFT_SIGNOFF = "Cordialement,\nL'équipe Cognito Inc."

def finalize_draft(draft):
    if not draft:
        return None
    draft = draft.strip()
    # Coupe tout ce qui suit une formule de politesse finale (et sa signature) que le
    # modèle aurait ajoutée malgré la consigne, pour garantir une signature cohérente
    # sur un email réellement envoyé au client.
    draft = re.split(
        r'\n\s*(?:Cordialement|Bien cordialement|Sincèrement|Bien à vous)\s*,?\s*(?:\n|$)',
        draft, maxsplit=1, flags=re.IGNORECASE
    )[0].strip()
    # Retire une éventuelle ligne de signature isolée restée en toute fin
    draft = re.sub(r"\n*(\[Votre nom\]|L'équipe Cognito Inc\.?|Cognito Inc\.?)\s*$", '', draft, flags=re.IGNORECASE).strip()
    return f"{draft}\n\n{DRAFT_SIGNOFF}"

def call_llm(prompt, system=None, max_tokens=1024):
    if not NVIDIA_API_KEY:
        return None
    try:
        r = requests.post(
            'https://integrate.api.nvidia.com/v1/chat/completions',
            headers={'Authorization': f'Bearer {NVIDIA_API_KEY}'},
            json={
                'model': NVIDIA_MODEL,
                'messages': [
                    {'role': 'system', 'content': system or COGNITO_SYSTEM},
                    {'role': 'user', 'content': prompt},
                ],
                'max_tokens': max_tokens,
                'temperature': 0.5,
            },
            timeout=30
        )
        r.raise_for_status()
        return r.json()['choices'][0]['message']['content'].strip()
    except Exception:
        return None

def get_db_context():
    try:
        db = get_db()

        projects = db.execute(
            "SELECT title, category, short_desc, tech_tags FROM projects "
            "WHERE status='completed' ORDER BY created_at DESC LIMIT 10"
        ).fetchall()

        testimonials = db.execute(
            "SELECT name, role, company, rating, comment FROM testimonials "
            "WHERE status='approved' ORDER BY created_at DESC LIMIT 5"
        ).fetchall()

        context = ""

        if projects:
            context += "\n\n=== PROJETS RÉALISÉS PAR COGNITO INC. ===\n"
            for p in projects:
                context += f"• {p['title']} ({p['category'] or 'Projet'})"
                if p['short_desc']:
                    context += f" : {p['short_desc']}"
                if p['tech_tags']:
                    context += f" [Technologies : {p['tech_tags']}]"
                context += "\n"

        if testimonials:
            context += "\n=== TÉMOIGNAGES CLIENTS VÉRIFIÉS ===\n"
            for t in testimonials:
                stars = "★" * t['rating']
                context += f"• {t['name']}"
                if t['role'] or t['company']:
                    parts = [x for x in [t['role'], t['company']] if x]
                    context += f" ({', '.join(parts)})"
                context += f" {stars} — \"{t['comment']}\"\n"

        if context:
            context = (
                "\n\nTu as accès aux données réelles de Cognito Inc. "
                "Utilise-les pour répondre précisément aux questions des visiteurs."
                + context
            )

        return context
    except Exception:
        return ""

_tarif_cache = {'text': '', 'fetched_at': 0}
TARIF_CACHE_TTL = 3600

def get_tarif_context():
    now = time.time()
    if _tarif_cache['text'] and now - _tarif_cache['fetched_at'] < TARIF_CACHE_TTL:
        return _tarif_cache['text']
    try:
        r = requests.get(TARIF_URL, timeout=8)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')
        for tag in soup(['script', 'style', 'nav', 'footer', 'svg']):
            tag.decompose()
        text = ' '.join(soup.stripped_strings)[:4000]
        if text:
            _tarif_cache['text'] = (
                "\n\n=== TARIFS COGNITO INC. (tarif.cognito-inc.ca) ===\n" + text
            )
            _tarif_cache['fetched_at'] = now
        return _tarif_cache['text']
    except Exception:
        return _tarif_cache['text']

def generate_ai_response(message_text):
    if NVIDIA_API_KEY:
        extra_context = get_db_context() + get_tarif_context()
        response = call_llm(
            f"Un visiteur du site Cognito Inc. écrit dans le chat : \"{message_text}\". "
            "Réponds de façon concise et professionnelle en moins de 100 mots. "
            "Si la question porte sur des projets, témoignages ou tarifs, utilise les données fournies dans le contexte.",
            system=COGNITO_SYSTEM + extra_context,
            max_tokens=250
        )
        if response:
            return response
    message_lower = message_text.lower()
    if 'bonjour' in message_lower or 'salut' in message_lower:
        return "Bonjour ! Comment puis-je vous aider aujourd'hui ?"
    elif 'service' in message_lower:
        return "Nous offrons des services en Innovation, Développement et IA. Lequel vous intéresse ?"
    elif 'prix' in message_lower or 'devis' in message_lower:
        return "Je peux vous aider avec un devis. Pouvez-vous me parler de votre projet ?"
    elif 'rdv' in message_lower or 'rendez-vous' in message_lower:
        return "Parfait ! Quelle date vous conviendrait pour un rendez-vous ?"
    else:
        return "Je comprends. Pouvez-vous me donner plus de détails sur votre besoin ?"

def send_telegram_message(chat_id, text, reply_markup=None):
    if not TELEGRAM_BOT_TOKEN or not chat_id:
        return False
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    payload = {'chat_id': chat_id, 'text': text}
    if reply_markup:
        payload['reply_markup'] = reply_markup
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.ok
    except requests.RequestException:
        return False

def send_confirmation_email(name, to_email):
    if not RESEND_API_KEY:
        return False
    html_body = (
        f"<p>Bonjour {name},</p>"
        "<p>Nous avons bien reçu votre message et nous vous répondrons dans les 24h ouvrées.</p>"
        "<p>Merci de votre confiance,<br>"
        "L'équipe Cognito Inc.<br>"
        f"{SITE_EMAIL} | {SITE_PHONE_DISPLAY}</p>"
    )
    try:
        r = requests.post(
            'https://api.resend.com/emails',
            headers={'Authorization': f'Bearer {RESEND_API_KEY}'},
            json={
                'from': RESEND_FROM_EMAIL,
                'to': [to_email],
                'subject': 'Confirmation de réception - Cognito Inc.',
                'html': html_body,
            },
            timeout=10
        )
        return r.ok
    except requests.RequestException:
        return False

def send_draft_email(to_email, draft_text):
    if not RESEND_API_KEY:
        return False
    paragraphs = ''.join(f'<p>{p}</p>' for p in draft_text.strip().split('\n\n'))
    try:
        r = requests.post(
            'https://api.resend.com/emails',
            headers={'Authorization': f'Bearer {RESEND_API_KEY}'},
            json={
                'from': RESEND_FROM_EMAIL,
                'to': [to_email],
                'subject': 'Re : Votre message à Cognito Inc.',
                'html': paragraphs,
            },
            timeout=10
        )
        return r.ok
    except requests.RequestException:
        return False

# ==================== AUTH ADMIN ====================

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

# ==================== ROUTES PUBLIQUES ====================

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/robots.txt')
def robots_txt():
    return Response('User-agent: *\nAllow: /\nDisallow: /admin\nSitemap: https://cognito-inc.ca/sitemap.xml\n', mimetype='text/plain')

@app.route('/sitemap.xml')
def sitemap_xml():
    paths = ('/', '/services', '/service/development', '/service/ai', '/service/innovation',
             '/products', '/projects', '/about', '/contact')
    entries = ''.join(f'<url><loc>https://cognito-inc.ca{path}</loc></url>' for path in paths)
    xml = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + entries + '</urlset>'
    return Response(xml, mimetype='application/xml')

@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/projects')
def projects():
    return render_template('projects.html')

@app.route('/products')
def products():
    return render_template('products.html')

@app.route('/partners')
def partners():
    return redirect(url_for('about'), code=301)

@app.route('/testimonials')
def testimonials():
    return redirect(url_for('projects'), code=301)

@app.route('/submit-testimonial', methods=['POST'])
def submit_testimonial():
    try:
        name         = request.form.get('name', '').strip()
        role         = request.form.get('role', '').strip()
        company      = request.form.get('company', '').strip()
        project_type = request.form.get('project_type', '').strip()
        comment      = request.form.get('comment', '').strip()
        try:
            rating = max(1, min(5, int(request.form.get('rating', '5'))))
        except ValueError:
            rating = 5

        if not name or not comment:
            return jsonify({'success': False, 'message': 'Veuillez remplir les champs obligatoires.'})

        db = get_db()
        db.execute(
            'INSERT INTO testimonials (name, role, company, rating, project_type, comment) VALUES (?,?,?,?,?,?)',
            (name, role, company, rating, project_type, comment)
        )
        db.commit()
        return jsonify({'success': True, 'message': 'Merci pour votre témoignage ! Il sera publié après validation.'})
    except Exception:
        return jsonify({'success': False, 'message': "Erreur lors de l'envoi."})

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/service/innovation')
def service_innovation():
    return render_template('service_innovation.html')

@app.route('/service/development')
def service_development():
    return render_template('service_development.html')

@app.route('/service/ai')
def service_ai():
    return render_template('service_ai.html')

@app.route('/project/ia-predictive')
def project_ia_predictive():
    return redirect(url_for('projects'), code=301)

@app.route('/project/mobile-app')
def project_mobile_app():
    return redirect(url_for('projects'), code=301)

@app.route('/project/saas-platform')
def project_saas_platform():
    return redirect(url_for('projects'), code=301)

@app.route('/project/chatbot-ai')
def project_chatbot_ai():
    return redirect(url_for('projects'), code=301)

@app.route('/project/iot-system')
def project_iot_system():
    return redirect(url_for('projects'), code=301)

@app.route('/project/blockchain')
def project_blockchain():
    return redirect(url_for('projects'), code=301)

@app.route('/project/lms-platform')
def project_lms_platform():
    return redirect(url_for('projects'), code=301)

@app.route('/project/<slug>')
def project_detail(slug):
    db = get_db()
    project = db.execute('SELECT * FROM projects WHERE slug = ?', (slug,)).fetchone()
    if not project:
        return render_template('404.html'), 404
    return render_template('project_detail.html', project=project)

@app.route('/ai-assistant')
def ai_assistant():
    return redirect(url_for('contact'), code=301)

# ==================== FORMULAIRE DE CONTACT ====================

@app.route('/send_message', methods=['POST'])
def send_message():
    try:
        data    = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({'success': False, 'message': 'Format de demande invalide.'}), 400
        name    = (data.get('name')    or '').strip()
        email   = (data.get('email')   or '').strip()
        phone   = (data.get('phone')   or '').strip()
        company = (data.get('company') or '').strip()
        service = (data.get('service') or '').strip()
        message = (data.get('message') or '').strip()

        if not name or not email or not message:
            return jsonify({'success': False, 'message': 'Veuillez remplir les champs obligatoires.'}), 400
        if len(name) > 120 or len(email) > 254 or len(company) > 160 or len(phone) > 32 or len(message) > 5000:
            return jsonify({'success': False, 'message': 'Un ou plusieurs champs dépassent la longueur permise.'}), 400
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
            return jsonify({'success': False, 'message': 'Veuillez saisir une adresse courriel valide.'}), 400

        # Générer un brouillon de réponse avec l'IA (avec accès aux projets/témoignages/tarifs réels)
        ai_draft = call_llm(
            f"Un client nommé {name} contacte Cognito Inc. via le formulaire de contact.\n"
            f"Service d'intérêt : {SERVICE_LABELS.get(service, 'Non précisé')}\n"
            f"Entreprise : {company or 'Non précisée'}\n"
            f"Message du client : {message}\n\n"
            "Rédige une réponse email professionnelle et chaleureuse en français (100-130 mots). "
            "Si le client parle de prix ou de tarifs, base-toi sur les tarifs réels fournis dans le contexte. "
            "Corps de l'email uniquement, pas de ligne Objet. Ne mets aucune formule de politesse finale "
            "ni signature (ni '[Votre nom]'), je m'en occupe moi-même.",
            system=COGNITO_SYSTEM + get_db_context() + get_tarif_context(),
            max_tokens=300
        )
        ai_draft = finalize_draft(ai_draft)

        # Enregistrer en base : action critique, doit réussir pour que le message soit considéré envoyé
        try:
            db = get_db()
            cur = db.execute(
                'INSERT INTO contact_messages (name, email, phone, company, service, message, ai_draft) '
                'VALUES (?, ?, ?, ?, ?, ?, ?)',
                (name, email, phone, company, service, message, ai_draft)
            )
            db.commit()
            msg_id = cur.lastrowid
        except Exception:
            return jsonify({'success': False, 'message': "Erreur lors de l'envoi du message"}), 500

        # Construire la notification Telegram (détails + brouillon IA dans un seul message)
        notif = (
            "📩 Nouveau message de contact\n\n"
            f"👤 Nom : {name}\n"
            f"✉️ Email : {email}\n"
            + (f"📱 Téléphone : {phone}\n" if phone else "")
            + f"🏢 Entreprise : {company or 'Non précisé'}\n"
            f"🔧 Service : {SERVICE_LABELS.get(service, 'Non précisé')}\n\n"
            f"💬 Message :\n{message}"
        )
        if ai_draft:
            notif += f"\n\n✨ Aperçu de la réponse (IA) :\n{ai_draft}"

        host = os.environ.get('RAILWAY_PUBLIC_DOMAIN') or request.host
        token = email_token_serializer.dumps(msg_id)
        inline_rows = [[
            {'text': '✉️ Envoyer la réponse par email', 'url': f'https://{host}/go/email?token={token}'}
        ]]
        wa_link = whatsapp_link(phone, text=ai_draft)
        if wa_link:
            inline_rows.append([{'text': '💬 Répondre par WhatsApp', 'url': wa_link}])
        reply_markup = {'inline_keyboard': inline_rows}

        # Notification best-effort : ne doit jamais faire échouer la requête,
        # le message est déjà enregistré en base à ce stade
        send_telegram_message(TELEGRAM_CHAT_ID, notif, reply_markup=reply_markup)

        send_confirmation_email(name, email)

        return jsonify({'success': True, 'message': 'Message envoyé avec succès!'})
    except Exception:
        return jsonify({'success': False, 'message': "Erreur lors de l'envoi du message"}), 500

def _go_email_page(message):
    return (
        "<!doctype html><html lang='fr'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<title>Cognito Inc.</title></head>"
        "<body style='font-family:sans-serif; background:#0f1117; color:#eee; "
        "display:flex; align-items:center; justify-content:center; height:100vh; margin:0;'>"
        f"<div style='text-align:center; padding:24px;'><p style='font-size:1.1rem;'>{message}</p></div>"
        "</body></html>"
    )

@app.route('/go/email')
def go_email():
    # Ce lien est cliqué depuis le bouton Telegram "Envoyer la réponse par email" :
    # il déclenche l'envoi réel du brouillon IA au client via Resend (pas un mailto:,
    # que Telegram refuse de toute façon pour les boutons inline — BUTTON_URL_INVALID).
    token = request.args.get('token', '')
    try:
        msg_id = email_token_serializer.loads(token)
    except BadSignature:
        return _go_email_page("Lien invalide ou expiré."), 400

    db  = get_db()
    row = db.execute('SELECT * FROM contact_messages WHERE id = ?', (msg_id,)).fetchone()
    if not row:
        return _go_email_page("Message introuvable."), 404

    if row['email_sent_at']:
        return _go_email_page(f"✅ Cet email a déjà été envoyé à {row['email']} le {row['email_sent_at'][:16]}.")

    draft = row['ai_draft'] or finalize_draft(f"Bonjour {row['name']},\n\nMerci pour votre message, nous revenons vers vous rapidement.")
    if send_draft_email(row['email'], draft):
        db.execute('UPDATE contact_messages SET email_sent_at = CURRENT_TIMESTAMP WHERE id = ?', (msg_id,))
        db.commit()
        return _go_email_page(f"✅ Email envoyé avec succès à {row['email']}.")

    return _go_email_page("❌ Erreur lors de l'envoi (Resend non configuré ou erreur API)."), 500

# ==================== CHAT (widget site) ====================

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data    = request.get_json()
        message = (data.get('message') or '').strip()
        if not message:
            return jsonify({'success': False, 'message': 'Message vide'})
        return jsonify({'success': True, 'response': generate_ai_response(message)})
    except Exception:
        return jsonify({'success': False, 'message': "Erreur de l'assistant"})

# ==================== WEBHOOK TELEGRAM ====================

def build_stats_message():
    try:
        db = get_db()
        total   = db.execute('SELECT COUNT(*) FROM contact_messages').fetchone()[0]
        last_30 = db.execute(
            "SELECT COUNT(*) FROM contact_messages WHERE created_at >= datetime('now', '-30 days')"
        ).fetchone()[0]
        last_7 = db.execute(
            "SELECT COUNT(*) FROM contact_messages WHERE created_at >= datetime('now', '-7 days')"
        ).fetchone()[0]
        by_service = db.execute(
            "SELECT service, COUNT(*) as n FROM contact_messages "
            "WHERE created_at >= datetime('now', '-30 days') GROUP BY service ORDER BY n DESC"
        ).fetchall()
        pending_testimonials = db.execute(
            "SELECT COUNT(*) FROM testimonials WHERE status='pending'"
        ).fetchone()[0]

        visits_total = db.execute('SELECT COUNT(*) FROM page_views').fetchone()[0]
        visits_30 = db.execute(
            "SELECT COUNT(*) FROM page_views WHERE created_at >= datetime('now', '-30 days')"
        ).fetchone()[0]
        visits_7 = db.execute(
            "SELECT COUNT(*) FROM page_views WHERE created_at >= datetime('now', '-7 days')"
        ).fetchone()[0]
        top_pages = db.execute(
            "SELECT path, COUNT(*) as n FROM page_views "
            "WHERE created_at >= datetime('now', '-30 days') GROUP BY path ORDER BY n DESC LIMIT 5"
        ).fetchall()

        lines = [
            "📊 Statistiques Cognito Inc.",
            "",
            "👀 Pages vues (total) : " + str(visits_total),
            f"🗓️ 30 derniers jours : {visits_30}",
            f"📅 7 derniers jours : {visits_7}",
        ]
        if top_pages:
            lines.append("")
            lines.append("🔝 Pages les plus visitées (30j) :")
            for row in top_pages:
                lines.append(f"  • {row['path']} : {row['n']}")
        lines.append("")
        lines.append(f"📩 Messages de contact (total) : {total}")
        lines.append(f"🗓️ 30 derniers jours : {last_30}")
        lines.append(f"📅 7 derniers jours : {last_7}")
        if by_service:
            lines.append("")
            lines.append("🔧 Répartition par service (30j) :")
            for row in by_service:
                label = SERVICE_LABELS.get(row['service'], row['service'] or 'Non précisé')
                lines.append(f"  • {label} : {row['n']}")
        lines.append("")
        lines.append(f"⭐ Témoignages en attente de validation : {pending_testimonials}")
        return "\n".join(lines)
    except Exception:
        return "Erreur lors de la récupération des statistiques."

@app.route('/telegram-webhook', methods=['POST'])
def telegram_webhook():
    update  = request.get_json(silent=True) or {}
    msg     = update.get('message', {})
    chat_id = msg.get('chat', {}).get('id')
    text    = (msg.get('text') or '').strip()
    if not chat_id or not text:
        return jsonify({'ok': True})

    is_admin = bool(TELEGRAM_CHAT_ID) and str(chat_id) == str(TELEGRAM_CHAT_ID)

    if is_admin:
        stats_text = build_stats_message()
        if text.lower() in ('/stats', '/statistiques'):
            send_telegram_message(chat_id, stats_text)
        else:
            admin_system = (
                "Tu es l'assistant interne de Cognito Inc. sur Telegram, réservé à l'administrateur. "
                "Réponds à sa question en te basant UNIQUEMENT sur les statistiques ci-dessous. "
                "Sois concis, précis et va droit au but, en français.\n" + stats_text
            )
            response = call_llm(text, system=admin_system, max_tokens=200)
            send_telegram_message(chat_id, response or stats_text)
    else:
        send_telegram_message(chat_id, generate_ai_response(text))
    return jsonify({'ok': True})

# ==================== ADMIN ====================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        pwd = request.form.get('password', '')
        if pwd and pwd == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        error = 'Mot de passe incorrect.'
    return render_template('admin/login.html', error=error)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

@app.route('/admin')
@admin_required
def admin_dashboard():
    db = get_db()
    messages             = db.execute('SELECT * FROM contact_messages ORDER BY created_at DESC LIMIT 20').fetchall()
    projects_count       = db.execute('SELECT COUNT(*) FROM projects').fetchone()[0]
    messages_count       = db.execute('SELECT COUNT(*) FROM contact_messages').fetchone()[0]
    pending_testimonials = db.execute("SELECT COUNT(*) FROM testimonials WHERE status='pending'").fetchone()[0]
    return render_template('admin/dashboard.html',
                           messages=messages,
                           projects_count=projects_count,
                           messages_count=messages_count,
                           pending_testimonials=pending_testimonials)

# --- Projets ---

@app.route('/admin/projects')
@admin_required
def admin_projects():
    projects = get_db().execute('SELECT * FROM projects ORDER BY created_at DESC').fetchall()
    return render_template('admin/projects.html', projects=projects)

@app.route('/admin/projects/new', methods=['GET', 'POST'])
@admin_required
def admin_project_new():
    if request.method == 'POST':
        title      = request.form.get('title', '').strip()
        category   = request.form.get('category', '').strip()
        short_desc = request.form.get('short_desc', '').strip()
        long_desc  = request.form.get('long_desc', '').strip()
        tech_tags  = request.form.get('tech_tags', '').strip()
        status     = request.form.get('status', 'completed')
        link       = request.form.get('link', '').strip()

        slug = slugify(title)
        db   = get_db()
        base_slug, counter = slug, 1
        while db.execute('SELECT id FROM projects WHERE slug = ?', (slug,)).fetchone():
            slug = f'{base_slug}-{counter}'
            counter += 1

        db.execute(
            'INSERT INTO projects (title, slug, category, short_desc, long_desc, tech_tags, status, link) '
            'VALUES (?,?,?,?,?,?,?,?)',
            (title, slug, category, short_desc, long_desc, tech_tags, status, link)
        )
        db.commit()
        return redirect(url_for('admin_projects'))

    return render_template('admin/project_form.html', project=None)

@app.route('/admin/projects/<int:project_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_project_edit(project_id):
    db      = get_db()
    project = db.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
    if not project:
        return redirect(url_for('admin_projects'))

    if request.method == 'POST':
        db.execute(
            'UPDATE projects SET title=?, category=?, short_desc=?, long_desc=?, '
            'tech_tags=?, status=?, link=? WHERE id=?',
            (
                request.form.get('title', '').strip(),
                request.form.get('category', '').strip(),
                request.form.get('short_desc', '').strip(),
                request.form.get('long_desc', '').strip(),
                request.form.get('tech_tags', '').strip(),
                request.form.get('status', 'completed'),
                request.form.get('link', '').strip(),
                project_id
            )
        )
        db.commit()
        return redirect(url_for('admin_projects'))

    return render_template('admin/project_form.html', project=project)

@app.route('/admin/projects/<int:project_id>/delete', methods=['POST'])
@admin_required
def admin_project_delete(project_id):
    db = get_db()
    db.execute('DELETE FROM projects WHERE id = ?', (project_id,))
    db.commit()
    return redirect(url_for('admin_projects'))

@app.route('/admin/generate-description', methods=['POST'])
@admin_required
def admin_generate_description():
    data      = request.get_json()
    title     = data.get('title', '')
    category  = data.get('category', '')
    tech_tags = data.get('tech_tags', '')
    hint      = data.get('hint', '')

    prompt = (
        f"Génère une description professionnelle pour ce projet réalisé par Cognito Inc. :\n"
        f"- Titre : {title}\n"
        f"- Catégorie : {category}\n"
        f"- Technologies : {tech_tags}\n"
        f"- Contexte/Détails : {hint}\n\n"
        "Retourne UNIQUEMENT un objet JSON valide (sans balises Markdown) avec :\n"
        "- \"short_desc\" : accroche courte (1 phrase, max 120 caractères)\n"
        "- \"long_desc\" : description complète et professionnelle (150-200 mots)"
    )
    response = call_llm(prompt, max_tokens=600)
    if not response:
        return jsonify({'success': False, 'message': "API NVIDIA non configurée ou erreur."})

    try:
        parsed = json.loads(response)
        return jsonify({'success': True, **parsed})
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group())
                return jsonify({'success': True, **parsed})
            except Exception:
                pass
        return jsonify({'success': False, 'message': 'Erreur de format', 'raw': response})

# --- Liens sociaux ---

@app.route('/admin/links', methods=['GET', 'POST'])
@admin_required
def admin_links():
    db = get_db()
    if request.method == 'POST':
        for key in ('linkedin', 'twitter', 'github', 'youtube'):
            url_val = request.form.get(key, '').strip() or '#'
            db.execute('INSERT OR REPLACE INTO social_links (key, url) VALUES (?, ?)', (key, url_val))
        db.commit()
        return redirect(url_for('admin_links'))

    links = {r['key']: r['url'] for r in db.execute('SELECT * FROM social_links').fetchall()}
    return render_template('admin/links.html', links=links)

# --- Témoignages ---

@app.route('/admin/testimonials')
@admin_required
def admin_testimonials():
    db      = get_db()
    pending  = db.execute("SELECT * FROM testimonials WHERE status='pending' ORDER BY created_at DESC").fetchall()
    approved = db.execute("SELECT * FROM testimonials WHERE status='approved' ORDER BY created_at DESC").fetchall()
    return render_template('admin/testimonials.html', pending=pending, approved=approved)

@app.route('/admin/testimonials/<int:tid>/approve', methods=['POST'])
@admin_required
def admin_testimonial_approve(tid):
    db = get_db()
    db.execute("UPDATE testimonials SET status='approved' WHERE id=?", (tid,))
    db.commit()
    return redirect(url_for('admin_testimonials'))

@app.route('/admin/testimonials/<int:tid>/reject', methods=['POST'])
@admin_required
def admin_testimonial_reject(tid):
    db = get_db()
    db.execute("DELETE FROM testimonials WHERE id=?", (tid,))
    db.commit()
    return redirect(url_for('admin_testimonials'))

# --- Statut du bot ---

@app.route('/admin/test-telegram')
@admin_required
def admin_test_telegram():
    token   = TELEGRAM_BOT_TOKEN
    chat_id = TELEGRAM_CHAT_ID
    if not token or not chat_id:
        return jsonify({'ok': False, 'error': 'Variables manquantes', 'token_set': bool(token), 'chat_id_set': bool(chat_id)})
    try:
        url = f'https://api.telegram.org/bot{token}/sendMessage'
        r   = requests.post(url, json={'chat_id': chat_id, 'text': '✅ Test depuis Railway - Admin Cognito Inc.'}, timeout=10)
        return jsonify({'ok': r.ok, 'status': r.status_code, 'telegram': r.json(), 'chat_id_used': chat_id})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

@app.route('/admin/bot')
@admin_required
def admin_bot():
    telegram_ok  = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
    nvidia_ok    = bool(NVIDIA_API_KEY)
    resend_ok    = bool(RESEND_API_KEY)
    host         = os.environ.get('RAILWAY_PUBLIC_DOMAIN') or request.host
    webhook_url  = f"https://{host}{url_for('telegram_webhook')}"
    setup_url    = (
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook?url={webhook_url}"
        if TELEGRAM_BOT_TOKEN else None
    )
    return render_template('admin/bot.html',
                           telegram_ok=telegram_ok,
                           nvidia_ok=nvidia_ok,
                           resend_ok=resend_ok,
                           setup_url=setup_url,
                           webhook_url=webhook_url)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
