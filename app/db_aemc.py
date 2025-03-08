import firebase_admin
from firebase_admin import credentials, firestore, auth

# Inicializar o Firebase AEMC com um nome específico
cred = credentials.Certificate("serviceAccountKeyAemc.json")
aemc_app = firebase_admin.initialize_app(cred, name='aemc-app')
dbAemc = firestore.client(app=aemc_app)
authAemc = auth.Client(app=aemc_app)