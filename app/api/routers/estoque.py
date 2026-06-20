from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.domain.models import (
    Estoque, Produto, Unidade, MovimentacaoEstoque,
    TipoMovimentacaoEstoque, PerfilUsuario, Usuario
)
from app.domain.schemas import EstoqueSaida, MovimentacaoEntrada, MovimentacaoSaida
from app.application.auth_servico import exigir_perfis, usuario_atual
from app.application.auditoria_servico import registrar
from app.infrastructure.database.conexao import obter_sessao

router = APIRouter(prefix="/estoque", tags=["Estoque"])

_equipe = exigir_perfis(PerfilUsuario.ATENDENTE, PerfilUsuario.GERENTE, PerfilUsuario.ADMIN)


@router.get("/{unidade_id}", response_model=list[EstoqueSaida],
            summary="Consultar estoque por unidade")
def consultar(
    unidade_id: int,
    pagina: int = Query(1, ge=1),
    limite: int = Query(30, ge=1, le=100),
    db: Session = Depends(obter_sessao),
    _: Usuario = Depends(_equipe),
):
    unidade = db.query(Unidade).filter(Unidade.id == unidade_id).first()
    if not unidade:
        raise HTTPException(404, detail={"erro": "NAO_ENCONTRADO", "mensagem": "Unidade não encontrada"})

    itens = (
        db.query(Estoque)
        .filter(Estoque.unidade_id == unidade_id)
        .offset((pagina - 1) * limite).limit(limite)
        .all()
    )
    return [
        EstoqueSaida(
            produto_id=e.produto_id,
            nome_produto=e.produto.nome,
            quantidade=e.quantidade,
            atualizado_em=e.atualizado_em,
        )
        for e in itens
    ]


@router.post("/{unidade_id}/movimentar", response_model=MovimentacaoSaida, status_code=201,
             summary="Movimentar estoque (entrada/saída)")
def movimentar(
    unidade_id: int,
    dados: MovimentacaoEntrada,
    db: Session = Depends(obter_sessao),
    responsavel: Usuario = Depends(_equipe),
):
    unidade = db.query(Unidade).filter(Unidade.id == unidade_id).first()
    if not unidade:
        raise HTTPException(404, detail={"erro": "NAO_ENCONTRADO", "mensagem": "Unidade não encontrada"})

    produto = db.query(Produto).filter(Produto.id == dados.produto_id, Produto.ativo == True).first()
    if not produto:
        raise HTTPException(404, detail={"erro": "NAO_ENCONTRADO", "mensagem": "Produto não encontrado"})

    registro = db.query(Estoque).filter(
        Estoque.unidade_id == unidade_id,
        Estoque.produto_id == dados.produto_id,
    ).first()

    if not registro:
        registro = Estoque(unidade_id=unidade_id, produto_id=dados.produto_id, quantidade=0)
        db.add(registro)
        db.flush()

    if dados.tipo == TipoMovimentacaoEstoque.SAIDA:
        if registro.quantidade < dados.quantidade:
            raise HTTPException(
                409,
                detail={
                    "erro": "ESTOQUE_INSUFICIENTE",
                    "mensagem": "Quantidade insuficiente em estoque",
                    "detalhes": [{"campo": "quantidade", "problema": f"Disponível: {registro.quantidade}"}],
                },
            )
        registro.quantidade -= dados.quantidade
    else:
        registro.quantidade += dados.quantidade

    mov = MovimentacaoEstoque(
        estoque_id=registro.id,
        tipo=dados.tipo,
        quantidade=dados.quantidade,
        motivo=dados.motivo,
        usuario_id=responsavel.id,
    )
    db.add(mov)
    db.commit()
    db.refresh(mov)

    registrar(db, f"ESTOQUE_{dados.tipo.value}", "estoques", registro.id,
              usuario_id=responsavel.id,
              detalhes=f"Produto {dados.produto_id} | Qtd: {dados.quantidade}")
    return mov
