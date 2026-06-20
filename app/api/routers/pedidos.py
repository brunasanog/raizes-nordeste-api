from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.domain.models import (
    Pedido, ItemPedido, Estoque, CardapioItem, Unidade,
    StatusPedido, PerfilUsuario, Usuario, CanalPedido
)
from app.domain.schemas import PedidoCriar, PedidoSaida, StatusAtualizar
from app.application.auth_servico import exigir_perfis, usuario_atual
from app.application.auditoria_servico import registrar
from app.infrastructure.database.conexao import obter_sessao

router = APIRouter(prefix="/pedidos", tags=["Pedidos"])

_cozinha_atendente = exigir_perfis(
    PerfilUsuario.COZINHA, PerfilUsuario.ATENDENTE,
    PerfilUsuario.GERENTE, PerfilUsuario.ADMIN
)

_transicoes_validas = {
    StatusPedido.AGUARDANDO_PAGAMENTO: {StatusPedido.PAGO, StatusPedido.CANCELADO},
    StatusPedido.PAGO: {StatusPedido.EM_PREPARO, StatusPedido.CANCELADO},
    StatusPedido.EM_PREPARO: {StatusPedido.PRONTO},
    StatusPedido.PRONTO: {StatusPedido.ENTREGUE},
    StatusPedido.ENTREGUE: set(),
    StatusPedido.CANCELADO: set(),
}


@router.post("/", response_model=PedidoSaida, status_code=201, summary="Criar pedido")
def criar_pedido(
    dados: PedidoCriar,
    db: Session = Depends(obter_sessao),
    cliente: Usuario = Depends(usuario_atual),
):
    unidade = db.query(Unidade).filter(
        Unidade.id == dados.unidade_id, Unidade.ativa == True
    ).first()
    if not unidade:
        raise HTTPException(404, detail={"erro": "NAO_ENCONTRADO", "mensagem": "Unidade não encontrada"})

    total = 0.0
    itens_montados = []

    for item_entrada in dados.itens:
        cardapio = db.query(CardapioItem).filter(
            CardapioItem.unidade_id == dados.unidade_id,
            CardapioItem.produto_id == item_entrada.produto_id,
            CardapioItem.disponivel == True,
        ).first()
        if not cardapio:
            raise HTTPException(
                404,
                detail={
                    "erro": "PRODUTO_INDISPONIVEL",
                    "mensagem": f"Produto {item_entrada.produto_id} não disponível nesta unidade",
                },
            )

        estoque = db.query(Estoque).filter(
            Estoque.unidade_id == dados.unidade_id,
            Estoque.produto_id == item_entrada.produto_id,
        ).first()
        quantidade_disponivel = estoque.quantidade if estoque else 0

        if quantidade_disponivel < item_entrada.quantidade:
            raise HTTPException(
                409,
                detail={
                    "erro": "ESTOQUE_INSUFICIENTE",
                    "mensagem": "Quantidade insuficiente para um ou mais itens",
                    "detalhes": [
                        {
                            "campo": f"itens[produto_id={item_entrada.produto_id}].quantidade",
                            "problema": f"Disponível: {quantidade_disponivel}",
                        }
                    ],
                },
            )

        preco_unitario = cardapio.preco_local if cardapio.preco_local else cardapio.produto.preco
        total += preco_unitario * item_entrada.quantidade
        itens_montados.append((item_entrada, preco_unitario, estoque))

    pedido = Pedido(
        cliente_id=cliente.id,
        unidade_id=dados.unidade_id,
        canal_pedido=dados.canal_pedido,
        total=round(total, 2),
        forma_pagamento=dados.forma_pagamento,
        observacao=dados.observacao,
    )
    db.add(pedido)
    db.flush()

    for item_entrada, preco_unitario, estoque in itens_montados:
        db.add(ItemPedido(
            pedido_id=pedido.id,
            produto_id=item_entrada.produto_id,
            quantidade=item_entrada.quantidade,
            preco_unitario=preco_unitario,
        ))

        if estoque:
            estoque.quantidade -= item_entrada.quantidade

    db.commit()
    db.refresh(pedido)

    registrar(db, "PEDIDO_CRIADO", "pedidos", pedido.id, usuario_id=cliente.id,
              detalhes=f"Canal: {dados.canal_pedido.value} | Total: {total:.2f}")
    return pedido


