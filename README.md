# Raízes do Nordeste — API Back-End

Sistema de gestão para rede de lanchonetes nordestinas com múltiplos canais de atendimento.  
Projeto Multidisciplinar — Trilha Back-End | UNINTER 2026

---

## Requisitos de ambiente

| Ferramenta | Versão mínima |
|------------|---------------|
| Python     | 3.10+         |
| pip        | 22+           |

Banco de dados: **SQLite** (embutido no Python, sem instalação separada).

---

## Instalação e execução

### 1. Clonar o repositório

```bash
git clone <URL_DO_REPOSITORIO>
cd raizes_nordeste
```

### 2. Criar ambiente virtual

```bash
python -m venv venv

# Linux/Mac
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Configurar variáveis de ambiente

```bash
cp .env.example .env
# Edite .env se necessário (para desenvolvimento, os valores padrão funcionam)
```

### 4. Instalar dependências

```bash
pip install -r requirements.txt
```

### 5. Popular o banco com dados iniciais (seed)

```bash
python seed.py
```

Saída esperada:
```
✅ Seed executado com sucesso!

📋 Usuários criados:
  admin@raizes.com     → Admin@123   (ADMIN)
  gerente@raizes.com   → Gerente@123 (GERENTE)
  atendente@raizes.com → Atende@123  (ATENDENTE)
  cozinha@raizes.com   → Cozinha@123 (COZINHA)
  cliente@raizes.com   → Cliente@123 (CLIENTE)
```

### 6. Iniciar a API

```bash
uvicorn app.main:app --reload
```

A API estará disponível em: **http://localhost:8000**

---

## Documentação interativa (Swagger)

Acesse no navegador após subir a API:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health check**: http://localhost:8000/

### Como autenticar no Swagger

1. Faça `POST /auth/login` com e-mail e senha
2. Copie o `access_token` da resposta
3. Clique no botão **Authorize 🔒** (canto superior direito)
4. Digite: `Bearer <access_token>` e confirme

---

## Executar os testes (coleção Postman)

### Ordem recomendada de execução

1. **Auth** → execute todos os "Login (setup)" primeiro para popular as variáveis de token
2. **Unidades e Cardápio**
3. **Pedidos** → T04 cria o pedido e salva `{{pedido_id}}`
4. **Pagamentos** → T05 e T06 completam o fluxo crítico
5. **Status do Pedido** → T07 avança o status
6. **Estoque** → T10 movimenta estoque
7. **Fidelidade** → T09 consulta pontos acumulados

### Importar no Postman

1. Abra o Postman
2. Clique em **Import**
3. Selecione o arquivo `raizes_nordeste_postman.json`
4. A coleção aparecerá com variáveis pré-configuradas (`base_url`, tokens, etc.)

> **Atenção:** Execute os requests de "Login (setup)" antes dos testes para preencher os tokens automaticamente via scripts de teste.

---

## Estrutura do projeto

```
raizes_nordeste/
├── app/
│   ├── main.py                        # Entrypoint FastAPI + Swagger
│   ├── config.py                      # Configurações (env vars)
│   ├── domain/
│   │   ├── models.py                  # Entidades SQLAlchemy (ORM)
│   │   └── schemas.py                 # Schemas Pydantic (request/response)
│   ├── application/
│   │   ├── auth_servico.py            # JWT, hash de senha, controle de acesso
│   │   └── auditoria_servico.py       # Log de ações sensíveis
│   ├── infrastructure/
│   │   └── database/
│   │       └── conexao.py             # Engine SQLAlchemy + sessão
│   └── api/
│       └── routers/
│           ├── auth.py                # POST /auth/login e /auth/cadastro
│           ├── usuarios.py            # GET/PATCH /usuarios (Admin)
│           ├── unidades.py            # /unidades + /unidades/{id}/cardapio
│           ├── produtos.py            # CRUD /produtos
│           ├── estoque.py             # /estoque/{unidade_id}/movimentar
│           ├── pedidos.py             # Fluxo crítico de pedidos
│           ├── pagamentos.py          # Gateway mock + confirmação
│           └── fidelidade.py          # Pontos, histórico, resgate
├── seed.py                            # Dados iniciais para demonstração
├── requirements.txt
├── .env.example
└── raizes_nordeste_postman.json       # Coleção de testes Postman
```

---

## Arquitetura em camadas

```
┌─────────────────────────────────────┐
│  API (Routers / Controllers)        │  ← Endpoints REST, auth, validação HTTP
├─────────────────────────────────────┤
│  Application (Serviços)             │  ← Regras de negócio, auth_servico, auditoria
├─────────────────────────────────────┤
│  Domain (Models + Schemas)          │  ← Entidades, enums, schemas Pydantic
├─────────────────────────────────────┤
│  Infrastructure (DB + Repositórios) │  ← SQLAlchemy, conexão, ORM
└─────────────────────────────────────┘
```

---

## Fluxo crítico implementado

```
POST /pedidos
    → valida unidade + cardápio + estoque
    → cria pedido com canalPedido (APP/TOTEM/BALCAO/PICKUP/WEB)
    → desconta estoque
    ↓
POST /pagamentos/solicitar?pedido_id={id}
    → cria registro de pagamento com referência MOCK-{uuid}
    ↓
POST /pagamentos/confirmar   (webhook simulado)
    → resultado: APROVADO → pedido vira PAGO + credita pontos fidelidade
    → resultado: RECUSADO → pedido volta a AGUARDANDO_PAGAMENTO
    ↓
PATCH /pedidos/{id}/status
    → PAGO → EM_PREPARO → PRONTO → ENTREGUE
    → qualquer transição inválida retorna 409
```

---

## Perfis e permissões

| Perfil     | Permissões principais                                      |
|------------|------------------------------------------------------------|
| CLIENTE    | Criar pedidos, ver próprios pedidos, fidelidade            |
| ATENDENTE  | Ver e movimentar estoque, atualizar status de pedidos      |
| COZINHA    | Atualizar status de pedidos (EM_PREPARO, PRONTO)           |
| GERENTE    | Tudo do atendente + gerenciar cardápio e unidades          |
| ADMIN      | Acesso total, confirmar pagamentos, gerenciar usuários     |

---

## Segurança e LGPD

- Senhas armazenadas com **bcrypt** (nunca em texto puro)
- Autenticação via **JWT Bearer Token** (expiração configurável)
- Autorização por **perfil/role** em todos os endpoints protegidos
- Respostas **nunca expõem** `senha_hash` ou dados sensíveis
- **Consentimento LGPD** obrigatório no cadastro e para uso do programa de fidelidade
- **Log de auditoria** para: login, cadastro, criação/cancelamento de pedidos, mudança de status, movimentações de estoque, pagamentos e resgates de pontos
- Dados de auditoria incluem: `usuario_id`, `ação`, `recurso`, `ip`, `timestamp`
