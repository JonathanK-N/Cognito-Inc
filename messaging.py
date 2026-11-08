"""Mise en forme des courriels (Resend) et des notifications Telegram de Cognito Inc.

Les courriels utilisent les gabarits de templates/emails/ (même structure pour tous les cas :
en-tête avec logo, contenu, bouton, bandeau d'information, signature, pied de page) et sont
toujours accompagnés d'une version texte. Les notifications Telegram utilisent le mode HTML
de Telegram ; tout contenu saisi par un visiteur est échappé.
"""
from datetime import datetime, timezone
from html import escape as _escape
import re
from zoneinfo import ZoneInfo

from flask import render_template

SITE_URL = 'https://cognito-inc.ca'
SITE_EMAIL = 'contact@cognito-inc.ca'
SITE_PHONE = '+1 (819) 272-5034'
TELEGRAM_LIMIT = 4000
LOCAL_TZ = ZoneInfo('America/Toronto')


def escape(value):
    return _escape(str(value or ''), quote=False)

MONTHS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet',
          'août', 'septembre', 'octobre', 'novembre', 'décembre']

_SIGNOFF_RE = re.compile(
    r"\n\s*(?:Cordialement|Bien cordialement|Sincèrement|Bien à vous)\s*,?\s*(?:\n.*)?$",
    re.IGNORECASE | re.DOTALL,
)


# ----------------------------------------------------------------------------
# Outils
# ----------------------------------------------------------------------------

def french_date(value=None, with_time=False):
    """Date lisible en français : « 8 novembre 2026 » (option : « à 16 h 05 »)."""
    if value is None:
        value = datetime.now(LOCAL_TZ)
    elif isinstance(value, str):
        # Les dates SQLite (CURRENT_TIMESTAMP) sont en UTC
        try:
            value = datetime.fromisoformat(value.replace(' ', 'T')[:19]).replace(tzinfo=timezone.utc).astimezone(LOCAL_TZ)
        except ValueError:
            return value
    text = f"{value.day} {MONTHS[value.month - 1]} {value.year}"
    if with_time:
        text += f" à {value.hour} h {value.minute:02d}"
    return text


def split_paragraphs(text):
    """Découpe un texte en paragraphes (lignes vides) en conservant les retours simples."""
    if not text:
        return []
    blocks = re.split(r'\n\s*\n', text.strip())
    return [' '.join(line.strip() for line in b.splitlines() if line.strip()) for b in blocks if b.strip()]


def strip_signoff(text):
    """Retire la formule de politesse finale : la signature est ajoutée par le gabarit."""
    return _SIGNOFF_RE.sub('', (text or '').strip()).strip()


def truncate(text, limit):
    text = (text or '').strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + '…'


# ----------------------------------------------------------------------------
# Courriels
# ----------------------------------------------------------------------------

def _base_context(**ctx):
    ctx.setdefault('site_url', SITE_URL)
    ctx.setdefault('site_email', SITE_EMAIL)
    ctx.setdefault('site_phone', SITE_PHONE)
    return ctx


def _text_footer():
    return (
        "\n\nCordialement,\nL'équipe Cognito Inc.\n\n"
        f"—\nCognito Inc. · Sherbrooke (Québec) · Kinshasa\n{SITE_EMAIL} · {SITE_PHONE} · {SITE_URL}"
    )


