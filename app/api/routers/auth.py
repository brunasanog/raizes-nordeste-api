from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.domain.models import Usuario, PontosFidelidade
from app.domain.schemas import LoginEntrada, TokenSaida, UsuarioCriar, UsuarioSaida, UsuarioResumido
from app.application.auth_servico import hash_senha, verificar_senha, gerar_token, usuario_atual
from app.application.auditoria_servico import registrar
from app.infrastructure.database.conexao import obter_sessao
from app.config import config

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/cadastro", response_model=UsuarioSaida, status_code=201,
             summary="Cadastrar novo usuário")
def cadastrar(entrada: UsuarioCriar, request: Request, db: Session = Depends(obter_sessao)):
    existente = db.query(Usuario).filter(Usuario.email == entrada.email).first()
    if existente:
        raise HTTPException(
            status_code=409,
            detail={"erro": "EMAIL_JA_CADASTRADO", "mensagem": "E-mail já está em uso"},
        )
    novo = Usuario(
        nome=entrada.nome,
        email=entrada.email,
        senha_hash=hash_senha(entrada.senha),
        consentimento_lgpd=entrada.consentimento_lgpd,
    )
    db.add(novo)
    db.flush()

    db.add(PontosFidelidade(usuario_id=novo.id))
    db.commit()
    db.refresh(novo)

    registrar(db, "CADASTRO_USUARIO", "usuarios", novo.id,
              ip=request.client.host if request.client else None)
    return novo


@router.post("/login", response_model=TokenSaida, summary="Autenticar e obter token JWT")
def login(entrada: LoginEntrada, request: Request, db: Session = Depends(obter_sessao)):
    usuario = db.query(Usuario).filter(
        Usuario.email == entrada.email, Usuario.ativo == True
    ).first()

    if not usuario or not verificar_senha(entrada.senha, usuario.senha_hash):
        raise HTTPException(
            status_code=401,
            detail={"erro": "CREDENCIAIS_INVALIDAS", "mensagem": "E-mail ou senha inválidos"},
        )

    token = gerar_token({"sub": str(usuario.id), "perfil": usuario.perfil.value})
    registrar(db, "LOGIN", "usuarios", usuario.id, usuario_id=usuario.id,
              ip=request.client.host if request.client else None)

    return TokenSaida(
        access_token=token,
        expira_em=config.token_expiracao_minutos * 60,
        usuario=UsuarioResumido.model_validate(usuario),
    )


@router.get("/perfil", response_model=UsuarioSaida, summary="Ver perfil do usuário logado")
def ver_perfil(usuario: Usuario = Depends(usuario_atual)):
    return usuario
