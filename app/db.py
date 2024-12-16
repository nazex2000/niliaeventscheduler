import firebase_admin
from firebase_admin import credentials, firestore

# Inicializar o Firebase
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()