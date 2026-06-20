from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.domain.models import PontosFidelidade, HistoricoFidelidade, Usuario, PerfilUsuario
from app.domain.schemas import FidelidadeSaida, ResgateEntrada, HistoricoFidelidadeSaida
from app.application.auth_servico import usuario_atual
from app.application.auditoria_servico import registrar
from app.infrastructure.database.conexao import obter_sessao

router = APIRouter(prefix="/fidelidade", tags=["Fidelidade"])

_PONTOS_POR_RESGATE = 50   # mínimo para resgatar


@router.get("/minha", response_model=FidelidadeSaida, summary="Minha carteira de pontos")
def minha_carteira(
    db: Session = Depends(obter_sessao),
    usuario: Usuario = Depends(usuario_atual),
):
    carteira = db.query(PontosFidelidade).filter(
        PontosFidelidade.usuario_id == usuario.id
    ).first()
    if not carteira:
        raise HTTPException(404, detail={"erro": "NAO_ENCONTRADO", "mensagem": "Carteira não encontrada"})
    return FidelidadeSaida(
        usuario_id=carteira.usuario_id,
        saldo=carteira.saldo,
        total_acumulado=carteira.total_acumulado,
        atualizado_em=carteira.atualizado_em,
    )


@router.get("/minha/historico", response_model=list[HistoricoFidelidadeSaida],
            summary="Histórico de pontos")
def historico(
    pagina: int = Query(1, ge=1),
    limite: int = Query(20, ge=1, le=50),
    db: Session = Depends(obter_sessao),
    usuario: Usuario = Depends(usuario_atual),
):
    carteira = db.query(PontosFidelidade).filter(
        PontosFidelidade.usuario_id == usuario.id
    ).first()
    if not carteira:
        return []

    return (
        db.query(HistoricoFidelidade)
        .filter(HistoricoFidelidade.pontos_id == carteira.id)
        .order_by(HistoricoFidelidade.criado_em.desc())
        .offset((pagina - 1) * limite).limit(limite)
        .all()
    )


@router.post("/resgatar", response_model=FidelidadeSaida,
             summary="Resgatar pontos (desconto no próximo pedido)")
def resgatar(
    dados: ResgateEntrada,
    db: Session = Depends(obter_sessao),
    usuario: Usuario = Depends(usuario_atual),
):
    if not usuario.consentimento_lgpd:
        raise HTTPException(
            403,
            detail={
                "erro": "LGPD_CONSENTIMENTO_AUSENTE",
                "mensagem": "É necessário consentimento LGPD para usar o programa de fidelidade",
            },
        )

    carteira = db.query(PontosFidelidade).filter(
        PontosFidelidade.usuario_id == usuario.id
    ).first()
    if not carteira:
        raise HTTPException(404, detail={"erro": "NAO_ENCONTRADO", "mensagem": "Carteira não encontrada"})

    if dados.pontos < _PONTOS_POR_RESGATE:
        raise HTTPException(
            409,
            detail={
                "erro": "PONTOS_INSUFICIENTES_PARA_RESGATE",
                "mensagem": f"Mínimo de {_PONTOS_POR_RESGATE} pontos para resgatar",
            },
        )

    if carteira.saldo < dados.pontos:
        raise HTTPException(
            409,
            detail={
                "erro": "SALDO_INSUFICIENTE",
                "mensagem": f"Saldo disponível: {carteira.saldo} pontos",
            },
        )

    carteira.saldo -= dados.pontos
    db.add(HistoricoFidelidade(
        pontos_id=carteira.id,
        tipo="RESGATE",
        quantidade=dados.pontos,
        descricao=f"Resgate de {dados.pontos} pontos",
    ))
    db.commit()
    db.refresh(carteira)

    registrar(db, "RESGATE_PONTOS", "pontos_fidelidade", carteira.id,
              usuario_id=usuario.id, detalhes=f"Pontos resgatados: {dados.pontos}")

    return FidelidadeSaida(
        usuario_id=carteira.usuario_id,
        saldo=carteira.saldo,
        total_acumulado=carteira.total_acumulado,
        atualizado_em=carteira.atualizado_em,
    )
