from flask import Flask, Response, render_template, request, jsonify, session, redirect, url_for, g, send_from_directory, abort
import uuid
import hmac
import hashlib
import os
from datetime import datetime
import sqlite3
import re
import json
import urllib.parse
from functools import wraps
import requests
from dotenv import load_dotenv
from itsdangerous import URLSafeSerializer, BadSignature
import messaging

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-change-this-secret')
app.config['MAX_CONTENT_LENGTH'] = 6 * 1024 * 1024
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
UPLOAD_DIR         = os.path.join(os.path.dirname(os.path.abspath(DATABASE_PATH)), 'uploads')

# --- Coordonnées Cognito Inc. ---
SITE_EMAIL         = 'contact@cognito-inc.ca'
SITE_PHONE_DISPLAY = '+1 (819) 272-5034'
SITE_PHONE_TEL     = '+18192725034'

SERVICE_LABELS = {
    'innovation': 'Recherche et développement',
    'development': 'Développement web et mobile',
    'ai': 'Intelligence artificielle et données',
    'cybersecurity': 'Cybersécurité et conformité',
    'consulting': 'Conseil et maintenance',
    'partnership': 'Partenariat'
}

COGNITO_SYSTEM = (
    "Tu es l'assistant IA de Cognito Inc., une entreprise technologique spécialisée dans plusieurs domaines : "
    "développement web et mobile, intelligence artificielle et valorisation des données, cybersécurité et conformité, "
    "ainsi que conseil technique et maintenance applicative. "
    "Elle accompagne des entreprises de toutes tailles dans leur transformation numérique, "
    "des produits numériques aux systèmes d'entreprise. N'annonce aucun prix, tarif ou montant. "
    "Si un visiteur demande une estimation, invite-le à décrire son besoin dans le formulaire de contact. "
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

    testimonial_columns = {row[1] for row in conn.execute('PRAGMA table_info(testimonials)')}
    if 'location' not in testimonial_columns:
        conn.execute('ALTER TABLE testimonials ADD COLUMN location TEXT')
    if 'photo' not in testimonial_columns:
        conn.execute('ALTER TABLE testimonials ADD COLUMN photo TEXT')

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

# Partenaires présentés sur l'accueil et la page /partners
PARTNERS = [
    {'name': 'Odoo', 'role': 'Intégrateur ERP', 'logo': 'odoo.png',
     'text': "Déploiement et personnalisation d'Odoo pour structurer les opérations."},
    {'name': 'SkyITUp S.A.', 'role': 'Services technologiques', 'logo': 'skyitup.png',
     'text': 'Partenariat de services technologiques en Afrique centrale.'},
    {'name': 'Orange Digital Center', 'role': 'Formation & FabLab Kinshasa', 'logo': 'orange-digital-center-logo.png',
     'text': 'Formation, encadrement et accès au prototypage à Kinshasa.'},
    {'name': 'Université Loyola du Congo / ICAM', 'role': 'Déploiement LMS', 'logo': 'ulc-icam-logo.png',
     'text': "Plateforme d'apprentissage Cognito Web déployée pour l'établissement."},
    {'name': 'TransitFlow', 'role': 'Transport & logistique', 'logo': None,
     'text': 'ERP de gestion de flotte, de trajets et de chauffeurs pour le transport multipays.'},
    {'name': 'Green Kin', 'role': 'Partenaire stratégique', 'logo': 'green-kin.png',
     'text': 'Valorisation des déchets plastiques et solutions durables à Kinshasa.'},
    {'name': 'Afrimarket', 'role': 'Partenaire technologique', 'logo': 'afrimarket.png',
     'text': 'Solutions numériques pour le commerce en ligne sur les marchés africains.'},
]

@app.context_processor
def inject_partners():
    if request.path.startswith('/admin'):
        return {}
    return {'partners': PARTNERS}

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

def generate_ai_response(message_text):
    if NVIDIA_API_KEY:
        extra_context = get_db_context()
        response = call_llm(
            f"Un visiteur du site Cognito Inc. écrit dans le chat : \"{message_text}\". "
            "Réponds de façon concise et professionnelle en moins de 100 mots. "
            "Si la question porte sur des projets ou des témoignages, utilise les données fournies dans le contexte. "
            "N'annonce aucun prix, tarif ou montant; oriente les demandes d'estimation vers le formulaire de contact.",
            system=COGNITO_SYSTEM + extra_context,
            max_tokens=250
        )
        if response:
            return response
    message_lower = message_text.lower()
    if 'bonjour' in message_lower or 'salut' in message_lower:
        return "Bonjour ! Comment puis-je vous aider aujourd'hui ?"
    elif 'service' in message_lower:
        return "Cognito accompagne les projets en développement web et mobile, IA et données, cybersécurité, conseil technique et maintenance. Quel est votre besoin ?"
    elif 'prix' in message_lower or 'devis' in message_lower:
        return "Pour orienter votre demande, décrivez votre contexte et votre besoin dans le formulaire de contact."
    elif 'rdv' in message_lower or 'rendez-vous' in message_lower:
        return "Envoyez vos disponibilités dans le formulaire de contact. L’équipe pourra vous répondre directement."
    else:
        return "Je comprends. Pouvez-vous me donner plus de détails sur votre besoin ?"

def send_telegram_message(chat_id, text, reply_markup=None, html=False):
    if not TELEGRAM_BOT_TOKEN or not chat_id:
        return False
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    payload = {'chat_id': chat_id, 'text': text, 'link_preview_options': {'is_disabled': True}}
    if html:
        payload['parse_mode'] = 'HTML'
    if reply_markup:
        payload['reply_markup'] = reply_markup
    try:
        r = requests.post(url, json=payload, timeout=10)
        if not r.ok:
            app.logger.warning('Telegram sendMessage a échoué (%s) : %s', r.status_code, r.text[:300])
        return r.ok
    except requests.RequestException as exc:
        app.logger.warning('Telegram injoignable : %s', exc)
        return False

def notify_admin(text, reply_markup=None):
    return send_telegram_message(TELEGRAM_CHAT_ID, text, reply_markup=reply_markup, html=True)

def send_email(to_email, subject, html, text):
    if not RESEND_API_KEY:
        return False
    try:
        r = requests.post(
            'https://api.resend.com/emails',
            headers={'Authorization': f'Bearer {RESEND_API_KEY}'},
            json={
                'from': RESEND_FROM_EMAIL,
                'to': [to_email],
                'reply_to': SITE_EMAIL,
                'subject': subject,
                'html': html,
                'text': text,
            },
            timeout=10
        )
        if not r.ok:
            app.logger.warning('Resend a refusé le courriel (%s) : %s', r.status_code, r.text[:300])
        return r.ok
    except requests.RequestException as exc:
        app.logger.warning('Resend injoignable : %s', exc)
        return False

def send_confirmation_email(name, to_email, service_label, message, company=None, phone=None):
    subject, html, text = messaging.contact_confirmation_email(name, service_label, message, company, phone)
    return send_email(to_email, subject, html, text)

def send_draft_email(row, draft_text):
    subject, html, text = messaging.reply_email(
        row['name'], draft_text, original_message=row['message'], original_date=row['created_at']
    )
    return send_email(row['email'], subject, html, text)

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
    approved_testimonials = get_db().execute(
        "SELECT name, role, company, rating, project_type, comment, location, photo FROM testimonials "
        "WHERE status='approved' ORDER BY created_at DESC LIMIT 12"
    ).fetchall()
    return render_template('index.html', approved_testimonials=approved_testimonials)

@app.route('/robots.txt')
def robots_txt():
    return Response('User-agent: *\nAllow: /\nDisallow: /admin\nSitemap: https://cognito-inc.ca/sitemap.xml\n', mimetype='text/plain')

@app.route('/sitemap.xml')
def sitemap_xml():
    paths = ('/', '/services', '/service/development', '/service/ai', '/service/cybersecurity', '/service/advisory',
             '/products', '/projects', '/partners', '/testimonials', '/about', '/contact', '/confidentialite')
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

@app.route('/confidentialite')
def privacy():
    return render_template('privacy.html')

@app.route('/politique-de-confidentialite')
def privacy_alias():
    return redirect(url_for('privacy'), code=301)

@app.route('/partners')
def partners():
    return render_template('partners.html')

@app.route('/testimonials')
def testimonials():
    approved_testimonials = get_db().execute(
        "SELECT name, role, company, rating, project_type, comment, location, photo FROM testimonials "
        "WHERE status='approved' ORDER BY created_at DESC LIMIT 30"
    ).fetchall()
    return render_template('testimonials.html', approved_testimonials=approved_testimonials)

@app.route('/submit-testimonial', methods=['POST'])
def submit_testimonial():
    try:
        name         = request.form.get('name', '').strip()
        role         = request.form.get('role', '').strip()
        company      = request.form.get('company', '').strip()
        project_type = request.form.get('project_type', '').strip()
        location     = request.form.get('location', '').strip()[:120]
        comment      = request.form.get('comment', '').strip()
        try:
            rating = max(1, min(5, int(request.form.get('rating', '5'))))
        except ValueError:
            rating = 5

        if not name or not comment:
            return jsonify({'success': False, 'message': 'Veuillez remplir les champs obligatoires.'})

        db = get_db()
        db.execute(
            'INSERT INTO testimonials (name, role, company, rating, project_type, comment, location) VALUES (?,?,?,?,?,?,?)',
            (name, role, company, rating, project_type, comment, location)
        )
        db.commit()
        host = os.environ.get('RAILWAY_PUBLIC_DOMAIN') or request.host
        notify_admin(
            messaging.tg_new_testimonial(name, role, company, rating, project_type, comment),
            reply_markup={'inline_keyboard': [[{'text': '✅ Valider dans l’administration', 'url': f'https://{host}/admin/testimonials'}]]},
        )
        return jsonify({'success': True, 'message': 'Merci pour votre témoignage ! Il sera publié après validation.'})
    except Exception:
        return jsonify({'success': False, 'message': "Erreur lors de l'envoi."})

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/service/innovation')
def service_innovation():
    return redirect(url_for('service_advisory'), code=301)

@app.route('/service/development')
def service_development():
    return render_template('service_development.html')

@app.route('/service/ai')
def service_ai():
    return render_template('service_ai.html')

@app.route('/service/cybersecurity')
def service_cybersecurity():
    return render_template('service_cybersecurity.html')

@app.route('/service/advisory')
def service_advisory():
    return render_template('service_advisory.html')

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

        # Générer un brouillon de réponse avec les informations vérifiées sur les projets et les témoignages.
        ai_draft = call_llm(
            f"Un client nommé {name} contacte Cognito Inc. via le formulaire de contact.\n"
            f"Service d'intérêt : {SERVICE_LABELS.get(service, 'Non précisé')}\n"
            f"Entreprise : {company or 'Non précisée'}\n"
            f"Message du client : {message}\n\n"
            "Rédige une réponse email professionnelle et chaleureuse en français (100-130 mots). "
            "N’annonce aucun prix, tarif ou montant; propose plutôt de poursuivre l’échange après avoir compris le besoin. "
            "Corps de l'email uniquement, pas de ligne Objet. Ne mets aucune formule de politesse finale "
            "ni signature (ni '[Votre nom]'), je m'en occupe moi-même.",
            system=COGNITO_SYSTEM + get_db_context(),
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

        service_label = SERVICE_LABELS.get(service, 'Non précisé')

        # Notification Telegram : détails de la demande + brouillon IA, avec boutons d'action
        host = os.environ.get('RAILWAY_PUBLIC_DOMAIN') or request.host
        token = email_token_serializer.dumps(msg_id)
        inline_rows = [[
            {'text': '✉️ Envoyer la réponse par courriel', 'url': f'https://{host}/go/email?token={token}'}
        ]]
        wa_link = whatsapp_link(phone, text=messaging.strip_signoff(ai_draft) if ai_draft else None)
        if wa_link:
            inline_rows.append([{'text': '💬 Répondre par WhatsApp', 'url': wa_link}])
        inline_rows.append([{'text': '🗂️ Ouvrir l’administration', 'url': f'https://{host}/admin'}])

        # Best-effort : ne doit jamais faire échouer la requête, le message est déjà en base
        notify_admin(
            messaging.tg_new_contact(name, email, phone, company, service_label, message, ai_draft, msg_id),
            reply_markup={'inline_keyboard': inline_rows},
        )

        if not send_confirmation_email(name, email, service_label, message, company, phone):
            notify_admin(messaging.tg_email_failed('accusé de réception', email, msg_id))

        return jsonify({'success': True, 'message': 'Merci ! Votre demande a bien été envoyée. Un courriel de confirmation vient de vous être adressé.'})
    except Exception:
        return jsonify({'success': False, 'message': "Erreur lors de l'envoi du message"}), 500

def _go_email_page(title, message, status='success'):
    return render_template('action_result.html', title=title, message=message, status=status)

@app.route('/go/email')
def go_email():
    # Ce lien est cliqué depuis le bouton Telegram « Envoyer la réponse par courriel » :
    # il déclenche l'envoi réel du brouillon au client via Resend (pas un mailto:,
    # que Telegram refuse pour les boutons inline — BUTTON_URL_INVALID).
    token = request.args.get('token', '')
    try:
        msg_id = email_token_serializer.loads(token)
    except BadSignature:
        return _go_email_page('Lien invalide', 'Ce lien est invalide ou a expiré.', 'error'), 400

    db  = get_db()
    row = db.execute('SELECT * FROM contact_messages WHERE id = ?', (msg_id,)).fetchone()
    if not row:
        return _go_email_page('Demande introuvable', 'Cette demande n’existe plus dans la base.', 'error'), 404

    if row['email_sent_at']:
        return _go_email_page(
            'Déjà envoyée',
            f"La réponse a déjà été envoyée à {row['email']} le {messaging.french_date(row['email_sent_at'], with_time=True)}.",
            'info',
        )

    draft = row['ai_draft'] or finalize_draft(
        f"Bonjour {row['name']},\n\nMerci pour votre message. Nous l’avons bien lu et nous revenons vers vous très rapidement "
        "pour en discuter."
    )
    if send_draft_email(row, draft):
        db.execute('UPDATE contact_messages SET email_sent_at = CURRENT_TIMESTAMP WHERE id = ?', (msg_id,))
        db.commit()
        notify_admin(messaging.tg_reply_sent(row['name'], row['email'], msg_id))
        return _go_email_page('Réponse envoyée', f"Le courriel a bien été envoyé à {row['email']}.")

    notify_admin(messaging.tg_email_failed('réponse au client', row['email'], msg_id))
    return _go_email_page('Échec de l’envoi', 'Le courriel n’a pas pu être envoyé. Vérifiez la configuration Resend.', 'error'), 500

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

        return messaging.tg_stats(
            visits_total, visits_30, visits_7,
            [(row['path'], row['n']) for row in top_pages],
            total, last_30, last_7,
            [(SERVICE_LABELS.get(row['service'], row['service'] or 'Non précisé'), row['n']) for row in by_service],
            pending_testimonials,
        )
    except Exception:
        return "Erreur lors de la récupération des statistiques."

def telegram_webhook_secret():
    """Jeton partagé avec Telegram (setWebhook secret_token) pour authentifier les appels du webhook."""
    return hmac.new(app.secret_key.encode(), b'telegram-webhook', hashlib.sha256).hexdigest()[:48]

@app.route('/telegram-webhook', methods=['POST'])
def telegram_webhook():
    received = request.headers.get('X-Telegram-Bot-Api-Secret-Token', '')
    if not hmac.compare_digest(received, telegram_webhook_secret()):
        return jsonify({'ok': False}), 403
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
            send_telegram_message(chat_id, stats_text, html=True)
        else:
            admin_system = (
                "Tu es l'assistant interne de Cognito Inc. sur Telegram, réservé à l'administrateur. "
                "Réponds à sa question en te basant UNIQUEMENT sur les statistiques ci-dessous. "
                "Sois concis, précis et va droit au but, en français.\n" + re.sub(r'<[^>]+>', '', stats_text)
            )
            response = call_llm(text, system=admin_system, max_tokens=200)
            if response:
                send_telegram_message(chat_id, response)
            else:
                send_telegram_message(chat_id, stats_text, html=True)
    else:
        send_telegram_message(chat_id, generate_ai_response(text))
    return jsonify({'ok': True})

# ==================== ADMIN ====================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        pwd = request.form.get('password', '')
        if pwd and ADMIN_PASSWORD and hmac.compare_digest(pwd.encode(), ADMIN_PASSWORD.encode()):
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

ALLOWED_PHOTO_TYPES = {'image/jpeg': '.jpg', 'image/png': '.png', 'image/webp': '.webp'}

def save_testimonial_photo(file):
    """Enregistre la photo d'un auteur d'avis sur le volume et retourne son nom de fichier."""
    if not file or not file.filename:
        return None
    ext = ALLOWED_PHOTO_TYPES.get(file.mimetype)
    if not ext:
        return None
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    filename = f'avis-{uuid.uuid4().hex[:12]}{ext}'
    file.save(os.path.join(UPLOAD_DIR, filename))
    return filename

@app.route('/media/avis/<path:filename>')
def testimonial_photo(filename):
    if not re.fullmatch(r'avis-[0-9a-f]{12}\.(jpg|png|webp)', filename):
        abort(404)
    return send_from_directory(UPLOAD_DIR, filename, max_age=60 * 60 * 24 * 30)

@app.route('/admin/testimonials/new', methods=['POST'])
@admin_required
def admin_testimonial_new():
    name    = request.form.get('name', '').strip()
    comment = request.form.get('comment', '').strip()
    if name and comment:
        try:
            rating = max(1, min(5, int(request.form.get('rating', '5'))))
        except ValueError:
            rating = 5
        db = get_db()
        db.execute(
            'INSERT INTO testimonials (name, role, company, rating, project_type, comment, location, photo, status) '
            "VALUES (?,?,?,?,?,?,?,?,'pending')",
            (name, request.form.get('role', '').strip(), request.form.get('company', '').strip(), rating,
             request.form.get('project_type', '').strip(), comment, request.form.get('location', '').strip()[:120],
             save_testimonial_photo(request.files.get('photo')))
        )
        db.commit()
    return redirect(url_for('admin_testimonials'))

@app.route('/admin/testimonials/<int:tid>/photo', methods=['POST'])
@admin_required
def admin_testimonial_photo(tid):
    filename = save_testimonial_photo(request.files.get('photo'))
    if filename:
        db = get_db()
        db.execute('UPDATE testimonials SET photo=? WHERE id=?', (filename, tid))
        db.commit()
    return redirect(url_for('admin_testimonials'))

@app.route('/admin/testimonials/<int:tid>/unpublish', methods=['POST'])
@admin_required
def admin_testimonial_unpublish(tid):
    db = get_db()
    db.execute("UPDATE testimonials SET status='pending' WHERE id=?", (tid,))
    db.commit()
    return redirect(url_for('admin_testimonials'))

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

def telegram_api(method, **params):
    """Appelle l'API Telegram côté serveur ; le jeton du bot ne quitte jamais le serveur."""
    if not TELEGRAM_BOT_TOKEN:
        return None
    try:
        r = requests.post(f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{method}', json=params, timeout=10)
        return r.json()
    except Exception:
        app.logger.exception('Appel Telegram %s impossible', method)
        return None

@app.route('/admin/bot')
@admin_required
def admin_bot():
    host        = os.environ.get('RAILWAY_PUBLIC_DOMAIN') or request.host
    webhook_url = f"https://{host}{url_for('telegram_webhook')}"
    info        = (telegram_api('getWebhookInfo') or {}).get('result') or {}
    return render_template('admin/bot.html',
                           telegram_ok=bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID),
                           nvidia_ok=bool(NVIDIA_API_KEY),
                           resend_ok=bool(RESEND_API_KEY),
                           token_set=bool(TELEGRAM_BOT_TOKEN),
                           webhook_url=webhook_url,
                           webhook_active=info.get('url') == webhook_url,
                           webhook_error=info.get('last_error_message'),
                           status=request.args.get('status'))

@app.route('/admin/bot/webhook', methods=['POST'])
@admin_required
def admin_bot_webhook():
    host        = os.environ.get('RAILWAY_PUBLIC_DOMAIN') or request.host
    webhook_url = f"https://{host}{url_for('telegram_webhook')}"
    result = telegram_api('setWebhook', url=webhook_url, secret_token=telegram_webhook_secret(),
                          allowed_updates=['message'], drop_pending_updates=True)
    return redirect(url_for('admin_bot', status='ok' if result and result.get('ok') else 'error'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
