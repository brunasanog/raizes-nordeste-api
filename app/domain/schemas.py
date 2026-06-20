from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, field_validator, model_validator
from app.domain.models import PerfilUsuario, StatusPedido, CanalPedido, StatusPagamento, TipoMovimentacaoEstoque


# ── Padrão de erro ────────────────────────────────────────────────────────────

class DetalheErro(BaseModel):
    campo: str
    problema: str


class RespostaErro(BaseModel):
    erro: str
    mensagem: str
    detalhes: List[DetalheErro] = []
    timestamp: datetime = None
    caminho: str = ""

    def model_post_init(self, __context):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginEntrada(BaseModel):
    email: EmailStr
    senha: str


class TokenSaida(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expira_em: int
    usuario: "UsuarioResumido"


class UsuarioResumido(BaseModel):
    id: int
    nome: str
    perfil: PerfilUsuario

    model_config = {"from_attributes": True}


# ── Usuário ───────────────────────────────────────────────────────────────────

class UsuarioCriar(BaseModel):
    nome: str
    email: EmailStr
    senha: str
    consentimento_lgpd: bool

    @field_validator("senha")
    @classmethod
    def senha_minima(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Senha deve ter ao menos 8 caracteres")
        return v

    @field_validator("consentimento_lgpd")
    @classmethod
    def lgpd_obrigatorio(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Consentimento LGPD é obrigatório para cadastro")
        return v


class UsuarioSaida(BaseModel):
    id: int
    nome: str
    email: EmailStr
    perfil: PerfilUsuario
    ativo: bool
    consentimento_lgpd: bool
    criado_em: datetime

    model_config = {"from_attributes": True}


class UsuarioAtualizar(BaseModel):
    nome: Optional[str] = None
    perfil: Optional[PerfilUsuario] = None
    ativo: Optional[bool] = None


# ── Unidade ───────────────────────────────────────────────────────────────────

class UnidadeCriar(BaseModel):
    nome: str
    cidade: str
    estado: str
    endereco: Optional[str] = None
    cozinha_completa: bool = True


class UnidadeSaida(BaseModel):
    id: int
    nome: str
    cidade: str
    estado: str
    endereco: Optional[str]
    cozinha_completa: bool
    ativa: bool

    model_config = {"from_attributes": True}


# ── Produto ───────────────────────────────────────────────────────────────────

class ProdutoCriar(BaseModel):
    nome: str
    descricao: Optional[str] = None
    preco: float
    categoria: Optional[str] = None
    disponivel_periodo_junino: bool = False

    @field_validator("preco")
    @classmethod
    def preco_positivo(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Preço deve ser maior que zero")
        return v


class ProdutoSaida(BaseModel):
    id: int
    nome: str
    descricao: Optional[str]
    preco: float
    categoria: Optional[str]
    disponivel_periodo_junino: bool
    ativo: bool

    model_config = {"from_attributes": True}


# ── Cardápio ──────────────────────────────────────────────────────────────────

class CardapioItemSaida(BaseModel):
    produto_id: int
    nome: str
    descricao: Optional[str]
    preco: float
    categoria: Optional[str]
    disponivel: bool

    model_config = {"from_attributes": True}


class CardapioAdicionarEntrada(BaseModel):
    produto_id: int
    preco_local: Optional[float] = None
    disponivel: bool = True


# ── Estoque ───────────────────────────────────────────────────────────────────

class EstoqueSaida(BaseModel):
    produto_id: int
    nome_produto: str
    quantidade: int
    atualizado_em: datetime

    model_config = {"from_attributes": True}


class MovimentacaoEntrada(BaseModel):
    produto_id: int
    tipo: TipoMovimentacaoEstoque
    quantidade: int
    motivo: Optional[str] = None

    @field_validator("quantidade")
    @classmethod
    def qtd_positiva(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Quantidade deve ser maior que zero")
        return v


class MovimentacaoSaida(BaseModel):
    id: int
    tipo: TipoMovimentacaoEstoque
    quantidade: int
    motivo: Optional[str]
    criado_em: datetime

    model_config = {"from_attributes": True}


# ── Pedido ────────────────────────────────────────────────────────────────────

class ItemPedidoEntrada(BaseModel):
    produto_id: int
    quantidade: int

    @field_validator("quantidade")
    @classmethod
    def qtd_positiva(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Quantidade deve ser maior que zero")
        return v


class PedidoCriar(BaseModel):
    unidade_id: int
    canal_pedido: CanalPedido
    itens: List[ItemPedidoEntrada]
    forma_pagamento: str
    observacao: Optional[str] = None

    @field_validator("itens")
    @classmethod
    def itens_nao_vazios(cls, v):
        if not v:
            raise ValueError("Pedido deve ter ao menos um item")
        return v


class ItemPedidoSaida(BaseModel):
    produto_id: int
    quantidade: int
    preco_unitario: float

    model_config = {"from_attributes": True}


class PedidoSaida(BaseModel):
    id: int
    cliente_id: int
    unidade_id: int
    canal_pedido: CanalPedido
    status: StatusPedido
    total: float
    forma_pagamento: Optional[str]
    observacao: Optional[str]
    itens: List[ItemPedidoSaida]
    criado_em: datetime
    atualizado_em: datetime

    model_config = {"from_attributes": True}


class StatusAtualizar(BaseModel):
    status: StatusPedido
    motivo: Optional[str] = None


# ── Pagamento ─────────────────────────────────────────────────────────────────

class PagamentoSaida(BaseModel):
    id: int
    pedido_id: int
    status: StatusPagamento
    valor: float
    metodo: Optional[str]
    referencia_externa: Optional[str]
    criado_em: datetime
    processado_em: Optional[datetime]

    model_config = {"from_attributes": True}


class ProcessarPagamentoEntrada(BaseModel):
    pedido_id: int
    resultado: str        


# ── Fidelidade ────────────────────────────────────────────────────────────────

class FidelidadeSaida(BaseModel):
    usuario_id: int
    saldo: int
    total_acumulado: int
    atualizado_em: datetime

    model_config = {"from_attributes": True}


class ResgateEntrada(BaseModel):
    pontos: int

    @field_validator("pontos")
    @classmethod
    def pontos_positivos(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Quantidade de pontos deve ser positiva")
        return v


class HistoricoFidelidadeSaida(BaseModel):
    tipo: str
    quantidade: int
    descricao: Optional[str]
    criado_em: datetime

    model_config = {"from_attributes": True}


# ── Paginação ─────────────────────────────────────────────────────────────────

class PaginaSaida(BaseModel):
    pagina: int
    limite: int
    total: int
    itens: list