def contact_confirmation_email(name, service_label, message, company=None, phone=None):
    """Accusé de réception envoyé au visiteur après le formulaire de contact."""
    subject = 'Nous avons bien reçu votre demande — Cognito Inc.'
    sent_at = french_date(with_time=True)
    ctx = _base_context(
        subject=subject,
        preheader='Votre demande est bien arrivée. Nous vous répondons sous 24 heures ouvrables.',
        eyebrow='Demande reçue',
        heading='Merci, votre demande est bien arrivée.',
        name=name,
        service_label=service_label,
        company=company,
        phone=phone,
        sent_at=sent_at,
        message_lines=split_paragraphs(truncate(message, 1500)),
        cta_url=f'{SITE_URL}/projects',
        cta_label='Découvrir nos réalisations',
        info_lines=[
            'Besoin d’ajouter un détail ou un document ? Répondez simplement à ce courriel.',
            'Pour une question urgente, joignez-nous au ' + SITE_PHONE + '.',
        ],
        notice='Ne partagez pas d’information confidentielle (mots de passe, données bancaires) par courriel.',
        footer_reason='Vous recevez ce message car une demande a été envoyée depuis le formulaire de contact de cognito-inc.ca.',
    )
    html = render_template('emails/contact_confirmation.html', **ctx)
    text = (
        f"Bonjour {name},\n\n"
        "Merci d’avoir pris contact avec Cognito Inc. Votre demande est bien arrivée et un membre de "
        "l’équipe vous répondra dans un délai de 24 heures ouvrables.\n\n"
        "Récapitulatif de votre demande\n"
        f"- Service : {service_label}\n"
        + (f"- Organisation : {company}\n" if company else '')
        + (f"- Téléphone : {phone}\n" if phone else '')
        + f"- Envoyée le : {sent_at}\n\n"
        f"Votre message :\n{truncate(message, 1500)}\n\n"
        "La suite\n"
        "1. Analyse : nous relisons votre besoin et votre contexte.\n"
        "2. Premier échange : nous revenons vers vous par courriel ou par téléphone.\n"
        "3. Proposition : nous vous présentons une approche adaptée et les prochaines étapes.\n\n"
        "Besoin d’ajouter un détail ? Répondez simplement à ce courriel."
        + _text_footer()
    )
    return subject, html, text


def reply_email(name, body, original_message=None, original_date=None):
    """Réponse personnalisée envoyée au client (à partir du brouillon validé)."""
    subject = 'Re : Votre demande à Cognito Inc.'
    body = strip_signoff(body)
    paragraphs = split_paragraphs(body)
    greeting_re = r'(bonjour|salut)\b[^.!?]{0,60}[,!]?'
    greeting = paragraphs[0] if paragraphs and re.fullmatch(greeting_re, paragraphs[0], re.IGNORECASE) else None
    if greeting:
        paragraphs = paragraphs[1:]
    elif name:
        greeting = f'Bonjour {name},'
    else:
        greeting = 'Bonjour,'
    ctx = _base_context(
        subject=subject,
        preheader=truncate(paragraphs[1] if len(paragraphs) > 1 else (paragraphs[0] if paragraphs else ''), 110),
        eyebrow='Réponse à votre demande',
        heading=greeting,
        body_paragraphs=paragraphs,
        original_lines=split_paragraphs(truncate(original_message, 800)) if original_message else [],
        original_date=french_date(original_date) if original_date else None,
        cta_url=f'mailto:{SITE_EMAIL}?subject=' + 'Re%20%3A%20Votre%20demande%20%C3%A0%20Cognito%20Inc.',
        cta_label='Répondre à Cognito Inc.',
        info_lines=[
            'Vous pouvez répondre directement à ce courriel : il arrive dans notre boîte de réception.',
            'Préférez-vous un appel ? Indiquez-nous vos disponibilités ou joignez-nous au ' + SITE_PHONE + '.',
        ],
        footer_reason='Vous recevez ce message en réponse à votre demande envoyée sur cognito-inc.ca.',
    )
    html = render_template('emails/reply.html', **ctx)
    text = greeting + '\n\n' + '\n\n'.join(paragraphs)
    if original_message:
        text += f"\n\n> Votre message :\n> " + truncate(original_message, 800).replace('\n', '\n> ')
    text += _text_footer()
    return subject, html, text


# ----------------------------------------------------------------------------
# Notifications Telegram (mode HTML)
# ----------------------------------------------------------------------------

def _tg(text):
    return truncate(text, TELEGRAM_LIMIT)


