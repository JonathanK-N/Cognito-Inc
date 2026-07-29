from flask import Flask, render_template, request, jsonify, session, redirect, url_for, g
import os
import sqlite3
import re
import json
import urllib.parse
from functools import wraps
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-change-this-secret')

# --- Configuration ---
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID   = os.environ.get('TELEGRAM_CHAT_ID')
RESEND_API_KEY     = os.environ.get('RESEND_API_KEY')
RESEND_FROM_EMAIL  = os.environ.get('RESEND_FROM_EMAIL', 'Cognito Inc. <contact@cognito-inc.ca>')
ADMIN_PASSWORD     = os.environ.get('ADMIN_PASSWORD', '')
ANTHROPIC_API_KEY  = os.environ.get('ANTHROPIC_API_KEY')
DATABASE_PATH      = os.environ.get('DATABASE_PATH', 'cognito.db')

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
    ''')
    for key in ('linkedin', 'twitter', 'github', 'youtube'):
        conn.execute('INSERT OR IGNORE INTO social_links (key, url) VALUES (?, ?)', (key, '#'))

    if conn.execute('SELECT COUNT(*) FROM projects').fetchone()[0] == 0:
        conn.executemany(
            'INSERT INTO projects (title, slug, category, short_desc, tech_tags, status) '
            'VALUES (?, ?, ?, ?, ?, ?)',
            [
                ('Système IA Prédictive pour E-commerce', 'ia-predictive', 'Intelligence Artificielle',
                 "Développement d'un modèle d'IA personnalisé pour prédire les tendances d'achat et optimiser les stocks. Augmentation de 35% des ventes.",
                 'Machine Learning, Python, TensorFlow', 'completed'),
                ('App Mobile de Gestion Intelligente', 'mobile-app', 'Développement Mobile',
                 "Application mobile avec IA intégrée pour la gestion automatisée des tâches professionnelles.",
                 'Flutter, Python, IA', 'completed'),
                ("Plateforme d'Analyse de Données", 'saas-platform', 'Plateforme SaaS',
                 "Solution SaaS complète pour l'analyse en temps réel de données massives avec tableaux de bord interactifs.",
                 'React, Node.js, BigQuery', 'completed'),
                ('Chatbot IA Multilingue', 'chatbot-ai', 'IA Conversationnelle',
                 "Assistant virtuel intelligent capable de gérer 95% des demandes clients en 12 langues.",
                 'NLP, Python, Claude', 'completed'),
                ('Système IoT Intelligent', 'iot-system', 'IoT & IA',
                 "Réseau de capteurs IoT avec IA pour l'optimisation énergétique des bâtiments intelligents.",
                 'IoT, Python, Edge AI', 'completed'),
                ('Plateforme Blockchain Sécurisée', 'blockchain', 'Blockchain & IA',
                 "Solution blockchain avec IA pour la traçabilité et l'authentification de produits de luxe.",
                 'Blockchain, Solidity, IA', 'completed'),
                ('Plateforme LMS - Université Loyola du Congo/ICAM', 'lms-platform', 'Plateforme Éducative',
                 "Système de gestion d'apprentissage complet avec IA pour l'enseignement supérieur et la formation continue.",
                 'Django, PostgreSQL, IA', 'completed'),
            ]
        )

    if conn.execute('SELECT COUNT(*) FROM testimonials').fetchone()[0] == 0:
        conn.executemany(
            'INSERT INTO testimonials (name, role, company, rating, comment, status) '
            'VALUES (?, ?, ?, ?, ?, ?)',
            [
                ('Marie Dubois', 'CEO', 'TechStart', 5,
                 "Cognito Inc. a transformé notre processus métier avec une solution IA sur mesure. Résultats exceptionnels !", 'approved'),
                ('Pierre Martin', 'CTO', 'InnovCorp', 5,
                 "Une équipe réactive et compétente. Notre application mobile dépasse toutes nos attentes.", 'approved'),
                ('Sophie Laurent', 'Directrice', 'DigitalPro', 5,
                 "Partenaire idéal pour notre transformation digitale. Expertise technique remarquable.", 'approved'),
                ('Julie Martin', 'Data Scientist', 'AnalyticsCorp', 5,
                 "La solution SaaS d'analyse prédictive nous a fait économiser 20h par semaine. Précision et fiabilité au rendez-vous.", 'approved'),
                ('Pierre Laurent', 'VP Customer Success', 'GlobalTech', 5,
                 "Le chatbot IA multilingue a révolutionné notre support client. Disponible 24/7, 90% de résolution en première interaction.", 'approved'),
                ('Thomas Rousseau', 'CTO', 'IndustrialSmart', 5,
                 "Leur solution IoT prédictive a réduit nos coûts de maintenance de 40%. Un ROI exceptionnel dès les premiers mois.", 'approved'),
            ]
        )

    conn.commit()
    conn.close()

init_db()

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

# ==================== HELPERS ====================

def slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    return re.sub(r'-+', '-', text)

def call_claude(prompt, system=None, max_tokens=1024):
    if not ANTHROPIC_API_KEY:
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model='claude-sonnet-5',
            max_tokens=max_tokens,
            system=system or COGNITO_SYSTEM,
            messages=[{'role': 'user', 'content': prompt}]
        )
        return msg.content[0].text.strip()
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
    if ANTHROPIC_API_KEY:
        db_context = get_db_context()
        response = call_claude(
            f"Un visiteur du site Cognito Inc. écrit dans le chat : \"{message_text}\". "
            "Réponds de façon concise et professionnelle en moins de 100 mots. "
            "Si la question porte sur des projets ou témoignages, utilise les données fournies dans le contexte.",
            system=COGNITO_SYSTEM + db_context,
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

@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/projects')
def projects():
    db = get_db()
    db_projects = db.execute('SELECT * FROM projects ORDER BY created_at DESC').fetchall()
    return render_template('projects.html', db_projects=db_projects)

@app.route('/partners')
def partners():
    return render_template('partners.html')

@app.route('/testimonials')
def testimonials():
    db = get_db()
    approved = db.execute(
        "SELECT * FROM testimonials WHERE status='approved' ORDER BY created_at DESC"
    ).fetchall()
    return render_template('testimonials.html', approved_testimonials=approved)

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
    return render_template('project_ia_predictive.html')

@app.route('/project/mobile-app')
def project_mobile_app():
    return render_template('project_mobile_app.html')

@app.route('/project/saas-platform')
def project_saas_platform():
    return render_template('project_saas_platform.html')

@app.route('/project/chatbot-ai')
def project_chatbot_ai():
    return render_template('project_chatbot_ai.html')

@app.route('/project/iot-system')
def project_iot_system():
    return render_template('project_iot_system.html')

@app.route('/project/blockchain')
def project_blockchain():
    return render_template('project_blockchain.html')

@app.route('/project/lms-platform')
def project_lms_platform():
    return render_template('project_lms_platform.html')

@app.route('/project/<slug>')
def project_detail(slug):
    db = get_db()
    project = db.execute('SELECT * FROM projects WHERE slug = ?', (slug,)).fetchone()
    if not project:
        return render_template('404.html'), 404
    return render_template('project_detail.html', project=project)

@app.route('/ai-assistant')
def ai_assistant():
    return render_template('ai_assistant.html')

# ==================== FORMULAIRE DE CONTACT ====================

@app.route('/send_message', methods=['POST'])
def send_message():
    try:
        data    = request.get_json()
        name    = (data.get('name')    or '').strip()
        email   = (data.get('email')   or '').strip()
        company = (data.get('company') or '').strip()
        service = (data.get('service') or '').strip()
        message = (data.get('message') or '').strip()

        if not name or not email or not message:
            return jsonify({'success': False, 'message': 'Veuillez remplir les champs obligatoires.'}), 400

        # Générer un brouillon de réponse avec Claude
        ai_draft = call_claude(
            f"Un client nommé {name} contacte Cognito Inc. via le formulaire de contact.\n"
            f"Service d'intérêt : {SERVICE_LABELS.get(service, 'Non précisé')}\n"
            f"Entreprise : {company or 'Non précisée'}\n"
            f"Message du client : {message}\n\n"
            "Rédige une réponse email professionnelle et chaleureuse en français (100-130 mots). "
            "Corps de l'email uniquement, pas de ligne Objet ni de balises.",
            max_tokens=300
        )

        # Enregistrer en base : action critique, doit réussir pour que le message soit considéré envoyé
        try:
            db = get_db()
            db.execute(
                'INSERT INTO contact_messages (name, email, company, service, message, ai_draft) '
                'VALUES (?, ?, ?, ?, ?, ?)',
                (name, email, company, service, message, ai_draft)
            )
            db.commit()
        except Exception:
            return jsonify({'success': False, 'message': "Erreur lors de l'envoi du message"}), 500

        # Construire la notification Telegram
        notif = (
            "📩 Nouveau message de contact\n\n"
            f"👤 Nom : {name}\n"
            f"✉️ Email : {email}\n"
            f"🏢 Entreprise : {company or 'Non précisé'}\n"
            f"🔧 Service : {SERVICE_LABELS.get(service, 'Non précisé')}\n\n"
            f"💬 Message :\n{message}"
        )
        reply_markup = {
            'inline_keyboard': [[
                {'text': '✉️ Répondre par email', 'url': f'mailto:{email}'}
            ]]
        }

        # Notifications best-effort : ne doivent jamais faire échouer la requête,
        # le message est déjà enregistré en base à ce stade
        send_telegram_message(TELEGRAM_CHAT_ID, notif, reply_markup=reply_markup)

        if ai_draft:
            send_telegram_message(
                TELEGRAM_CHAT_ID,
                f"✨ Brouillon de réponse (Claude) :\n\n{ai_draft}"
            )

        send_confirmation_email(name, email)

        return jsonify({'success': True, 'message': 'Message envoyé avec succès!'})
    except Exception:
        return jsonify({'success': False, 'message': "Erreur lors de l'envoi du message"}), 500

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

@app.route('/telegram-webhook', methods=['POST'])
def telegram_webhook():
    update  = request.get_json(silent=True) or {}
    msg     = update.get('message', {})
    chat_id = msg.get('chat', {}).get('id')
    text    = msg.get('text')
    if chat_id and text:
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
    response = call_claude(prompt, max_tokens=600)
    if not response:
        return jsonify({'success': False, 'message': "API Anthropic non configurée ou erreur."})

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
    claude_ok    = bool(ANTHROPIC_API_KEY)
    resend_ok    = bool(RESEND_API_KEY)
    host         = os.environ.get('RAILWAY_PUBLIC_DOMAIN') or request.host
    webhook_url  = f"https://{host}{url_for('telegram_webhook')}"
    setup_url    = (
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook?url={webhook_url}"
        if TELEGRAM_BOT_TOKEN else None
    )
    return render_template('admin/bot.html',
                           telegram_ok=telegram_ok,
                           claude_ok=claude_ok,
                           resend_ok=resend_ok,
                           setup_url=setup_url,
                           webhook_url=webhook_url)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
