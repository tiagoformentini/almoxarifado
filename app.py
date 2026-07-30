import streamlit as st
from werkzeug.security import generate_password_hash, check_password_hash

import models

st.set_page_config(page_title="Sistema de Estoque", layout="wide")


# ---------- Estado da sessão (substitui flask_login / cookies) ----------

if "usuario" not in st.session_state:
    st.session_state["usuario"] = None
if "pagina" not in st.session_state:
    st.session_state["pagina"] = "dashboard"


def usuario_logado():
    return st.session_state.get("usuario") is not None


def fazer_login(dados_usuario):
    st.session_state["usuario"] = dados_usuario


def fazer_logout():
    st.session_state["usuario"] = None
    st.session_state["pagina"] = "dashboard"


# ---------- Tela: configuração inicial (primeiro admin) ----------

def tela_configuracao_inicial():
    st.title("Configuração inicial")
    st.info("Nenhum usuário cadastrado. Crie o primeiro administrador para continuar.")

    with st.form("form_admin_inicial"):
        nome = st.text_input("Nome")
        email = st.text_input("E-mail")
        senha = st.text_input("Senha", type="password")
        confirmar_senha = st.text_input("Confirmar senha", type="password")
        enviado = st.form_submit_button("Criar administrador")

    if enviado:
        if not nome or not email or not senha:
            st.error("Preencha todos os campos.")
        elif senha != confirmar_senha:
            st.error("As senhas não coincidem.")
        elif len(senha) < 6:
            st.error("A senha deve ter pelo menos 6 caracteres.")
        else:
            senha_hash = generate_password_hash(senha)
            models.criar_usuario(nome, email, senha_hash, perfil="admin")
            st.success("Administrador criado com sucesso. Faça login para continuar.")
            st.rerun()


# ---------- Tela: login ----------

def tela_login():
    st.title("Login")

    with st.form("form_login"):
        email = st.text_input("E-mail")
        senha = st.text_input("Senha", type="password")
        enviado = st.form_submit_button("Entrar")

    if enviado:
        dados = models.obter_usuario_por_email(email)
        if dados and check_password_hash(dados.get("senha_hash", ""), senha):
            fazer_login(dados)
            st.success(f"Bem-vindo(a), {dados.get('nome')}!")
            st.rerun()
        else:
            st.error("E-mail ou senha inválidos.")


# ---------- Tela: dashboard (acessível a user, tecnico e admin) ----------

def tela_dashboard():
    st.title("Painel")

    produtos = models.listar_produtos()
    total_produtos = len(produtos)
    total_itens = sum(p.get("quantidade", 0) for p in produtos)
    estoque_baixo = [
        p for p in produtos if p.get("quantidade", 0) <= p.get("estoque_minimo", 0)
    ]
    movimentacoes = models.listar_movimentacoes(limite=8)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total de produtos", total_produtos)
    col2.metric("Total de itens em estoque", total_itens)
    col3.metric("Produtos com estoque baixo", len(estoque_baixo))

    if estoque_baixo:
        st.subheader("⚠️ Estoque baixo")
        st.table(estoque_baixo)

    st.subheader("Últimas movimentações")
    st.table(movimentacoes)

    st.subheader("Todos os produtos")
    st.dataframe(produtos, use_container_width=True)


# ---------- Telas: produtos (operacional: tecnico e admin) ----------

def tela_produtos_lista():
    st.title("Produtos")

    busca = st.text_input("Buscar", key="busca_produtos")
    produtos = models.listar_produtos(termo_busca=busca)
    st.dataframe(produtos, use_container_width=True)

    for produto in produtos:
        with st.expander(produto.get("nome", "")):
            col1, col2 = st.columns(2)
            if col1.button("Editar", key=f"editar_{produto['id']}"):
                st.session_state["produto_editar_id"] = produto["id"]
                st.session_state["pagina"] = "produtos_editar"
                st.rerun()
            if col2.button("Excluir", key=f"excluir_{produto['id']}"):
                models.excluir_produto(produto["id"])
                st.success(f"Produto '{produto.get('nome')}' excluído.")
                st.rerun()

    if st.button("+ Novo produto"):
        st.session_state["pagina"] = "produtos_novo"
        st.rerun()


