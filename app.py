from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import (
    login_user, logout_user, login_required, current_user,
)
from werkzeug.security import generate_password_hash, check_password_hash

import models
from auth import login_manager, admin_required, operacional_required, Usuario

app = Flask(__name__)
app.secret_key = "troque-esta-chave-por-uma-secreta-em-producao"

login_manager.init_app(app)


# ---------- Configuração inicial / autenticação ----------

@app.before_request
def exigir_configuracao_inicial():
    """
    Se o sistema ainda não tem nenhum usuário cadastrado, força a criação
    do primeiro administrador antes de liberar qualquer outra tela.
    """
    if request.endpoint in ("registrar_admin_inicial", "static"):
        return
    if not models.existe_algum_usuario():
        return redirect(url_for("registrar_admin_inicial"))


@app.route("/configuracao-inicial", methods=["GET", "POST"])
def registrar_admin_inicial():
    # Se já existe algum usuário, essa tela não deve mais ser usada.
    if models.existe_algum_usuario():
        return redirect(url_for("login"))

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip()
        senha = request.form.get("senha", "")
        confirmar_senha = request.form.get("confirmar_senha", "")

        if not nome or not email or not senha:
            flash("Preencha todos os campos.", "erro")
        elif senha != confirmar_senha:
            flash("As senhas não coincidem.", "erro")
        elif len(senha) < 6:
            flash("A senha deve ter pelo menos 6 caracteres.", "erro")
        else:
            senha_hash = generate_password_hash(senha)
            models.criar_usuario(nome, email, senha_hash, perfil="admin")
            flash("Administrador criado com sucesso. Faça login para continuar.", "sucesso")
            return redirect(url_for("login"))

    return render_template("registrar_admin_inicial.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        senha = request.form.get("senha", "")
        dados = models.obter_usuario_por_email(email)

        if dados and check_password_hash(dados.get("senha_hash", ""), senha):
            login_user(Usuario(dados))
            flash(f"Bem-vindo(a), {dados.get('nome')}!", "sucesso")
            proxima = request.args.get("next")
            return redirect(proxima or url_for("dashboard"))

        flash("E-mail ou senha inválidos.", "erro")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Você saiu do sistema.", "sucesso")
    return redirect(url_for("login"))


@app.errorhandler(403)
def acesso_negado(erro):
    return render_template("403.html"), 403


# ---------- Painel (acessível a user, técncio e admin) ----------

@app.route("/")
@login_required
def dashboard():
    produtos = models.listar_produtos()
    total_produtos = len(produtos)
    total_itens = sum(p.get("quantidade", 0) for p in produtos)
    estoque_baixo = [
        p for p in produtos if p.get("quantidade", 0) <= p.get("estoque_minimo", 0)
    ]
    movimentacoes = models.listar_movimentacoes(limite=8)
    return render_template(
        "dashboard.html",
        total_produtos=total_produtos,
        total_itens=total_itens,
        estoque_baixo=estoque_baixo,
        movimentacoes=movimentacoes,
        produtos=produtos,          # <-- adicionado: lista completa de produtos
    )


# ---------- Produtos (somente técnico e admin) ----------

@app.route("/produtos")
@operacional_required
def produtos_lista():
    busca = request.args.get("q", "")
    produtos = models.listar_produtos(termo_busca=busca)
    return render_template("produtos.html", produtos=produtos, busca=busca)


@app.route("/produtos/novo", methods=["GET", "POST"])
@operacional_required
def produtos_novo():
    if request.method == "POST":
        dados = {
            "nome": request.form.get("nome", "").strip(),
            "codigo": request.form.get("codigo", "").strip(),
            "categoria": request.form.get("categoria", "").strip(),
            "unidade": request.form.get("unidade", "").strip(),
            "localizacao": request.form.get("localizacao", "").strip(),
            "quantidade": request.form.get("quantidade", 0),
            "estoque_minimo": request.form.get("estoque_minimo", 0),
        }
        if not dados["nome"] or not dados["codigo"]:
            flash("Nome e código são obrigatórios.", "erro")
            return render_template("produto_form.html", produto=dados, modo="novo")
        models.criar_produto(dados)
        flash(f"Produto '{dados['nome']}' cadastrado com sucesso.", "sucesso")
        return redirect(url_for("produtos_lista"))
    return render_template("produto_form.html", produto={}, modo="novo")


@app.route("/produtos/<produto_id>/editar", methods=["GET", "POST"])
@operacional_required
def produtos_editar(produto_id):
    produto = models.obter_produto(produto_id)
    if produto is None:
        flash("Produto não encontrado.", "erro")
        return redirect(url_for("produtos_lista"))

    if request.method == "POST":
        dados = {
            "nome": request.form.get("nome", "").strip(),
            "codigo": request.form.get("codigo", "").strip(),
            "categoria": request.form.get("categoria", "").strip(),
            "unidade": request.form.get("unidade", "").strip(),
            "localizacao": request.form.get("localizacao", "").strip(),
            "quantidade": request.form.get("quantidade", 0),
            "estoque_minimo": request.form.get("estoque_minimo", 0),
        }
        models.atualizar_produto(produto_id, dados)
        flash(f"Produto '{dados['nome']}' atualizado.", "sucesso")
        return redirect(url_for("produtos_lista"))

    return render_template("produto_form.html", produto=produto, modo="editar")


@app.route("/produtos/<produto_id>/excluir", methods=["POST"])
@operacional_required
def produtos_excluir(produto_id):
    produto = models.obter_produto(produto_id)
    models.excluir_produto(produto_id)
    nome = produto.get("nome") if produto else produto_id
    flash(f"Produto '{nome}' excluído.", "sucesso")
    return redirect(url_for("produtos_lista"))


# ---------- Movimentações (somente admin) ----------

@app.route("/movimentacoes")
@operacional_required
def movimentacoes_lista():
    movimentacoes = models.listar_movimentacoes()
    return render_template("movimentacoes.html", movimentacoes=movimentacoes)


@app.route("/movimentacoes/nova", methods=["GET", "POST"])
@operacional_required
def movimentacoes_nova():
    produtos = models.listar_produtos()

    if request.method == "POST":
        produto_id = request.form.get("produto_id")
        tipo = request.form.get("tipo")
        quantidade = request.form.get("quantidade")
        responsavel = request.form.get("responsavel", "").strip()
        observacao = request.form.get("observacao", "").strip()

        try:
            quantidade_int = int(quantidade)
            if quantidade_int <= 0:
                raise ValueError("A quantidade deve ser maior que zero.")
            models.registrar_movimentacao(
                produto_id, tipo, quantidade_int, responsavel, observacao
            )
            flash("Movimentação registrada com sucesso.", "sucesso")
            return redirect(url_for("movimentacoes_lista"))
        except ValueError as erro:
            flash(str(erro), "erro")
            return render_template(
                "movimentacao_form.html", produtos=produtos, form=request.form
            )

    return render_template("movimentacao_form.html", produtos=produtos, form={})


# ---------- Usuários / perfis (somente admin) ----------

@app.route("/usuarios")
@admin_required
def usuarios_lista():
    usuarios = models.listar_usuarios()
    return render_template("usuarios.html", usuarios=usuarios)


@app.route("/usuarios/novo", methods=["GET", "POST"])
@admin_required
def usuarios_novo():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip()
        senha = request.form.get("senha", "")
        perfil = request.form.get("perfil", "user")
        if perfil not in ("admin", "tecnico", "user"):
            perfil = "user"

        if not nome or not email or not senha:
            flash("Preencha todos os campos.", "erro")
            return render_template("usuario_form.html", form=request.form)
        if len(senha) < 6:
            flash("A senha deve ter pelo menos 6 caracteres.", "erro")
            return render_template("usuario_form.html", form=request.form)
        if models.obter_usuario_por_email(email):
            flash("Já existe um usuário cadastrado com este e-mail.", "erro")
            return render_template("usuario_form.html", form=request.form)

        senha_hash = generate_password_hash(senha)
        models.criar_usuario(nome, email, senha_hash, perfil)
        flash(f"Usuário '{nome}' criado com sucesso.", "sucesso")
        return redirect(url_for("usuarios_lista"))

    return render_template("usuario_form.html", form={})


@app.route("/usuarios/<usuario_id>/alterar-perfil", methods=["POST"])
@admin_required
def usuarios_alterar_perfil(usuario_id):
    novo_perfil = request.form.get("perfil")
    if novo_perfil not in ("admin", "tecnico", "user"):
        flash("Perfil inválido.", "erro")
        return redirect(url_for("usuarios_lista"))

    if usuario_id == current_user.id and novo_perfil != "admin":
        flash("Você não pode remover seu próprio acesso de administrador.", "erro")
        return redirect(url_for("usuarios_lista"))

    models.atualizar_perfil_usuario(usuario_id, novo_perfil)
    flash("Perfil atualizado com sucesso.", "sucesso")
    return redirect(url_for("usuarios_lista"))


@app.route("/usuarios/<usuario_id>/excluir", methods=["POST"])
@admin_required
def usuarios_excluir(usuario_id):
    if usuario_id == current_user.id:
        flash("Você não pode excluir o seu próprio usuário.", "erro")
        return redirect(url_for("usuarios_lista"))
    models.excluir_usuario(usuario_id)
    flash("Usuário excluído.", "sucesso")
    return redirect(url_for("usuarios_lista"))


if __name__ == "__main__":
    app.run(

        host="0.0.0.0",

        port=5000,

        debug=True

    )
