from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.domain.models import Unidade, PerfilUsuario, CardapioItem, Produto, Usuario
from app.domain.schemas import UnidadeCriar, UnidadeSaida, CardapioItemSaida, CardapioAdicionarEntrada
from app.application.auth_servico import exigir_perfis, usuario_atual
from app.infrastructure.database.conexao import obter_sessao

router = APIRouter(prefix="/unidades", tags=["Unidades"])

_gerente_ou_admin = exigir_perfis(PerfilUsuario.GERENTE, PerfilUsuario.ADMIN)


@router.get("/", response_model=list[UnidadeSaida], summary="Listar unidades ativas")
def listar(
    pagina: int = Query(1, ge=1),
    limite: int = Query(20, ge=1, le=100),
    db: Session = Depends(obter_sessao),
    _: Usuario = Depends(usuario_atual),
):
    offset = (pagina - 1) * limite
    return db.query(Unidade).filter(Unidade.ativa == True).offset(offset).limit(limite).all()


@router.post("/", response_model=UnidadeSaida, status_code=201, summary="Criar unidade (Admin)")
def criar(
    dados: UnidadeCriar,
    db: Session = Depends(obter_sessao),
    _: Usuario = Depends(exigir_perfis(PerfilUsuario.ADMIN)),
):
    nova = Unidade(**dados.model_dump())
    db.add(nova)
    db.commit()
    db.refresh(nova)
    return nova


@router.get("/{unidade_id}", response_model=UnidadeSaida, summary="Buscar unidade")
def buscar(
    unidade_id: int,
    db: Session = Depends(obter_sessao),
    _: Usuario = Depends(usuario_atual),
):
    u = db.query(Unidade).filter(Unidade.id == unidade_id).first()
    if not u:
        raise HTTPException(404, detail={"erro": "NAO_ENCONTRADO", "mensagem": "Unidade não encontrada"})
    return u


# ── Cardápio ──────────────────────────────────────────────────────────────────

@router.get("/{unidade_id}/cardapio", response_model=list[CardapioItemSaida],
            summary="Cardápio da unidade")
def cardapio(
    unidade_id: int,
    db: Session = Depends(obter_sessao),
    _: Usuario = Depends(usuario_atual),
):
    unidade = db.query(Unidade).filter(Unidade.id == unidade_id, Unidade.ativa == True).first()
    if not unidade:
        raise HTTPException(404, detail={"erro": "NAO_ENCONTRADO", "mensagem": "Unidade não encontrada"})

    itens = (
        db.query(CardapioItem)
        .filter(CardapioItem.unidade_id == unidade_id, CardapioItem.disponivel == True)
        .all()
    )
    resultado = []
    for item in itens:
        produto = item.produto
        resultado.append(CardapioItemSaida(
            produto_id=produto.id,
            nome=produto.nome,
            descricao=produto.descricao,
            preco=item.preco_local if item.preco_local else produto.preco,
            categoria=produto.categoria,
            disponivel=item.disponivel,
        ))
    return resultado


@router.post("/{unidade_id}/cardapio", status_code=201, summary="Adicionar produto ao cardápio (Gerente/Admin)")
def adicionar_cardapio(
    unidade_id: int,
    dados: CardapioAdicionarEntrada,
    db: Session = Depends(obter_sessao),
    _: Usuario = Depends(_gerente_ou_admin),
):
    unidade = db.query(Unidade).filter(Unidade.id == unidade_id).first()
    if not unidade:
        raise HTTPException(404, detail={"erro": "NAO_ENCONTRADO", "mensagem": "Unidade não encontrada"})

    produto = db.query(Produto).filter(Produto.id == dados.produto_id, Produto.ativo == True).first()
    if not produto:
        raise HTTPException(404, detail={"erro": "NAO_ENCONTRADO", "mensagem": "Produto não encontrado"})

    existente = db.query(CardapioItem).filter(
        CardapioItem.unidade_id == unidade_id,
        CardapioItem.produto_id == dados.produto_id,
    ).first()
    if existente:
        raise HTTPException(409, detail={"erro": "JA_EXISTE", "mensagem": "Produto já está no cardápio"})

    item = CardapioItem(
        unidade_id=unidade_id,
        produto_id=dados.produto_id,
        preco_local=dados.preco_local,
        disponivel=dados.disponivel,
    )
    db.add(item)
    db.commit()
    return {"mensagem": "Produto adicionado ao cardápio com sucesso"}