@router.get("/", response_model=list[PedidoSaida], summary="Listar pedidos")
def listar(
    canal_pedido: CanalPedido = Query(None, description="Filtrar por canal"),
    status: StatusPedido = Query(None, description="Filtrar por status"),
    unidade_id: int = Query(None),
    pagina: int = Query(1, ge=1),
    limite: int = Query(20, ge=1, le=100),
    db: Session = Depends(obter_sessao),
    usuario: Usuario = Depends(usuario_atual),
):
    q = db.query(Pedido)

    if usuario.perfil == PerfilUsuario.CLIENTE:
        q = q.filter(Pedido.cliente_id == usuario.id)

    if canal_pedido:
        q = q.filter(Pedido.canal_pedido == canal_pedido)
    if status:
        q = q.filter(Pedido.status == status)
    if unidade_id:
        q = q.filter(Pedido.unidade_id == unidade_id)

    return q.order_by(Pedido.criado_em.desc()).offset((pagina - 1) * limite).limit(limite).all()


@router.get("/{pedido_id}", response_model=PedidoSaida, summary="Buscar pedido por ID")
def buscar(
    pedido_id: int,
    db: Session = Depends(obter_sessao),
    usuario: Usuario = Depends(usuario_atual),
):
    pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(404, detail={"erro": "NAO_ENCONTRADO", "mensagem": "Pedido não encontrado"})

    if usuario.perfil == PerfilUsuario.CLIENTE and pedido.cliente_id != usuario.id:
        raise HTTPException(403, detail={"erro": "SEM_PERMISSAO", "mensagem": "Acesso negado"})

    return pedido


@router.patch("/{pedido_id}/status", response_model=PedidoSaida,
              summary="Atualizar status do pedido (Equipe interna)")
def atualizar_status(
    pedido_id: int,
    dados: StatusAtualizar,
    db: Session = Depends(obter_sessao),
    responsavel: Usuario = Depends(_cozinha_atendente),
):
    pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(404, detail={"erro": "NAO_ENCONTRADO", "mensagem": "Pedido não encontrado"})

    permitidos = _transicoes_validas.get(pedido.status, set())
    if dados.status not in permitidos:
        raise HTTPException(
            409,
            detail={
                "erro": "TRANSICAO_INVALIDA",
                "mensagem": f"Não é possível mover de '{pedido.status.value}' para '{dados.status.value}'",
            },
        )

    status_anterior = pedido.status.value
    pedido.status = dados.status
    db.commit()
    db.refresh(pedido)

    registrar(db, "STATUS_PEDIDO_ALTERADO", "pedidos", pedido_id,
              usuario_id=responsavel.id,
              detalhes=f"{status_anterior} → {dados.status.value} | Motivo: {dados.motivo}")
    return pedido


@router.delete("/{pedido_id}", status_code=204, summary="Cancelar pedido")
def cancelar(
    pedido_id: int,
    db: Session = Depends(obter_sessao),
    usuario: Usuario = Depends(usuario_atual),
):
    pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(404, detail={"erro": "NAO_ENCONTRADO", "mensagem": "Pedido não encontrado"})

    if usuario.perfil == PerfilUsuario.CLIENTE and pedido.cliente_id != usuario.id:
        raise HTTPException(403, detail={"erro": "SEM_PERMISSAO", "mensagem": "Acesso negado"})

    if pedido.status not in {StatusPedido.AGUARDANDO_PAGAMENTO, StatusPedido.PAGO}:
        raise HTTPException(
            409,
            detail={"erro": "CANCELAMENTO_NEGADO", "mensagem": "Pedido não pode mais ser cancelado"},
        )

    pedido.status = StatusPedido.CANCELADO
    db.commit()

    registrar(db, "PEDIDO_CANCELADO", "pedidos", pedido_id, usuario_id=usuario.id)
