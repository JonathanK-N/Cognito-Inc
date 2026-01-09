from flask import Flask, render_template, request, jsonify
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)

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
        name = data.get('name')
        email = data.get('email')
        message = data.get('message')
        
        # Ici vous pouvez ajouter la logique d'envoi d'email
        # Pour l'instant, on simule un succès
        
        return jsonify({'success': True, 'message': 'Message envoyé avec succès!'})
    except Exception as e:
        return jsonify({'success': False, 'message': 'Erreur lors de l\'envoi du message'})

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)