def tg_new_contact(name, email, phone, company, service_label, message, ai_draft=None, msg_id=None):
    lines = [
        '📩 <b>Nouvelle demande de contact</b>' + (f'  <code>#{msg_id}</code>' if msg_id else ''),
        f'<i>{escape(french_date(with_time=True))}</i>',
        '',
        f'👤 <b>{escape(name)}</b>' + (f' · {escape(company)}' if company else ''),
        f'✉️ {escape(email)}',
    ]
    if phone:
        lines.append(f'📱 {escape(phone)}')
    lines += [
        f'🔧 {escape(service_label)}',
        '',
        '💬 <b>Message</b>',
        f'<blockquote>{escape(truncate(message, 1500))}</blockquote>',
    ]
    if ai_draft:
        lines += [
            '',
            '✨ <b>Brouillon de réponse (IA)</b>',
            f'<blockquote expandable>{escape(truncate(strip_signoff(ai_draft), 1500))}</blockquote>',
        ]
    else:
        lines += ['', '⚠️ <i>Aucun brouillon IA (service indisponible).</i>']
    lines += ['', '👇 Envoyez la réponse avec le bouton ci-dessous.']
    return _tg('\n'.join(lines))


def tg_reply_sent(name, email, msg_id=None):
    return _tg(
        '✅ <b>Réponse envoyée</b>' + (f'  <code>#{msg_id}</code>' if msg_id else '') + '\n'
        f'À {escape(name)} — {escape(email)}\n'
        f'<i>{escape(french_date(with_time=True))}</i>'
    )


def tg_email_failed(kind, email, msg_id=None):
    return _tg(
        f'⚠️ <b>Échec d’envoi du courriel</b> ({escape(kind)})' + (f'  <code>#{msg_id}</code>' if msg_id else '') + '\n'
        f'Destinataire : {escape(email)}\n'
        'Vérifiez RESEND_API_KEY et le domaine d’envoi dans Resend.'
    )


def tg_new_testimonial(name, role, company, rating, project_type, comment):
    stars = '★' * rating + '☆' * (5 - rating)
    who = ', '.join(x for x in (role, company) if x)
    lines = [
        '⭐ <b>Nouvel avis client à valider</b>',
        f'<i>{escape(french_date(with_time=True))}</i>',
        '',
        f'👤 <b>{escape(name)}</b>' + (f' · {escape(who)}' if who else ''),
        f'{stars}  ({rating}/5)' + (f' · {escape(project_type)}' if project_type else ''),
        '',
        f'<blockquote>{escape(truncate(comment, 1500))}</blockquote>',
        '',
        '👇 Approuvez ou refusez l’avis dans l’administration.',
    ]
    return _tg('\n'.join(lines))


def tg_stats(visits_total, visits_30, visits_7, top_pages, total, last_30, last_7, by_service, pending):
    lines = [
        '📊 <b>Statistiques Cognito Inc.</b>',
        f'<i>{escape(french_date(with_time=True))}</i>',
        '',
        '👀 <b>Visites</b>',
        f'• 7 derniers jours : <b>{visits_7}</b>',
        f'• 30 derniers jours : <b>{visits_30}</b>',
        f'• Total : {visits_total}',
    ]
    if top_pages:
        lines += ['', '🔝 <b>Pages les plus vues (30 j)</b>']
        lines += [f'• <code>{escape(path)}</code> : {n}' for path, n in top_pages]
    lines += [
        '',
        '📩 <b>Demandes de contact</b>',
        f'• 7 derniers jours : <b>{last_7}</b>',
        f'• 30 derniers jours : <b>{last_30}</b>',
        f'• Total : {total}',
    ]
    if by_service:
        lines += ['', '🔧 <b>Par service (30 j)</b>']
        lines += [f'• {escape(label)} : {n}' for label, n in by_service]
    lines += ['', f'⭐ Avis en attente de validation : <b>{pending}</b>']
    return _tg('\n'.join(lines))
