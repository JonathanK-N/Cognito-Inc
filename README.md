# Cognito Inc.

Site vitrine de Cognito Inc., développé avec Flask, Jinja, CSS et JavaScript.

## Démarrer localement

1. Installer Python et créer un environnement virtuel.
2. Installer les dépendances : `pip install -r requirements.txt`.
3. Copier `.env.example` vers `.env` et renseigner les services facultatifs nécessaires.
4. Lancer le serveur : `python app.py`.

Sans clés d’API, les pages publiques et les fonctions principales du site restent accessibles. Les notifications Telegram, les courriels Resend et les réponses NVIDIA dépendent de leur configuration. La base SQLite est créée au démarrage.

## Pages principales

- `/` — Accueil
- `/services` — Expertises
- `/service/development`, `/service/ai`, `/service/innovation` — Détails des expertises
- `/products` — Produits et solutions
- `/projects` — Portfolio
- `/about` — À propos
- `/partners`, `/testimonials` — Écosystème et témoignages
- `/contact` — Formulaire de demande
- `/robots.txt`, `/sitemap.xml` — Référencement

Les sections de produits, de projets, de partenaires et de témoignages restent volontairement sans exemples tant que les informations ne sont pas confirmées et autorisées.

## Intégrations

L’application conserve SQLite pour les demandes, projets et témoignages; Telegram pour les notifications, Resend pour les courriels et NVIDIA pour la rédaction facultative de réponses assistées. La gestion administrative existante demeure disponible sous `/admin`. Le déploiement est configuré par `Procfile` et `railway.toml`.

## Rapport de refonte

Voir [`docs/COGNITO_WEBSITE_REDESIGN_REPORT.md`](docs/COGNITO_WEBSITE_REDESIGN_REPORT.md) pour le bilan de l’audit, les choix visuels, les pages retravaillées, les validations et les éléments à confirmer.
