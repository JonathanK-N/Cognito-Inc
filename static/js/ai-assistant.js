// Assistant IA JavaScript
let chatOpen = false;
let conversationContext = [];

// Réponses prédéfinies de l'assistant
const responses = {
    services: {
        keywords: ['service', 'services', 'que faites-vous', 'activité', 'domaine'],
        response: `**Les expertises de Cognito :**

• Ingénierie logicielle et intégrations
• IA, automatisation et systèmes intelligents
• Recherche et développement

Les solutions sont cadrées selon le besoin du projet. [Parlez-nous de votre contexte](/contact).`
    },
    devis: {
        keywords: ['devis', 'prix', 'coût', 'tarif', 'budget', 'combien'],
        response: `Pour discuter d’un devis, décrivez votre besoin, votre contexte et vos principales contraintes dans le [formulaire de contact](/contact). L’équipe pourra examiner votre demande.`
    },
    rdv: {
        keywords: ['rendez-vous', 'rdv', 'rencontrer', 'meeting', 'consultation'],
        response: `Je ne peux pas confirmer de rendez-vous directement. Envoyez votre demande et vos disponibilités par le [formulaire de contact](/contact).`
    },
    contact: {
        keywords: ['contact', 'joindre', 'téléphone', 'email', 'adresse'],
        response: `📞 **Nos Coordonnées**

• **Email :** contact@cognito-inc.ca
• **Téléphone :** +1 (819) 272-5034
• **Localisation :** Sherbrooke, Québec

Vous pouvez écrire ou appeler Cognito directement.`
    },
    ia: {
        keywords: ['intelligence artificielle', 'ia', 'machine learning', 'ml', 'chatbot'],
        response: `Cognito explore l’IA, l’automatisation et le traitement des données selon les besoins du projet. Nous commençons par examiner le cas d’usage, les données et les contraintes avant de définir une approche.`
    }
};

function openChat() {
    document.getElementById('chatWidget').style.display = 'none';
    document.querySelector('.ai-assistant-container').style.display = 'flex';
    chatOpen = true;
    
    // Supprimer la notification
    const dot = document.querySelector('.notification-dot');
    if (dot) dot.style.display = 'none';
}

function toggleChat() {
    document.querySelector('.ai-assistant-container').style.display = 'none';
    document.getElementById('chatWidget').style.display = 'block';
    chatOpen = false;
}

function handleKeyPress(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

function sendQuickMessage(message) {
    document.getElementById('messageInput').value = message;
    sendMessage();
}

async function sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();

    if (!message) return;

    addMessage(message, 'user');
    input.value = '';
    conversationContext.push({role: 'user', content: message});
    showTypingIndicator();

    try {
        const res = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });
        const data = await res.json();
        hideTypingIndicator();
        const reply = (data.success && data.response) ? data.response : generateResponse(message);
        addMessage(reply, 'bot');
        conversationContext.push({role: 'bot', content: reply});
    } catch (_) {
        hideTypingIndicator();
        const reply = generateResponse(message);
        addMessage(reply, 'bot');
        conversationContext.push({role: 'bot', content: reply});
    }
}

function addMessage(content, sender) {
    const messagesContainer = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = formatMessage(content);

    if (sender === 'bot') {
        const contactBtn = document.createElement('a');
        contactBtn.href = '/contact';
        contactBtn.className = 'chat-contact-btn';
        contactBtn.innerHTML = '<i class="fas fa-envelope"></i> Nous contacter';
        contentDiv.appendChild(contactBtn);
    }

    messageDiv.appendChild(contentDiv);
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function formatMessage(content) {
    const escaped = String(content).replace(/[&<>"']/g, character => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[character]));
    return escaped
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n/g, '<br>')
        .replace(/•/g, '•');
}

function generateResponse(userMessage) {
    const message = userMessage.toLowerCase();
    
    // Vérifier les mots-clés pour chaque catégorie
    for (const [category, data] of Object.entries(responses)) {
        if (data.keywords.some(keyword => message.includes(keyword))) {
            return data.response;
        }
    }
    
    // Réponses contextuelles
    if (message.includes('merci')) {
        return `😊 De rien ! Je suis là pour vous aider. Avez-vous d'autres questions ?`;
    }
    
    if (message.includes('bonjour') || message.includes('salut')) {
        return `👋 Bonjour ! Ravi de vous parler. Comment puis-je vous aider avec vos projets technologiques ?`;
    }
    
    // Ne pas confirmer automatiquement un rendez-vous.
    if (message.includes('lundi') || message.includes('mardi') || message.includes('mercredi') || 
        message.includes('jeudi') || message.includes('vendredi')) {
        return `Je ne peux pas confirmer une disponibilité. Indiquez vos préférences dans le [formulaire de contact](/contact) afin que l’équipe puisse vous répondre.`;
    }
    
    // Réponse par défaut
    return `Je peux vous orienter vers nos expertises en ingénierie logicielle, en IA et systèmes intelligents, ou en recherche et développement. Pour une question précise, [écrivez à l’équipe](/contact).`;
}

function showTypingIndicator() {
    const messagesContainer = document.getElementById('chatMessages');
    const typingDiv = document.createElement('div');
    typingDiv.className = 'typing-indicator';
    typingDiv.id = 'typingIndicator';
    
    for (let i = 0; i < 3; i++) {
        const dot = document.createElement('div');
        dot.className = 'typing-dot';
        typingDiv.appendChild(dot);
    }
    
    messagesContainer.appendChild(typingDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function hideTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    if (indicator) {
        indicator.remove();
    }
}

// Initialisation
document.addEventListener('DOMContentLoaded', function() {
    // Afficher la notification après 3 secondes
    setTimeout(() => {
        if (!chatOpen) {
            const dot = document.querySelector('.notification-dot');
            if (dot) dot.style.display = 'block';
        }
    }, 3000);
});

// Fermer le chat en cliquant à l'extérieur
document.addEventListener('click', function(event) {
    const chatContainer = document.querySelector('.ai-assistant-container');
    const chatWidget = document.getElementById('chatWidget');
    
    if (chatOpen && !chatContainer.contains(event.target) && !chatWidget.contains(event.target)) {
        toggleChat();
    }
});
