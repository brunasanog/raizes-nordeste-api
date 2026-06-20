from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.domain.models import Usuario, PerfilUsuario
from app.domain.schemas import UsuarioSaida, UsuarioAtualizar
from app.application.auth_servico import exigir_perfis
from app.application.auditoria_servico import registrar
from app.infrastructure.database.conexao import obter_sessao

router = APIRouter(prefix="/usuarios", tags=["Usuários"])

_apenas_admin = exigir_perfis(PerfilUsuario.ADMIN)


@router.get("/", response_model=list[UsuarioSaida], summary="Listar usuários (Admin)")
def listar(
    pagina: int = Query(1, ge=1),
    limite: int = Query(10, ge=1, le=100),
    db: Session = Depends(obter_sessao),
    _: Usuario = Depends(_apenas_admin),
):
    offset = (pagina - 1) * limite
    return db.query(Usuario).offset(offset).limit(limite).all()


@router.get("/{usuario_id}", response_model=UsuarioSaida, summary="Buscar usuário por ID (Admin)")
def buscar(
    usuario_id: int,
    db: Session = Depends(obter_sessao),
    _: Usuario = Depends(_apenas_admin),
):
    u = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not u:
        raise HTTPException(404, detail={"erro": "NAO_ENCONTRADO", "mensagem": "Usuário não existe"})
    return u


@router.patch("/{usuario_id}", response_model=UsuarioSaida, summary="Atualizar usuário (Admin)")
def atualizar(
    usuario_id: int,
    dados: UsuarioAtualizar,
    db: Session = Depends(obter_sessao),
    admin: Usuario = Depends(_apenas_admin),
):
    u = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not u:
        raise HTTPException(404, detail={"erro": "NAO_ENCONTRADO", "mensagem": "Usuário não existe"})

    for campo, valor in dados.model_dump(exclude_none=True).items():
        setattr(u, campo, valor)
    db.commit()
    db.refresh(u)

    registrar(db, "ATUALIZACAO_USUARIO", "usuarios", usuario_id, usuario_id=admin.id,
              detalhes=str(dados.model_dump(exclude_none=True)))
    return u
