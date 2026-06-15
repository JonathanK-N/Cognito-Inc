from flask import Flask, render_template, request, jsonify
import os
import requests

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

SERVICE_LABELS = {
    'innovation': 'Innovation technologique',
    'development': 'Développement sur mesure',
    'ai': 'Intelligence artificielle',
    'consulting': 'Conseil stratégique',
    'partnership': 'Partenariat'
}

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
    return render_template('projects.html')

@app.route('/partners')
def partners():
    return render_template('partners.html')

@app.route('/testimonials')
def testimonials():
    return render_template('testimonials.html')

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

@app.route('/ai-assistant')
def ai_assistant():
    return render_template('ai_assistant.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        message = data.get('message')
        
        # Logique de réponse simple (peut être étendue avec une vraie IA)
        response = generate_ai_response(message)
        
        return jsonify({'success': True, 'response': response})
    except Exception as e:
        return jsonify({'success': False, 'message': 'Erreur de l\'assistant'})

def generate_ai_response(message):
    # Réponses basiques - peut être remplacé par une vraie IA
    message_lower = message.lower()
    
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

@app.route('/send_message', methods=['POST'])
def send_message():
    try:
        data = request.get_json()
        name = (data.get('name') or '').strip()
        email = (data.get('email') or '').strip()
        company = (data.get('company') or '').strip()
        service = (data.get('service') or '').strip()
        message = (data.get('message') or '').strip()

        if not name or not email or not message:
            return jsonify({'success': False, 'message': 'Veuillez remplir les champs obligatoires.'}), 400

        text = (
            "📩 Nouveau message de contact\n\n"
            f"👤 Nom: {name}\n"
            f"✉️ Email: {email}\n"
            f"🏢 Entreprise: {company or 'Non précisé'}\n"
            f"🔧 Service: {SERVICE_LABELS.get(service, 'Non précisé')}\n\n"
            f"💬 Message:\n{message}"
        )

        if not send_telegram_notification(text, email):
            return jsonify({'success': False, 'message': 'Erreur lors de l\'envoi du message'}), 500

        return jsonify({'success': True, 'message': 'Message envoyé avec succès!'})
    except Exception:
        return jsonify({'success': False, 'message': 'Erreur lors de l\'envoi du message'}), 500


def send_telegram_notification(text, reply_email):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False

    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': text,
        'reply_markup': {
            'inline_keyboard': [[
                {'text': '📧 Répondre par mail', 'url': f'mailto:{reply_email}'}
            ]]
        }
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.ok
    except requests.RequestException:
        return False

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)