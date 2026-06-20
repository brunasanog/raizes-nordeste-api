from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.domain.models import Produto, PerfilUsuario, Usuario
from app.domain.schemas import ProdutoCriar, ProdutoSaida
from app.application.auth_servico import exigir_perfis, usuario_atual
from app.infrastructure.database.conexao import obter_sessao

router = APIRouter(prefix="/produtos", tags=["Produtos"])

_gerente_admin = exigir_perfis(PerfilUsuario.GERENTE, PerfilUsuario.ADMIN)


@router.get("/", response_model=list[ProdutoSaida], summary="Listar produtos")
def listar(
    pagina: int = Query(1, ge=1),
    limite: int = Query(20, ge=1, le=100),
    categoria: str = Query(None),
    db: Session = Depends(obter_sessao),
    _: Usuario = Depends(usuario_atual),
):
    q = db.query(Produto).filter(Produto.ativo == True)
    if categoria:
        q = q.filter(Produto.categoria == categoria)
    return q.offset((pagina - 1) * limite).limit(limite).all()


@router.post("/", response_model=ProdutoSaida, status_code=201, summary="Criar produto (Gerente/Admin)")
def criar(
    dados: ProdutoCriar,
    db: Session = Depends(obter_sessao),
    _: Usuario = Depends(_gerente_admin),
):
    novo = Produto(**dados.model_dump())
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return novo


@router.get("/{produto_id}", response_model=ProdutoSaida, summary="Buscar produto por ID")
def buscar(
    produto_id: int,
    db: Session = Depends(obter_sessao),
    _: Usuario = Depends(usuario_atual),
):
    p = db.query(Produto).filter(Produto.id == produto_id, Produto.ativo == True).first()
    if not p:
        raise HTTPException(404, detail={"erro": "NAO_ENCONTRADO", "mensagem": "Produto não encontrado"})
    return p


@router.patch("/{produto_id}", response_model=ProdutoSaida, summary="Atualizar produto (Gerente/Admin)")
def atualizar(
    produto_id: int,
    dados: ProdutoCriar,
    db: Session = Depends(obter_sessao),
    _: Usuario = Depends(_gerente_admin),
):
    p = db.query(Produto).filter(Produto.id == produto_id, Produto.ativo == True).first()
    if not p:
        raise HTTPException(404, detail={"erro": "NAO_ENCONTRADO", "mensagem": "Produto não encontrado"})
    for campo, valor in dados.model_dump().items():
        setattr(p, campo, valor)
    db.commit()
    db.refresh(p)
    return p


@router.delete("/{produto_id}", status_code=204, summary="Desativar produto (Admin)")
def desativar(
    produto_id: int,
    db: Session = Depends(obter_sessao),
    _: Usuario = Depends(exigir_perfis(PerfilUsuario.ADMIN)),
):
    p = db.query(Produto).filter(Produto.id == produto_id).first()
    if not p:
        raise HTTPException(404, detail={"erro": "NAO_ENCONTRADO", "mensagem": "Produto não encontrado"})
    p.ativo = False
    db.commit()
