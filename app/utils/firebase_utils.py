from app.db import db
from app.smtp_service import send_email_async
from app.config import settings
import datetime
import asyncio

# Variável global para controlar o último timestamp verificado
last_checked = datetime.datetime.utcnow()


def get_email_recipients(doc_data):
    """Get email recipients based on education guardian and available information."""
    recipients = []

    education_guardian = doc_data.get('educationGuardian')

    if education_guardian == 'parents':
        # Add father's emails if available
        if father_email := doc_data.get('filiation', {}).get('father', {}).get('email'):
            recipients.append(father_email)
        if father_alt_email := doc_data.get('filiation', {}).get('father', {}).get('alternativeEmail'):
            recipients.append(father_alt_email)

        # Add mother's emails if available
        if mother_email := doc_data.get('filiation', {}).get('mother', {}).get('email'):
            recipients.append(mother_email)
        if mother_alt_email := doc_data.get('filiation', {}).get('mother', {}).get('alternativeEmail'):
            recipients.append(mother_alt_email)

    elif education_guardian == 'father':
        # Add only father's emails
        if father_email := doc_data.get('filiation', {}).get('father', {}).get('email'):
            recipients.append(father_email)
        if father_alt_email := doc_data.get('filiation', {}).get('father', {}).get('alternativeEmail'):
            recipients.append(father_alt_email)

    elif education_guardian == 'mother':
        # Add only mother's emails
        if mother_email := doc_data.get('filiation', {}).get('mother', {}).get('email'):
            recipients.append(mother_email)
        if mother_alt_email := doc_data.get('filiation', {}).get('mother', {}).get('alternativeEmail'):
            recipients.append(mother_alt_email)

    elif education_guardian == 'other':
        # Add guardian's emails
        if guardian_email := doc_data.get('guardian', {}).get('email'):
            recipients.append(guardian_email)
        if guardian_alt_email := doc_data.get('guardian', {}).get('alternativeEmail'):
            recipients.append(guardian_alt_email)

    # Remove any empty strings or None values and remove duplicates
    recipients = list(set(filter(None, recipients)))

    return recipients


async def check_new_documents():
    """Check for new documents in Firebase and send emails asynchronously."""
    global last_checked
    try:
        # Buscar documentos criados após o último timestamp
        collection_ref = db.collection(settings.firebase_collection)
        # filtra para documentos com campo notification array vazio
        query = collection_ref.where('notification', '==', []).stream()

        # Coletar os novos documentos e seus IDs
        new_documents = []
        for doc in query:
            new_documents.append({"id": doc.id, **doc.to_dict()})

        if new_documents:
            print(f"Found {len(new_documents)} new documents.")
            # Enviar e-mails de forma assíncrona para os novos documentos
            tasks = []
            for doc in new_documents:
                subject = "Confirmação de Receção de Inscrição"
                body = generate_email_body(doc["id"])

                # Get recipients for this document
                recipients = get_email_recipients(doc)

                if recipients:
                    for recipient in recipients:
                        tasks.append(send_email_async(subject, body, recipient))

                    # Atualizar o documento no Firebase para marcar como notificado
                    doc_ref = collection_ref.document(doc["id"])
                    doc_ref.update({"notification": [datetime.datetime.utcnow()]})

            # Executar todas as tarefas de envio de e-mail
            if tasks:
                await asyncio.gather(*tasks)

        # Atualizar o último timestamp verificado
        last_checked = datetime.datetime.utcnow()
    except Exception as e:
        print(f"Error while checking documents: {e}")


def generate_email_body(doc_id):
    # Leia o template HTML
    dirTemplate = "app/templates/confirmation.template.html"
    with open(dirTemplate, "r", encoding='utf-8') as file:
        html_content = file.read()

    # Substitua o marcador {{ id }} pelo ID real do documento
    html_content = html_content.replace("{{ id }}", doc_id)

    return html_content