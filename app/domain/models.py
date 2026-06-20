import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    ForeignKey, Enum, Text, UniqueConstraint
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class PerfilUsuario(str, enum.Enum):
    CLIENTE = "CLIENTE"
    ATENDENTE = "ATENDENTE"
    COZINHA = "COZINHA"
    GERENTE = "GERENTE"
    ADMIN = "ADMIN"


class StatusPedido(str, enum.Enum):
    AGUARDANDO_PAGAMENTO = "AGUARDANDO_PAGAMENTO"
    PAGO = "PAGO"
    EM_PREPARO = "EM_PREPARO"
    PRONTO = "PRONTO"
    ENTREGUE = "ENTREGUE"
    CANCELADO = "CANCELADO"


class CanalPedido(str, enum.Enum):
    APP = "APP"
    TOTEM = "TOTEM"
    BALCAO = "BALCAO"
    PICKUP = "PICKUP"
    WEB = "WEB"


class StatusPagamento(str, enum.Enum):
    PENDENTE = "PENDENTE"
    APROVADO = "APROVADO"
    RECUSADO = "RECUSADO"


class TipoMovimentacaoEstoque(str, enum.Enum):
    ENTRADA = "ENTRADA"
    SAIDA = "SAIDA"


# ── Usuário ──────────────────────────────────────────────────────────────────

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(120), nullable=False)
    email = Column(String(180), unique=True, nullable=False, index=True)
    senha_hash = Column(String(255), nullable=False)
    perfil = Column(Enum(PerfilUsuario), default=PerfilUsuario.CLIENTE, nullable=False)
    ativo = Column(Boolean, default=True)
    consentimento_lgpd = Column(Boolean, default=False)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    pedidos = relationship("Pedido", back_populates="cliente")
    pontos_fidelidade = relationship("PontosFidelidade", back_populates="usuario", uselist=False)


# ── Unidade ───────────────────────────────────────────────────────────────────

class Unidade(Base):
    __tablename__ = "unidades"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(120), nullable=False)
    cidade = Column(String(80), nullable=False)
    estado = Column(String(2), nullable=False)
    endereco = Column(String(255))
    cozinha_completa = Column(Boolean, default=True)
    ativa = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

    estoques = relationship("Estoque", back_populates="unidade")
    pedidos = relationship("Pedido", back_populates="unidade")
    cardapio_itens = relationship("CardapioItem", back_populates="unidade")


# ── Produto ───────────────────────────────────────────────────────────────────

class Produto(Base):
    __tablename__ = "produtos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(120), nullable=False)
    descricao = Column(Text)
    preco = Column(Float, nullable=False)
    categoria = Column(String(60))
    disponivel_periodo_junino = Column(Boolean, default=False)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

    estoques = relationship("Estoque", back_populates="produto")
    itens_pedido = relationship("ItemPedido", back_populates="produto")
    cardapio_itens = relationship("CardapioItem", back_populates="produto")


# ── Cardápio por unidade ──────────────────────────────────────────────────────

class CardapioItem(Base):
    __tablename__ = "cardapio_itens"
    __table_args__ = (UniqueConstraint("unidade_id", "produto_id"),)

    id = Column(Integer, primary_key=True, index=True)
    unidade_id = Column(Integer, ForeignKey("unidades.id"), nullable=False)
    produto_id = Column(Integer, ForeignKey("produtos.id"), nullable=False)
    preco_local = Column(Float)          # permite variação regional de preço
    disponivel = Column(Boolean, default=True)

    unidade = relationship("Unidade", back_populates="cardapio_itens")
    produto = relationship("Produto", back_populates="cardapio_itens")


# ── Estoque ───────────────────────────────────────────────────────────────────

class Estoque(Base):
    __tablename__ = "estoques"
    __table_args__ = (UniqueConstraint("unidade_id", "produto_id"),)

    id = Column(Integer, primary_key=True, index=True)
    unidade_id = Column(Integer, ForeignKey("unidades.id"), nullable=False)
    produto_id = Column(Integer, ForeignKey("produtos.id"), nullable=False)
    quantidade = Column(Integer, default=0, nullable=False)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    unidade = relationship("Unidade", back_populates="estoques")
    produto = relationship("Produto", back_populates="estoques")
    movimentacoes = relationship("MovimentacaoEstoque", back_populates="estoque")


