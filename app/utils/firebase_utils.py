from app.db import db
from app.db_aemc import dbAemc, authAemc
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
        
async def check_new_messages_aemc():
    """Check for new messages in Firebase and send emails asynchronously."""
    global last_checked
    try:
        collection_ref = dbAemc.collection('messages')
        query = collection_ref.where('read', '==', False).stream()
        
        new_messages = []
        for doc in query:
            new_messages.append({"id": doc.id, **doc.to_dict()})

        if new_messages:
            print(f"Found {len(new_messages)} new messages.")
            
            for doc in new_messages:
                doc_id = doc["id"]
                print(f"Processing message {doc_id}")

                subject = doc.get('assunto')
                name = doc.get('nome')
                email = doc.get('email')
                message = doc.get('mensagem')
                
                recipients = fetch_aemc_admin_emails()

                if recipients:
                    try:
                        doc_ref = collection_ref.document(doc_id)
                        
                        body = generate_aemc_message_body(subject, name, email, message)
                        
                        tasks = [send_email_async("AEMC - Nova Mensagem", body, recipient, doc_id) 
                                for recipient in recipients]
                        
                        results = await asyncio.gather(*tasks, return_exceptions=True)
                        
                        success = all(result is True for result in results)
                        
                        doc_ref.update({
                            "read": True
                        })
                        
                    except Exception as e:
                        print(f"Error processing message {doc_id}: {e}")
                        # Marcar documento com erro
                        doc_ref.update({
                            "error_message": str(e)
                        })
    except Exception as e:
        print(f"Error while checking messages: {e}")




async def check_new_documents_aemc():
    """Check for new documents in Firebase and send emails asynchronously."""
    global last_checked
    try:
        collection_ref = dbAemc.collection('notifications')
        query = collection_ref.where('read', '==', False).stream()

        new_documents = []
        for doc in query:
            new_documents.append({"id": doc.id, **doc.to_dict()})

        if new_documents:
            print(f"Found {len(new_documents)} new documents.")

            for doc in new_documents:
                doc_id = doc["id"]
                print(f"Processing document {doc_id}")

                subject = parse_aemc_subject(doc.get('type'))
                name = doc.get('name')
                recipients = get_aemc_email_recipients(doc.get('to'))
                body = generate_aemc_email_body(doc.get('type'), doc.get('name'), doc.get('adminEmail') or None, doc.get('adminPassword') or None, doc.get('reason') or None)

                if recipients:
                    try:
                        # Primeiro atualizar o documento para evitar processamento duplicado
                        doc_ref = collection_ref.document(doc_id)
                        
                        # Criar e executar as tasks de email
                        tasks = [send_email_async(subject, body, recipient, doc_id) 
                                for recipient in recipients]
                        
                        # Aguardar o envio de todos os emails
                        results = await asyncio.gather(*tasks, return_exceptions=True)
                        
                        # Verificar se todos os emails foram enviados com sucesso
                        success = all(result is True for result in results)
                        
                        doc_ref.update({
                            "read": True
                        })
                        
                    except Exception as e:
                        print(f"Error processing document {doc_id}: {e}")
                        # Marcar documento com erro
                        doc_ref.update({
                            "error_message": str(e)
                        })
                        

        last_checked = datetime.datetime.utcnow()
    except Exception as e:
        print(f"Error while checking documents: {e}")

def get_aemc_email_recipients(to):
    if to == 'admin':
        return fetch_aemc_admin_emails()
    else:
        return [to]

def fetch_aemc_admin_emails():
    #on the collection users pick all with role admin, and the id of document is the uid of the user, so pick the email of the user
    query = dbAemc.collection('users').where('role', '==', 'admin').stream()
    #for each document in the query, pick the id and find the user on authentification and pick the email
    emails = []
    for doc in query:
        user = authAemc.get_user(doc.id)
        emails.append(user.email)
    return emails


def parse_aemc_subject(type):
    if type == 'request_received':
        return 'Pedido de Adesão Recebido - AEMC'
    elif type == 'new_request':
        return 'Novo Pedido de Adesão - AEMC'
    elif type == 'request_approved':
        return 'Pedido de Adesão Aprovado - AEMC'
    elif type == 'request_rejected':
        return 'Pedido de Adesão Rejeitado - AEMC'
    else:
        return 'AEMC'

def generate_email_body(doc_id):
    # Leia o template HTML
    dirTemplate = "app/templates/confirmation.template.html"
    with open(dirTemplate, "r", encoding='utf-8') as file:
        html_content = file.read()

    # Substitua o marcador {{ id }} pelo ID real do documento
    html_content = html_content.replace("{{ id }}", doc_id)

    return html_content

def generate_aemc_message_body(subject, name, email, message):
    dirTemplate = "app/templates/message.template.html"
    with open(dirTemplate, "r", encoding='utf-8') as file:
        html_content = file.read()
    html_content = html_content.replace("aemcSubject", subject)
    html_content = html_content.replace("aemcName", name)
    html_content = html_content.replace("aemcEmail", email)
    html_content = html_content.replace("aemcMessage", message)
    return html_content

def generate_aemc_email_body(type, name, email, password, reason):
    if type == 'request_received':
        dirTemplate = "app/templates/requestmember.template.html"
        with open(dirTemplate, "r", encoding='utf-8') as file:
            html_content = file.read()
        # Substituir o nome da empresa no template
        html_content = html_content.replace("AiTECH", name)
        return html_content
    elif type == 'new_request':
        dirTemplate = "app/templates/requestadmin.template.html"
        with open(dirTemplate, "r", encoding='utf-8') as file:
            html_content = file.read()
        # Substituir o nome da empresa no template
        html_content = html_content.replace("AiTECH", name)
        return html_content
    elif type == 'request_approved':
        dirTemplate = "app/templates/responsemember.template.html"
        with open(dirTemplate, "r", encoding='utf-8') as file:
            html_content = file.read()
        # Substituir o nome da empresa no template
        html_content = html_content.replace("AiTECH", name)
        html_content = html_content.replace("adminEmail", email)
        html_content = html_content.replace("adminPassword", password)
        return html_content
    elif type == 'request_rejected':
        dirTemplate = "app/templates/rejectmember.template.html"
        with open(dirTemplate, "r", encoding='utf-8') as file:
            html_content = file.read()
        # Substituir o nome da empresa no template
        html_content = html_content.replace("AiTECH", name)
        html_content = html_content.replace("aemcReason", reason)
        return html_content
    else:
        return 'AEMC'