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

        # Add mother's emails if available
        if mother_email := doc_data.get('filiation', {}).get('mother', {}).get('email'):
            recipients.append(mother_email)

    elif education_guardian == 'father':
        # Add only father's emails
        if father_email := doc_data.get('filiation', {}).get('father', {}).get('email'):
            recipients.append(father_email)

    elif education_guardian == 'mother':
        # Add only mother's emails
        if mother_email := doc_data.get('filiation', {}).get('mother', {}).get('email'):
            recipients.append(mother_email)

    elif education_guardian == 'other':
        # Add guardian's emails
        if guardian_email := doc_data.get('guardian', {}).get('email'):
            recipients.append(guardian_email)

    # Remove any empty strings or None values and remove duplicates
    recipients = list(set(filter(None, recipients)))

    return recipients


async def check_new_documents():
    """Check for new documents in Firebase and send emails asynchronously."""
    global last_checked
    try:
        collection_ref = db.collection(settings.firebase_collection)
        query = collection_ref.where('notification', '==', []).stream()

        new_documents = []
        for doc in query:
            new_documents.append({"id": doc.id, **doc.to_dict()})

        if new_documents:
            print(f"Found {len(new_documents)} new documents.")
            
            for doc in new_documents:
                doc_id = doc["id"]
                print(f"Processing document {doc_id}")
                
                subject = "Confirmação de Receção de Inscrição"
                body = generate_email_body(doc_id)

                recipients = get_email_recipients(doc)
                print(f"Recipients for document {doc_id}: {recipients}")

                if recipients:
                    try:
                        # Primeiro atualizar o documento para evitar processamento duplicado
                        doc_ref = collection_ref.document(doc_id)
                        doc_ref.update({
                            "notification": [datetime.datetime.utcnow()],
                            "email_status": "processing"
                        })
                        
                        # Criar e executar as tasks de email
                        tasks = [send_email_async(subject, body, recipient, doc_id) 
                                for recipient in recipients]
                        
                        # Aguardar o envio de todos os emails
                        results = await asyncio.gather(*tasks, return_exceptions=True)
                        
                        # Verificar se todos os emails foram enviados com sucesso
                        success = all(result is True for result in results)
                        
                        # Atualizar status final
                        doc_ref.update({
                            "email_status": "completed" if success else "partial_failure",
                            "email_sent_at": datetime.datetime.utcnow()
                        })
                        
                    except Exception as e:
                        print(f"Error processing document {doc_id}: {e}")
                        # Marcar documento com erro
                        doc_ref.update({
                            "email_status": "failed",
                            "error_message": str(e)
                        })

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