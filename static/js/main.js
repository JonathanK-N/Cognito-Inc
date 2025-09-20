// Initialisation AOS et optimisations
document.addEventListener('DOMContentLoaded', function() {
    // Initialiser AOS
    AOS.init({
        duration: 800,
        easing: 'ease-out-cubic',
        once: true,
        offset: 100
    });
    const navToggle = document.getElementById('nav-toggle');
    const navMenu = document.getElementById('nav-menu');

    if (navToggle && navMenu) {
        navToggle.addEventListener('click', function() {
            navMenu.classList.toggle('active');
        });

        // Fermer le menu mobile quand on clique sur un lien
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', () => {
                navMenu.classList.remove('active');
            });
        });
    }

    // Animation des statistiques
    const statNumbers = document.querySelectorAll('.stat-number[data-target]');
    
    const animateStats = () => {
        statNumbers.forEach(stat => {
            const target = parseInt(stat.getAttribute('data-target'));
            if (!target || isNaN(target)) return;
            
            const increment = target / 50;
            let current = 0;
            
            const updateStat = () => {
                if (current < target) {
                    current += increment;
                    const value = Math.ceil(current);
                    const originalText = stat.getAttribute('data-suffix') || '';
                    stat.textContent = value + originalText;
                    setTimeout(updateStat, 50);
                } else {
                    const originalText = stat.getAttribute('data-suffix') || '';
                    stat.textContent = target + originalText;
                }
            };
            
            updateStat();
        });
    };

    // Observer pour déclencher l'animation des stats quand elles sont visibles
    const statsObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                animateStats();
                statsObserver.unobserve(entry.target);
            }
        });
    });

    const statsSection = document.querySelector('.stats-grid');
    if (statsSection && statNumbers.length > 0) {
        statsObserver.observe(statsSection);
    }

    // Formulaire de contact
    const contactForm = document.getElementById('contactForm');
    const formMessage = document.getElementById('formMessage');

    if (contactForm) {
        contactForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const submitBtn = contactForm.querySelector('button[type="submit"]');
            const btnText = submitBtn.querySelector('.btn-text');
            const btnLoading = submitBtn.querySelector('.btn-loading');
            
            // Afficher le loading
            btnText.style.display = 'none';
            btnLoading.style.display = 'inline-block';
            submitBtn.disabled = true;
            
            // Récupérer les données du formulaire
            const formData = {
                name: document.getElementById('name').value,
                email: document.getElementById('email').value,
                company: document.getElementById('company').value,
                service: document.getElementById('service').value,
                message: document.getElementById('message').value
            };
            
            try {
                const response = await fetch('/send_message', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(formData)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    formMessage.className = 'form-message success';
                    formMessage.textContent = result.message;
                    contactForm.reset();
                } else {
                    formMessage.className = 'form-message error';
                    formMessage.textContent = result.message;
                }
                
                formMessage.style.display = 'block';
                
            } catch (error) {
                formMessage.className = 'form-message error';
                formMessage.textContent = 'Une erreur est survenue. Veuillez réessayer.';
                formMessage.style.display = 'block';
            } finally {
                // Restaurer le bouton
                btnText.style.display = 'inline-block';
                btnLoading.style.display = 'none';
                submitBtn.disabled = false;
            }
        });
    }

    // Smooth scroll pour les liens d'ancrage
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Animation d'apparition des éléments au scroll
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);

    // Observer les cartes et sections
    document.querySelectorAll('.feature-card, .service-card, .value-card, .team-member, .faq-item').forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(30px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(el);
    });

    // Parallax effect pour les éléments flottants
    const floatingElements = document.querySelectorAll('.floating-element');
    
    window.addEventListener('scroll', () => {
        const scrolled = window.pageYOffset;
        
        floatingElements.forEach(element => {
            const speed = element.dataset.speed || 1;
            const yPos = -(scrolled * speed * 0.1);
            element.style.transform = `translateY(${yPos}px)`;
        });
    });

    // Highlight du lien de navigation actuel
    const currentLocation = location.pathname;
    const navLinks = document.querySelectorAll('.nav-link');
    
    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentLocation) {
            link.style.color = 'var(--primary-color)';
            link.style.fontWeight = '600';
        }
    });

    // Lazy loading des images
    const images = document.querySelectorAll('img[data-src]');
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.classList.remove('lazy');
                observer.unobserve(img);
            }
        });
    });
    
    images.forEach(img => imageObserver.observe(img));

    // Performance: Préchargement des pages importantes
    const importantLinks = document.querySelectorAll('a[href^="/"]');
    importantLinks.forEach(link => {
        link.addEventListener('mouseenter', () => {
            const linkElement = document.createElement('link');
            linkElement.rel = 'prefetch';
            linkElement.href = link.href;
            document.head.appendChild(linkElement);
        }, { once: true });
    });
});

// Fonction utilitaire pour débouncer les événements
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Optimisation du scroll
const optimizedScroll = debounce(() => {
    // Code de scroll optimisé ici si nécessaire
}, 10);