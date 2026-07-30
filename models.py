"""
Camada de acesso a dados: coleções 'produtos' e 'movimentacoes' no Firestore.
"""

from datetime import datetime, timezone
from google.cloud.firestore_v1 import Increment
from firebase_config import get_db

PRODUTOS_COL = "produtos"
MOVIMENTACOES_COL = "movimentacoes"
USUARIOS_COL = "usuarios"


# ---------- Produtos ----------

def listar_produtos(termo_busca=None):
    db = get_db()
    docs = db.collection(PRODUTOS_COL).stream()
    produtos = []
    for doc in docs:
        item = doc.to_dict()
        item["id"] = doc.id
        produtos.append(item)

    produtos.sort(key=lambda p: (p.get("nome") or "").lower())

    if termo_busca:
        termo = termo_busca.lower().strip()
        produtos = [
            p for p in produtos
            if termo in (p.get("nome") or "").lower()
            or termo in (p.get("codigo") or "").lower()
            or termo in (p.get("categoria") or "").lower()
        ]
    return produtos


def obter_produto(produto_id):
    db = get_db()
    doc = db.collection(PRODUTOS_COL).document(produto_id).get()
    if not doc.exists:
        return None
    item = doc.to_dict()
    item["id"] = doc.id
    return item


def criar_produto(dados):
    db = get_db()
    dados["quantidade"] = int(dados.get("quantidade") or 0)
    dados["estoque_minimo"] = int(dados.get("estoque_minimo") or 0)
    dados["criado_em"] = datetime.now(timezone.utc)
    ref = db.collection(PRODUTOS_COL).document()
    ref.set(dados)
    return ref.id


def atualizar_produto(produto_id, dados):
    db = get_db()
    dados["quantidade"] = int(dados.get("quantidade") or 0)
    dados["estoque_minimo"] = int(dados.get("estoque_minimo") or 0)
    db.collection(PRODUTOS_COL).document(produto_id).update(dados)


def excluir_produto(produto_id):
    db = get_db()
    db.collection(PRODUTOS_COL).document(produto_id).delete()


# ---------- Movimentações (entradas / saídas) ----------

def listar_movimentacoes(limite=100):
    db = get_db()
    docs = (
        db.collection(MOVIMENTACOES_COL)
        .order_by("data", direction="DESCENDING")
        .limit(limite)
        .stream()
    )
    movs = []
    for doc in docs:
        item = doc.to_dict()
        item["id"] = doc.id
        movs.append(item)
    return movs


def registrar_movimentacao(produto_id, tipo, quantidade, responsavel, observacao=""):
    """
    Registra uma movimentação (entrada ou saída) e ajusta a quantidade do
    produto de forma atômica usando Increment do Firestore.
    """
    db = get_db()
    produto_ref = db.collection(PRODUTOS_COL).document(produto_id)
    produto = produto_ref.get()
    if not produto.exists:
        raise ValueError("Produto não encontrado.")

    produto_data = produto.to_dict()
    quantidade = int(quantidade)

    if tipo == "saida" and produto_data.get("quantidade", 0) < quantidade:
        raise ValueError(
            f"Estoque insuficiente. Disponível: {produto_data.get('quantidade', 0)}."
        )

    delta = quantidade if tipo == "entrada" else -quantidade
    produto_ref.update({"quantidade": Increment(delta)})

    mov_ref = db.collection(MOVIMENTACOES_COL).document()
    mov_ref.set({
        "produto_id": produto_id,
        "produto_nome": produto_data.get("nome"),
        "produto_codigo": produto_data.get("codigo"),
        "tipo": tipo,
        "quantidade": quantidade,
        "responsavel": responsavel,
        "observacao": observacao,
        "data": datetime.now(timezone.utc),
    })
    return mov_ref.id


def produtos_estoque_baixo():
    produtos = listar_produtos()
    return [
        p for p in produtos
        if p.get("quantidade", 0) <= p.get("estoque_minimo", 0)
    ]


# ---------- Usuários (autenticação e perfis) ----------
# Perfis suportados: "admin" (acesso total) e "user" (acesso somente ao painel)

def existe_algum_usuario():
    db = get_db()
    docs = db.collection(USUARIOS_COL).limit(1).stream()
    return any(True for _ in docs)


def criar_usuario(nome, email, senha_hash, perfil="user"):
    if perfil not in ("admin", "tecnico", "user"):
        perfil = "user"
    db = get_db()
    ref = db.collection(USUARIOS_COL).document()
    ref.set({
        "nome": nome.strip(),
        "email": email.strip().lower(),
        "senha_hash": senha_hash,
        "perfil": perfil,
        "criado_em": datetime.now(timezone.utc),
    })
    return ref.id


def obter_usuario_por_email(email):
    db = get_db()
    docs = (
        db.collection(USUARIOS_COL)
        .where("email", "==", email.strip().lower())
        .limit(1)
        .stream()
    )
    for doc in docs:
        item = doc.to_dict()
        item["id"] = doc.id
        return item
    return None


def obter_usuario_por_id(usuario_id):
    db = get_db()
    doc = db.collection(USUARIOS_COL).document(usuario_id).get()
    if not doc.exists:
        return None
    item = doc.to_dict()
    item["id"] = doc.id
    return item


def listar_usuarios():
    db = get_db()
    docs = db.collection(USUARIOS_COL).stream()
    usuarios = []
    for doc in docs:
        item = doc.to_dict()
        item["id"] = doc.id
        usuarios.append(item)
    usuarios.sort(key=lambda u: (u.get("nome") or "").lower())
    return usuarios


def atualizar_perfil_usuario(usuario_id, perfil):
    if perfil not in ("admin", "tecnico", "user"):
        raise ValueError("Perfil inválido.")
    db = get_db()
    db.collection(USUARIOS_COL).document(usuario_id).update({"perfil": perfil})


def excluir_usuario(usuario_id):
    db = get_db()
    db.collection(USUARIOS_COL).document(usuario_id).delete()