class MovimentacaoEstoque(Base):
    __tablename__ = "movimentacoes_estoque"

    id = Column(Integer, primary_key=True, index=True)
    estoque_id = Column(Integer, ForeignKey("estoques.id"), nullable=False)
    tipo = Column(Enum(TipoMovimentacaoEstoque), nullable=False)
    quantidade = Column(Integer, nullable=False)
    motivo = Column(String(200))
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    criado_em = Column(DateTime, default=datetime.utcnow)

    estoque = relationship("Estoque", back_populates="movimentacoes")


# ── Pedido ────────────────────────────────────────────────────────────────────

class Pedido(Base):
    __tablename__ = "pedidos"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    unidade_id = Column(Integer, ForeignKey("unidades.id"), nullable=False)
    canal_pedido = Column(Enum(CanalPedido), nullable=False)
    status = Column(Enum(StatusPedido), default=StatusPedido.AGUARDANDO_PAGAMENTO)
    total = Column(Float, nullable=False)
    forma_pagamento = Column(String(40))
    observacao = Column(Text)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    cliente = relationship("Usuario", back_populates="pedidos")
    unidade = relationship("Unidade", back_populates="pedidos")
    itens = relationship("ItemPedido", back_populates="pedido", cascade="all, delete-orphan")
    pagamento = relationship("Pagamento", back_populates="pedido", uselist=False)


class ItemPedido(Base):
    __tablename__ = "itens_pedido"

    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"), nullable=False)
    produto_id = Column(Integer, ForeignKey("produtos.id"), nullable=False)
    quantidade = Column(Integer, nullable=False)
    preco_unitario = Column(Float, nullable=False)

    pedido = relationship("Pedido", back_populates="itens")
    produto = relationship("Produto", back_populates="itens_pedido")


# ── Pagamento (desacoplado) ───────────────────────────────────────────────────

class Pagamento(Base):
    __tablename__ = "pagamentos"

    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"), unique=True, nullable=False)
    status = Column(Enum(StatusPagamento), default=StatusPagamento.PENDENTE)
    valor = Column(Float, nullable=False)
    metodo = Column(String(40))
    referencia_externa = Column(String(120))   # ID retornado pelo gateway mock
    payload_retorno = Column(Text)             # JSON bruto da resposta mock
    criado_em = Column(DateTime, default=datetime.utcnow)
    processado_em = Column(DateTime)

    pedido = relationship("Pedido", back_populates="pagamento")


# ── Fidelidade ────────────────────────────────────────────────────────────────

class PontosFidelidade(Base):
    __tablename__ = "pontos_fidelidade"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), unique=True, nullable=False)
    saldo = Column(Integer, default=0)
    total_acumulado = Column(Integer, default=0)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    usuario = relationship("Usuario", back_populates="pontos_fidelidade")
    historico = relationship("HistoricoFidelidade", back_populates="pontos")


class HistoricoFidelidade(Base):
    __tablename__ = "historico_fidelidade"

    id = Column(Integer, primary_key=True, index=True)
    pontos_id = Column(Integer, ForeignKey("pontos_fidelidade.id"), nullable=False)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"))
    tipo = Column(String(20))          # CREDITO / DEBITO / RESGATE
    quantidade = Column(Integer, nullable=False)
    descricao = Column(String(200))
    criado_em = Column(DateTime, default=datetime.utcnow)

    pontos = relationship("PontosFidelidade", back_populates="historico")


# ── Log de Auditoria ──────────────────────────────────────────────────────────

class LogAuditoria(Base):
    __tablename__ = "logs_auditoria"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    acao = Column(String(100), nullable=False)
    recurso = Column(String(80))
    recurso_id = Column(Integer)
    detalhes = Column(Text)
    ip = Column(String(45))
    criado_em = Column(DateTime, default=datetime.utcnow)
