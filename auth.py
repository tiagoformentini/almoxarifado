"""
Autenticação e controle de perfis com Flask-Login.

Perfis suportados:
- "user": acesso apenas ao Painel (dashboard), em modo de leitura.
- "tecnico": acesso ao Painel, Produtos e Movimentações. Sem acesso a Usuários.
- "admin": acesso total (Painel, Produtos, Movimentações e Usuários).
"""

from functools import wraps

from flask import abort
from flask_login import LoginManager, UserMixin, login_required, current_user

import models

PERFIS_VALIDOS = ("admin", "tecnico", "user")

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.login_message = "Faça login para acessar o sistema."
login_manager.login_message_category = "erro"


class Usuario(UserMixin):
    """Wrapper do Flask-Login em torno do documento de usuário do Firestore."""

    def __init__(self, dados):
        self.id = dados["id"]
        self.nome = dados.get("nome")
        self.email = dados.get("email")
        self.perfil = dados.get("perfil", "user")

    @property
    def is_admin(self):
        return self.perfil == "admin"

    @property
    def is_tecnico(self):
        return self.perfil == "tecnico"

    @property
    def pode_operar_estoque(self):
        """Admin e técnico podem mexer em Produtos e Movimentações."""
        return self.perfil in ("admin", "tecnico")


@login_manager.user_loader
def carregar_usuario(usuario_id):
    dados = models.obter_usuario_por_id(usuario_id)
    if dados is None:
        return None
    return Usuario(dados)


def requer_perfis(*perfis_permitidos):
    """
    Fábrica de decorators: exige login E que o perfil do usuário esteja
    entre os perfis permitidos. Quem não se encaixa recebe 403.
    """
    def decorator(f):
        @wraps(f)
        @login_required
        def wrapper(*args, **kwargs):
            if current_user.perfil not in perfis_permitidos:
                abort(403)
            return f(*args, **kwargs)
        return wrapper
    return decorator


# Usuários e Perfis: somente administrador
admin_required = requer_perfis("admin")

# Produtos e Movimentações: administrador ou técnico
operacional_required = requer_perfis("admin", "tecnico")