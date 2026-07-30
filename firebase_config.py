"""
Inicialização do Firebase Admin SDK (Firestore).

Este backend em Python usa o Firebase ADMIN SDK, que é diferente do
Firebase Web SDK (usado em JavaScript no navegador). O Admin SDK precisa
de um arquivo de credenciais de "conta de serviço" (service account),
baixado no Console do Firebase, e NÃO da apiKey usada no frontend web.

Como gerar o arquivo:
1. Acesse https://console.firebase.google.com/
2. Selecione o projeto "almoxarifado-81ce6"
3. Vá em Configurações do projeto (engrenagem) > Contas de serviço
4. Clique em "Gerar nova chave privada"
5. Salve o arquivo baixado como "serviceAccountKey.json" na raiz deste
   projeto (mesma pasta do app.py). NUNCA compartilhe ou versione esse
   arquivo (adicione-o ao .gitignore).
"""

import os
import firebase_admin
from firebase_admin import credentials, firestore

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CRED_PATH = os.path.join(BASE_DIR, "almoxarifado-81ce6-firebase-adminsdk-fbsvc-1ea48a562d.json")

_db = None


def get_db():
    """Retorna o cliente do Firestore, inicializando o app apenas uma vez."""
    global _db
    if _db is None:
        if not os.path.exists(CRED_PATH):
            raise FileNotFoundError(
                "Arquivo 'serviceAccountKey.json' não encontrado em "
                f"{CRED_PATH}. Veja as instruções no topo deste arquivo "
                "(firebase_config.py) para gerar sua credencial no "
                "Console do Firebase."
            )
        cred = credentials.Certificate(CRED_PATH)
        firebase_admin.initialize_app(cred, {
            "projectId": "almoxarifado-81ce6",
        })
        _db = firestore.client()
    return _db