def _formulario_produto(produto=None):
    produto = produto or {}
    with st.form("form_produto"):
        nome = st.text_input("Nome", value=produto.get("nome", ""))
        codigo = st.text_input("Código", value=produto.get("codigo", ""))
        categoria = st.text_input("Categoria", value=produto.get("categoria", ""))
        unidade = st.text_input("Unidade", value=produto.get("unidade", ""))
        localizacao = st.text_input("Localização", value=produto.get("localizacao", ""))
        quantidade = st.number_input(
            "Quantidade", min_value=0, value=int(produto.get("quantidade", 0) or 0)
        )
        estoque_minimo = st.number_input(
            "Estoque mínimo", min_value=0, value=int(produto.get("estoque_minimo", 0) or 0)
        )
        enviado = st.form_submit_button("Salvar")

    dados = {
        "nome": nome.strip(),
        "codigo": codigo.strip(),
        "categoria": categoria.strip(),
        "unidade": unidade.strip(),
        "localizacao": localizacao.strip(),
        "quantidade": quantidade,
        "estoque_minimo": estoque_minimo,
    }
    return enviado, dados


def tela_produtos_novo():
    st.title("Novo produto")

    enviado, dados = _formulario_produto()
    if enviado:
        if not dados["nome"] or not dados["codigo"]:
            st.error("Nome e código são obrigatórios.")
        else:
            models.criar_produto(dados)
            st.success(f"Produto '{dados['nome']}' cadastrado com sucesso.")
            st.session_state["pagina"] = "produtos"
            st.rerun()

    if st.button("Cancelar"):
        st.session_state["pagina"] = "produtos"
        st.rerun()


def tela_produtos_editar():
    produto_id = st.session_state.get("produto_editar_id")
    produto = models.obter_produto(produto_id)

    if produto is None:
        st.error("Produto não encontrado.")
        st.session_state["pagina"] = "produtos"
        st.rerun()
        return

    st.title(f"Editar produto: {produto.get('nome')}")
    enviado, dados = _formulario_produto(produto)
    if enviado:
        models.atualizar_produto(produto_id, dados)
        st.success(f"Produto '{dados['nome']}' atualizado.")
        st.session_state["pagina"] = "produtos"
        st.rerun()

    if st.button("Cancelar"):
        st.session_state["pagina"] = "produtos"
        st.rerun()


# ---------- Telas: movimentações (operacional: tecnico e admin) ----------

def tela_movimentacoes_lista():
    st.title("Movimentações")

    movimentacoes = models.listar_movimentacoes()
    st.dataframe(movimentacoes, use_container_width=True)

    if st.button("+ Nova movimentação"):
        st.session_state["pagina"] = "movimentacoes_nova"
        st.rerun()


def tela_movimentacoes_nova():
    st.title("Nova movimentação")

    produtos = models.listar_produtos()
    nomes_produtos = {p["id"]: p.get("nome", p["id"]) for p in produtos}

    with st.form("form_movimentacao"):
        produto_id = st.selectbox(
            "Produto",
            options=list(nomes_produtos.keys()),
            format_func=lambda pid: nomes_produtos.get(pid, pid),
        )
        tipo = st.selectbox("Tipo", options=["entrada", "saida"])
        quantidade = st.number_input("Quantidade", min_value=1, step=1)
        responsavel = st.text_input("Responsável")
        observacao = st.text_area("Observação")
        enviado = st.form_submit_button("Registrar")

    if enviado:
        try:
            quantidade_int = int(quantidade)
            if quantidade_int <= 0:
                raise ValueError("A quantidade deve ser maior que zero.")
            models.registrar_movimentacao(
                produto_id, tipo, quantidade_int, responsavel.strip(), observacao.strip()
            )
            st.success("Movimentação registrada com sucesso.")
            st.session_state["pagina"] = "movimentacoes"
            st.rerun()
        except ValueError as erro:
            st.error(str(erro))

    if st.button("Cancelar"):
        st.session_state["pagina"] = "movimentacoes"
        st.rerun()


# ---------- Telas: usuários / perfis (somente admin) ----------

