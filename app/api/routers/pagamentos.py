import json
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.domain.models import (
    Pagamento, Pedido, StatusPedido, StatusPagamento,
    PerfilUsuario, Usuario, PontosFidelidade, HistoricoFidelidade
)
from app.domain.schemas import PagamentoSaida, ProcessarPagamentoEntrada
from app.application.auth_servico import exigir_perfis, usuario_atual
from app.application.auditoria_servico import registrar
from app.infrastructure.database.conexao import obter_sessao

router = APIRouter(prefix="/pagamentos", tags=["Pagamentos"])


def _calcular_pontos(total: float) -> int:
    """1 ponto a cada R$ 5,00 gastos."""
    return int(total // 5)


@router.post("/solicitar", response_model=PagamentoSaida, status_code=201,
             summary="Solicitar pagamento via gateway mock")
def solicitar(
    pedido_id: int,
    db: Session = Depends(obter_sessao),
    cliente: Usuario = Depends(usuario_atual),
):
    pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(404, detail={"erro": "NAO_ENCONTRADO", "mensagem": "Pedido não encontrado"})

    if cliente.perfil == PerfilUsuario.CLIENTE and pedido.cliente_id != cliente.id:
        raise HTTPException(403, detail={"erro": "SEM_PERMISSAO", "mensagem": "Acesso negado"})

    if pedido.status != StatusPedido.AGUARDANDO_PAGAMENTO:
        raise HTTPException(
            409,
            detail={"erro": "STATUS_INVALIDO", "mensagem": "Pedido não está aguardando pagamento"},
        )

    existente = db.query(Pagamento).filter(Pagamento.pedido_id == pedido_id).first()
    if existente:
        raise HTTPException(
            409,
            detail={"erro": "PAGAMENTO_JA_SOLICITADO", "mensagem": "Já existe uma solicitação para este pedido"},
        )

    pagamento = Pagamento(
        pedido_id=pedido_id,
        valor=pedido.total,
        metodo=pedido.forma_pagamento,
        referencia_externa=f"MOCK-{uuid.uuid4().hex[:12].upper()}",
        status=StatusPagamento.PENDENTE,
    )
    db.add(pagamento)
    db.commit()
    db.refresh(pagamento)

    registrar(db, "PAGAMENTO_SOLICITADO", "pagamentos", pagamento.id,
              usuario_id=cliente.id,
              detalhes=f"Pedido {pedido_id} | Valor: {pedido.total:.2f}")
    return pagamento


@router.post("/confirmar", response_model=PagamentoSaida,
             summary="Confirmar resultado do gateway mock (webhook simulado)")
def confirmar(
    dados: ProcessarPagamentoEntrada,
    db: Session = Depends(obter_sessao),
    _: Usuario = Depends(exigir_perfis(PerfilUsuario.ADMIN, PerfilUsuario.GERENTE)),
):
    pagamento = db.query(Pagamento).filter(Pagamento.pedido_id == dados.pedido_id).first()
    if not pagamento:
        raise HTTPException(404, detail={"erro": "NAO_ENCONTRADO", "mensagem": "Pagamento não encontrado"})

    if pagamento.status != StatusPagamento.PENDENTE:
        raise HTTPException(
            409,
            detail={"erro": "PAGAMENTO_JA_PROCESSADO", "mensagem": "Este pagamento já foi processado"},
        )

    resultado = dados.resultado.upper()
    if resultado not in ("APROVADO", "RECUSADO"):
        raise HTTPException(
            422,
            detail={"erro": "RESULTADO_INVALIDO", "mensagem": "Resultado deve ser APROVADO ou RECUSADO"},
        )

    pagamento.status = StatusPagamento[resultado]
    pagamento.processado_em = datetime.utcnow()
    pagamento.payload_retorno = json.dumps({
        "resultado": resultado,
        "referencia": pagamento.referencia_externa,
        "processado_em": pagamento.processado_em.isoformat(),
    })

    pedido = pagamento.pedido
    if resultado == "APROVADO":
        pedido.status = StatusPedido.PAGO
        _creditar_pontos(db, pedido)
    else:
        pedido.status = StatusPedido.AGUARDANDO_PAGAMENTO  # permite nova tentativa

    db.commit()
    db.refresh(pagamento)

    registrar(db, f"PAGAMENTO_{resultado}", "pagamentos", pagamento.id,
              detalhes=f"Pedido {dados.pedido_id} | Ref: {pagamento.referencia_externa}")
    return pagamento


def _creditar_pontos(db: Session, pedido: Pedido) -> None:
    """Credita pontos de fidelidade ao cliente após pagamento aprovado."""
    pontos_ganhos = _calcular_pontos(pedido.total)
    if pontos_ganhos <= 0:
        return

    carteira = db.query(PontosFidelidade).filter(
        PontosFidelidade.usuario_id == pedido.cliente_id
    ).first()
    if not carteira:
        carteira = PontosFidelidade(usuario_id=pedido.cliente_id)
        db.add(carteira)
        db.flush()

    carteira.saldo += pontos_ganhos
    carteira.total_acumulado += pontos_ganhos

    db.add(HistoricoFidelidade(
        pontos_id=carteira.id,
        pedido_id=pedido.id,
        tipo="CREDITO",
        quantidade=pontos_ganhos,
        descricao=f"Pontos por pedido #{pedido.id} — R$ {pedido.total:.2f}",
    ))


@router.get("/{pedido_id}", response_model=PagamentoSaida,
            summary="Consultar pagamento de um pedido")
def consultar(
    pedido_id: int,
    db: Session = Depends(obter_sessao),
    usuario: Usuario = Depends(usuario_atual),
):
    pagamento = db.query(Pagamento).filter(Pagamento.pedido_id == pedido_id).first()
    if not pagamento:
        raise HTTPException(404, detail={"erro": "NAO_ENCONTRADO", "mensagem": "Pagamento não encontrado"})

    pedido = pagamento.pedido
    if usuario.perfil == PerfilUsuario.CLIENTE and pedido.cliente_id != usuario.id:
        raise HTTPException(403, detail={"erro": "SEM_PERMISSAO", "mensagem": "Acesso negado"})

    return pagamento
