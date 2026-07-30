# almoxarifado
Sistema web para controle de estoque de almoxarifado: cadastro de produtos,
controle de quantidade, estoque mínimo e histórico de movimentações
(entradas e saídas), usando o **Firestore** (banco NoSQL do Firebase) como
banco de dados.

## ⚠️ Importante sobre as credenciais do Firebase

Os dados que você tem (`apiKey`, `authDomain`, etc.) são a configuração do
**Firebase Web SDK**, usada em páginas JavaScript no navegador. Um backend
em **Python não usa esse tipo de credencial**. Ele usa o **Firebase Admin
SDK**, que exige um arquivo de **conta de serviço** (service account),
com permissões administrativas sobre o banco.

### Como gerar o arquivo de credenciais:

1. Acesse https://console.firebase.google.com/
2. Abra o projeto **almoxarifado-81ce6**
3. Clique na engrenagem (⚙️) ao lado de "Visão geral do projeto" → **Configurações do projeto**
4. Vá na aba **Contas de serviço**
5. Clique em **Gerar nova chave privada** → confirme o download
6. Renomeie o arquivo baixado para `serviceAccountKey.json`
7. Coloque esse arquivo na raiz do projeto (mesma pasta do `app.py`)

🔒 **Nunca** compartilhe esse arquivo nem o envie para repositórios públicos
(Git, GitHub etc). Ele dá acesso total de leitura/escrita ao seu banco.
Adicione-o ao `.gitignore`.

### Habilitar o Firestore

No Console do Firebase, vá em **Firestore Database** → **Criar banco de
dados** (se ainda não existir), e escolha o modo de produção ou teste
conforme sua necessidade. As coleções `produtos` e `movimentacoes` são
criadas automaticamente pelo próprio sistema no primeiro uso — não é
preciso criá-las manualmente.

## Instalação

```bash
# 1. Crie um ambiente virtual (recomendado)
python -m venv venv
source venv/bin/activate      # Linux/Mac
venv\Scripts\activate         # Windows

# 2. Instale as dependências
pip install -r requirements.txt

# 3. Coloque o arquivo serviceAccountKey.json na raiz do projeto
#    (veja instruções acima)

# 4. Rode a aplicação
python app.py
```

Acesse: http://localhost:5000

## Estrutura do projeto

```
almoxarifado/
├── app.py                        # Rotas Flask (login, dashboard, produtos, movimentações, usuários)
├── auth.py                       # Flask-Login: classe Usuario, decorator admin_required
├── models.py                     # Funções de acesso ao Firestore (produtos, movimentações, usuários)
├── firebase_config.py            # Inicialização do Firebase Admin SDK
├── requirements.txt
├── serviceAccountKey.json        # (você precisa adicionar este arquivo)
├── static/css/style.css
└── templates/
    ├── base.html
    ├── login.html
    ├── registrar_admin_inicial.html
    ├── dashboard.html
    ├── produtos.html
    ├── produto_form.html
    ├── movimentacoes.html
    ├── movimentacao_form.html
    ├── usuarios.html
    ├── usuario_form.html
    └── 403.html
```

## Primeiro acesso

Ao rodar a aplicação pela primeira vez (sem nenhum usuário cadastrado no
Firestore), o sistema redireciona automaticamente para a tela de
**configuração inicial**, onde você cria a primeira conta — que já nasce
como **administrador**. Depois disso, o login normal (`/login`) passa a
ser exigido para tudo.

## Perfis de acesso

| Perfil | O que enxerga |
|---|---|
| **user** (usuário comum) | Apenas o **Painel** (dashboard), em modo leitura. Tentar acessar Produtos, Movimentações ou Usuários resulta em página de acesso negado (403). |
| **admin** (administrador) | Acesso total: Painel, Produtos, Movimentações e gestão de Usuários (criar, promover/rebaixar perfil, excluir). |

Somente administradores podem cadastrar novos usuários e escolher o
perfil (`user` ou `admin`) em **Usuários → Novo usuário**. Um
administrador não consegue excluir a própria conta nem remover o próprio
acesso de administrador (para evitar ficar todo mundo trancado para
fora do sistema).

As senhas são armazenadas com hash (`werkzeug.security`), nunca em texto
puro — nem no Firestore, nem em qualquer lugar do código.

## Funcionalidades

- **Login / Logout** com sessão via Flask-Login.
- **Painel (dashboard)**: total de produtos, total de itens em estoque,
  alerta de itens com estoque baixo, últimas movimentações. Acessível a
  ambos os perfis.
- **Produtos** *(somente admin)*: cadastrar, listar (com busca), editar e
  excluir. Cada produto tem nome, código/SKU, categoria, unidade,
  quantidade, estoque mínimo e localização física.
- **Movimentações** *(somente admin)*: registrar entrada ou saída de um
  produto. A quantidade do produto é atualizada de forma atômica no
  Firestore (usando `Increment`), e saídas são bloqueadas se não houver
  estoque suficiente.
- **Usuários** *(somente admin)*: criar novos usuários, alternar o perfil
  entre `user` e `admin`, e excluir usuários.

## Modelo de dados no Firestore

**Coleção `produtos`**
| Campo | Tipo | Descrição |
|---|---|---|
| nome | string | Nome do item |
| codigo | string | Código/SKU |
| categoria | string | Categoria do item |
| unidade | string | Unidade de medida (un, kg, caixa...) |
| quantidade | number | Quantidade atual em estoque |
| estoque_minimo | number | Quantidade mínima antes do alerta |
| localizacao | string | Localização física (prateleira, corredor...) |
| criado_em | timestamp | Data de criação |

**Coleção `movimentacoes`**
| Campo | Tipo | Descrição |
|---|---|---|
| produto_id | string | Referência ao produto |
| produto_nome / produto_codigo | string | Cópia para exibição no histórico |
| tipo | string | `entrada` ou `saida` |
| quantidade | number | Quantidade movimentada |
| responsavel | string | Quem realizou a movimentação |
| observacao | string | Observação opcional |
| data | timestamp | Data/hora da movimentação |

**Coleção `usuarios`**
| Campo | Tipo | Descrição |
|---|---|---|
| nome | string | Nome completo |
| email | string | E-mail (usado no login) |
| senha_hash | string | Hash da senha (nunca em texto puro) |
| perfil | string | `admin` ou `user` |
| criado_em | timestamp | Data de criação |

## Próximos passos sugeridos

- Trocar `app.secret_key` por um valor secreto forte e vindo de variável
  de ambiente antes de colocar em produção.
- Adicionar exportação de relatórios (CSV/PDF).
- Adicionar paginação na listagem de produtos para catálogos grandes.
- Adicionar recuperação de senha por e-mail.

