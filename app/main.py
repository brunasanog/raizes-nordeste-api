from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.config import config
from app.domain.models import Base
from app.infrastructure.database.conexao import engine
from app.api.routers import auth, usuarios, unidades, produtos, estoque, pedidos, pagamentos, fidelidade

# cria tabelas se não existirem
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=config.app_nome,
    version=config.app_versao,
    description="""
## API Back-End — Rede Raízes do Nordeste

Sistema de gestão para rede de lanchonetes nordestinas com suporte a múltiplos canais de atendimento.

### Funcionalidades
- **Autenticação** JWT com controle de perfis (CLIENTE, ATENDENTE, COZINHA, GERENTE, ADMIN)
- **Cardápio** por unidade com variações regionais de preço
- **Pedidos** via APP, TOTEM, BALCÃO, PICKUP e WEB (`canalPedido`)
- **Estoque** por unidade com movimentações auditadas
- **Pagamento** desacoplado via gateway mock
- **Fidelidade** com pontos e histórico (conformidade LGPD)
- **Auditoria** de ações sensíveis

### Fluxo crítico
`POST /pedidos` → `POST /pagamentos/solicitar` → `POST /pagamentos/confirmar` → `PATCH /pedidos/{id}/status`

### Autenticação
Use `POST /auth/login` para obter o token e clique em **Authorize** (🔒) passando: `Bearer <token>`
    """,
    contact={"name": "Raízes do Nordeste Dev", "email": "dev@raizes.com"},
    license_info={"name": "Acadêmico — UNINTER 2026"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(usuarios.router)
app.include_router(unidades.router)
app.include_router(produtos.router)
app.include_router(estoque.router)
app.include_router(pedidos.router)
app.include_router(pagamentos.router)
app.include_router(fidelidade.router)


# ── Handlers de erro padronizados ─────────────────────────────────────────────

@app.exception_handler(RequestValidationError)
async def erro_validacao(request: Request, exc: RequestValidationError):
    """Converte erros 422 do Pydantic para o padrão da API."""
    detalhes = []
    for erro in exc.errors():
        campo = ".".join(str(x) for x in erro.get("loc", []) if x != "body")
        detalhes.append({"campo": campo or "body", "problema": erro.get("msg", "")})
    return JSONResponse(
        status_code=422,
        content={
            "erro": "DADOS_INVALIDOS",
            "mensagem": "Um ou mais campos estão inválidos ou ausentes.",
            "detalhes": detalhes,
        },
    )


@app.exception_handler(Exception)
async def erro_generico(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "erro": "ERRO_INTERNO",
            "mensagem": "Ocorreu um erro inesperado. Tente novamente.",
            "caminho": str(request.url),
        },
    )


@app.get("/", tags=["Raiz"], summary="Health check da API")
def raiz():
    return {
        "api": config.app_nome,
        "versao": config.app_versao,
        "status": "online",
        "docs": "/docs",
        "redoc": "/redoc",
    }
