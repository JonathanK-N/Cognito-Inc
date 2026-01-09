// Assistant IA JavaScript
let chatOpen = false;
let conversationContext = [];

// Réponses prédéfinies de l'assistant
const responses = {
    services: {
        keywords: ['service', 'services', 'que faites-vous', 'activité', 'domaine'],
        response: `🔧 **Nos Services Principaux :**

• **Innovation Technologique** - R&D et solutions innovantes
• **Développement Logiciel** - Applications web/mobile sur mesure  
• **Intelligence Artificielle** - IA, ML et automatisation

Quel service vous intéresse le plus ? Je peux vous donner plus de détails !`
    },
    devis: {
        keywords: ['devis', 'prix', 'coût', 'tarif', 'budget', 'combien'],
        response: `💰 **Devis Personnalisé**

Pour vous proposer un devis précis, j'ai besoin de quelques informations :

• Type de projet souhaité
• Fonctionnalités principales
• Délais envisagés
• Budget approximatif

Pouvez-vous me parler de votre projet ?`
    },
    rdv: {
        keywords: ['rendez-vous', 'rdv', 'rencontrer', 'meeting', 'consultation'],
        response: `📅 **Prise de Rendez-vous**

Parfait ! Je peux organiser un rendez-vous avec notre équipe.

**Créneaux disponibles :**
• Lundi-Vendredi : 9h-18h
• Durée : 30-60 minutes
• Format : Présentiel ou visioconférence

Quelle date vous conviendrait le mieux ?`
    },
    contact: {
        keywords: ['contact', 'joindre', 'téléphone', 'email', 'adresse'],
        response: `📞 **Nos Coordonnées**

• **Email :** contact@cognito-inc.com
• **Téléphone :** +243 XXX XXX XXX
• **Adresse :** Kinshasa, RD Congo

Vous préférez être contacté par quel moyen ?`
    },
    ia: {
        keywords: ['intelligence artificielle', 'ia', 'machine learning', 'ml', 'chatbot'],
        response: `🤖 **Intelligence Artificielle**

Nous développons des solutions IA avancées :

• Chatbots intelligents
• Analyse prédictive
• Automatisation de processus
• Vision par ordinateur
• Traitement du langage naturel

Quel type de solution IA recherchez-vous ?`
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

function sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();
    
    if (!message) return;
    
    // Ajouter le message utilisateur
    addMessage(message, 'user');
    input.value = '';
    
    // Ajouter à l'historique
    conversationContext.push({role: 'user', content: message});
    
    // Afficher l'indicateur de frappe
    showTypingIndicator();
    
    // Générer et afficher la réponse
    setTimeout(() => {
        const response = generateResponse(message);
        hideTypingIndicator();
        addMessage(response, 'bot');
        conversationContext.push({role: 'bot', content: response});
    }, 1500);
}

function addMessage(content, sender) {
    const messagesContainer = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = formatMessage(content);
    
    messageDiv.appendChild(contentDiv);
    messagesContainer.appendChild(messageDiv);
    
    // Scroll vers le bas
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function formatMessage(content) {
    return content
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
    
    // Gestion des dates pour RDV
    if (message.includes('lundi') || message.includes('mardi') || message.includes('mercredi') || 
        message.includes('jeudi') || message.includes('vendredi')) {
        return `✅ **Rendez-vous confirmé !**
        
J'ai noté votre préférence. Un membre de notre équipe vous contactera sous 24h pour confirmer les détails.

**Prochaines étapes :**
• Confirmation par email
• Envoi du lien de visioconférence
• Préparation de votre dossier

Merci de votre confiance ! 🚀`;
    }
    
    // Réponse par défaut
    return `🤔 Je comprends votre question. Pour vous donner la meilleure réponse, pouvez-vous préciser :

• Quel type de service vous intéresse ?
• Votre secteur d'activité ?
• Vos objectifs principaux ?

Ou utilisez les boutons rapides ci-dessous ! 👇`;
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