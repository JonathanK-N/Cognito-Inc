# Rapport de refonte du site Cognito Inc.

Date : 7 novembre 2026

## Résumé

Le site a reçu une nouvelle direction visuelle et éditoriale : un studio technologique d’ingénierie, avec une identité bleu nuit et bleu électrique, une typographie éditoriale, des schémas techniques dessinés en CSS et des sections claires qui rythment la lecture. L’expérience privilégie les expertises, les produits, les projets et une prise de contact directe.

Les pages qui présentaient des statistiques, des résultats de projets, des témoignages et des partenaires d’exemple ont été remplacées par des états éditoriaux transparents. Aucun produit ou projet n’est présenté comme une réalisation vérifiée sans information publique confirmée.

## Audit technique

- Application serveur Flask avec routes rendues par Jinja et fichiers statiques CSS/JavaScript.
- SQLite initialise les tables de projets, témoignages, demandes de contact, liens sociaux et visites.
- Le formulaire de contact transmet les demandes à `/send_message`, enregistre la demande, peut envoyer une notification Telegram et une confirmation Resend. Si NVIDIA est configuré, le contenu de la demande est aussi utilisé pour préparer un brouillon de réponse.
- Le clavardage utilise `/chat`, avec réponses locales et intégration NVIDIA facultative. Les services tarifaires sont lus depuis `TARIF_URL` par le serveur.
- L’administration des projets, des témoignages et des liens demeure sous `/admin`.
- Déploiement Flask/Gunicorn défini par `Procfile` et `railway.toml`.
- Le site public initial contenait des chiffres de croissance et de satisfaction, des études de cas et des témoignages préremplis qui n’étaient pas étayés par les informations du dépôt.

## Changements de conception

### Système visuel

- Couleurs : bleu nuit `#091426`, bleu profond `#112744`, bleu électrique `#1677E8`, bleu ciel `#48A9FF`, blanc froid `#F4F6FA`, ardoise `#64748B` et charbon `#182230`.
- Typographies : Space Grotesk pour les titres, Inter pour le texte, JetBrains Mono pour les repères techniques.
- Navigation fixe avec fond renforcé au défilement, menu mobile accessible et indicateur de page courante.
- Composants : boutons, liens éditoriaux, rangées d’expertises, étapes de méthode, schémas, formulaires et pied de page.
- Visuels abstraits conçus en CSS, sans photographies génériques, bibliothèque d’animation ou script d’animation externe.
- Animations limitées à l’apparition de contenu et au schéma du hero; elles sont désactivées ou réduites si l’utilisateur préfère les mouvements réduits.

### Pages modifiées

- Accueil : nouveau hero « Ingénierie de ce qui vient », schéma système, introduction, expertises, présentation de l’approche produit, méthode en cinq étapes et appel à l’action.
- Expertises et pages détaillées : ingénierie logicielle, IA et systèmes intelligents, recherche et développement.
- Produits : nouvelle route `/products`, avec présentation transparente en attendant des produits publiquement vérifiés.
- Projets : portfolio éditorial sans fiches ou résultats non confirmés.
- À propos : activités, principes et mission, sans métriques ou équipe non validées.
- Contact : formulaire resserré, coordonnées, validation HTML et serveur, consentement et information sur le traitement des demandes.
- Partenaires et témoignages : états vides honnêtes jusqu’à confirmation et autorisation.
- Assistant Cognito, page 404 et fiche de projet administrée : nouvelle présentation; le clavardage n’annonce plus de rendez-vous fictifs et échappe son contenu avant affichage.
- Pied de page et navigation : liens vers les principales pages et coordonnées de contact.

## Décisions techniques

- La structure Flask, le stockage SQLite, les intégrations et les routes de contact ont été conservés.
- Une route de produits a été ajoutée. Les routes de services historiques restent accessibles.
- Les anciennes routes de projets d’exemple redirigent vers le portfolio; les projets saisis par l’administration conservent leur route dynamique.
- Les enregistrements d’exemple connus (sept slugs de projet et six sociétés de témoignage) sont supprimés lors de l’initialisation de la base, et ne sont plus ajoutés aux nouvelles bases.
- La validation du formulaire vérifie les champs requis, le format du courriel et les longueurs maximales avant l’enregistrement.
- Les messages du clavardage sont échappés avant insertion dans le DOM. Les réponses locales ne prétendent plus réserver ou confirmer un rendez-vous.
- Canonical, Open Graph en français canadien, données structurées de l’organisation, `robots.txt` et `sitemap.xml` ont été ajoutés.
- Le sélecteur français/anglais n’a pas été affiché : le dépôt ne contient pas de système de traduction fonctionnel.
- Aucun nom d’auteur n’a été ajouté aux fichiers ou aux informations Git; aucun commit ni nouvelle branche n’a été créé pour cette intervention.

## Validations effectuées

- `node --check static/js/main.js` : réussi.
- `node --check static/js/ai-assistant.js` : réussi.
- Vérification statique des 15 templates HTML de premier niveau : aucun bloc Jinja dupliqué et toutes les références `url_for` pointent vers une fonction existante.
- `git diff --check` : réussi; Git signale seulement la normalisation CRLF attendue sur Windows.
- Vérification du code et des templates : le contenu public actuel ne contient plus les compteurs, entreprises, témoignages et résultats d’exemple retirés.
- Aucune dépendance de production ou configuration de déploiement n’a été remplacée.

## À vérifier avant publication

- Python n’est pas installé ni accessible dans l’environnement de travail (`python` renvoie l’alias du Microsoft Store). Le chargement Flask, la compilation Python, le rendu Jinja, les tests des routes, la validation complète du formulaire et les vues dans un navigateur n’ont donc pas pu être exécutés localement.
- Rejouer les validations Flask et inspecter les pages sur téléphone, tablette et ordinateur dans un environnement doté des dépendances du projet.
- Effectuer les contrôles automatisés d’accessibilité, de contraste, de performance et de Core Web Vitals; aucun score Lighthouse n’est revendiqué.
- Confirmer les produits, études de cas, affiliations, témoignages, liens sociaux et visuels que Cognito souhaite publier.
- Confirmer la politique de conservation des demandes et la notice de confidentialité, notamment pour les services externes facultatifs déjà branchés.
- Les fontes sont chargées depuis Google Fonts; prévoir une stratégie de fontes locales si l’autonomie vis-à-vis de ce service est requise.
- Les coordonnées sont celles déjà présentes dans le site et l’application; confirmer qu’elles sont toujours à jour.