def tela_usuarios_lista():
    st.title("Usuários")

    usuarios = models.listar_usuarios()
    st.dataframe(usuarios, use_container_width=True)

    usuario_atual = st.session_state["usuario"]
    perfis_disponiveis = ["admin", "tecnico", "user"]

    for usuario in usuarios:
        with st.expander(usuario.get("nome", "")):
            st.write(f"E-mail: {usuario.get('email')}")
            st.write(f"Perfil atual: {usuario.get('perfil')}")

            perfil_atual_usuario = usuario.get("perfil", "user")
            indice_atual = (
                perfis_disponiveis.index(perfil_atual_usuario)
                if perfil_atual_usuario in perfis_disponiveis
                else 2
            )
            novo_perfil = st.selectbox(
                "Alterar perfil",
                options=perfis_disponiveis,
                index=indice_atual,
                key=f"perfil_{usuario['id']}",
            )
            if st.button("Salvar perfil", key=f"salvar_perfil_{usuario['id']}"):
                if usuario["id"] == usuario_atual["id"] and novo_perfil != "admin":
                    st.error("Você não pode remover seu próprio acesso de administrador.")
                else:
                    models.atualizar_perfil_usuario(usuario["id"], novo_perfil)
                    st.success("Perfil atualizado com sucesso.")
                    st.rerun()

            if st.button("Excluir usuário", key=f"excluir_usuario_{usuario['id']}"):
                if usuario["id"] == usuario_atual["id"]:
                    st.error("Você não pode excluir o seu próprio usuário.")
                else:
                    models.excluir_usuario(usuario["id"])
                    st.success("Usuário excluído.")
                    st.rerun()

    if st.button("+ Novo usuário"):
        st.session_state["pagina"] = "usuarios_novo"
        st.rerun()


def tela_usuarios_novo():
    st.title("Novo usuário")

    with st.form("form_usuario"):
        nome = st.text_input("Nome")
        email = st.text_input("E-mail")
        senha = st.text_input("Senha", type="password")
        perfil = st.selectbox("Perfil", options=["admin", "tecnico", "user"])
        enviado = st.form_submit_button("Criar")

    if enviado:
        if not nome or not email or not senha:
            st.error("Preencha todos os campos.")
        elif len(senha) < 6:
            st.error("A senha deve ter pelo menos 6 caracteres.")
        elif models.obter_usuario_por_email(email):
            st.error("Já existe um usuário cadastrado com este e-mail.")
        else:
            senha_hash = generate_password_hash(senha)
            models.criar_usuario(nome.strip(), email.strip(), senha_hash, perfil)
            st.success(f"Usuário '{nome}' criado com sucesso.")
            st.session_state["pagina"] = "usuarios"
            st.rerun()

    if st.button("Cancelar"):
        st.session_state["pagina"] = "usuarios"
        st.rerun()


# ---------- Navegação principal (substitui as rotas do Flask) ----------

PERFIS_OPERACIONAL = {"admin", "tecnico"}
PERFIS_ADMIN = {"admin"}

MENU = [
    ("dashboard", "Painel", None),
    ("produtos", "Produtos", PERFIS_OPERACIONAL),
    ("movimentacoes", "Movimentações", PERFIS_OPERACIONAL),
    ("usuarios", "Usuários", PERFIS_ADMIN),
]

PAGINAS_OPERACIONAL = {"produtos", "produtos_novo", "produtos_editar", "movimentacoes", "movimentacoes_nova"}
PAGINAS_ADMIN = {"usuarios", "usuarios_novo"}

ROTAS = {
    "dashboard": tela_dashboard,
    "produtos": tela_produtos_lista,
    "produtos_novo": tela_produtos_novo,
    "produtos_editar": tela_produtos_editar,
    "movimentacoes": tela_movimentacoes_lista,
    "movimentacoes_nova": tela_movimentacoes_nova,
    "usuarios": tela_usuarios_lista,
    "usuarios_novo": tela_usuarios_novo,
}


def main():
    # Equivalente ao before_request: força criação do primeiro admin
    if not models.existe_algum_usuario():
        tela_configuracao_inicial()
        return

    if not usuario_logado():
        tela_login()
        return

    usuario = st.session_state["usuario"]

    with st.sidebar:
        st.write(f"Logado como **{usuario.get('nome')}** ({usuario.get('perfil')})")
        for chave, rotulo, perfis_permitidos in MENU:
            if perfis_permitidos is None or usuario.get("perfil") in perfis_permitidos:
                if st.button(rotulo, key=f"menu_{chave}", use_container_width=True):
                    st.session_state["pagina"] = chave
                    st.rerun()
        st.divider()
        if st.button("Sair", use_container_width=True):
            fazer_logout()
            st.rerun()

    pagina = st.session_state.get("pagina", "dashboard")

    # Equivalente aos decorators admin_required / operacional_required
    if pagina in PAGINAS_OPERACIONAL and usuario.get("perfil") not in PERFIS_OPERACIONAL:
        st.error("Acesso negado: você não tem permissão para acessar esta página.")
        pagina = "dashboard"
    if pagina in PAGINAS_ADMIN and usuario.get("perfil") not in PERFIS_ADMIN:
        st.error("Acesso negado: você não tem permissão para acessar esta página.")
        pagina = "dashboard"

    ROTAS.get(pagina, tela_dashboard)()


if __name__ == "__main__":
    main()
