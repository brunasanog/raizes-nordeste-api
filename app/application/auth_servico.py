from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.config import config
from app.domain.models import Usuario, PerfilUsuario
from app.infrastructure.database.conexao import obter_sessao

_contexto_senha = CryptContext(schemes=["bcrypt"], deprecated="auto")
_bearer = HTTPBearer()


def hash_senha(senha: str) -> str:
    return _contexto_senha.hash(senha)


def verificar_senha(senha_plana: str, hash_: str) -> bool:
    return _contexto_senha.verify(senha_plana, hash_)


def gerar_token(dados: dict, expiracao_minutos: int = None) -> str:
    exp = expiracao_minutos or config.token_expiracao_minutos
    payload = dados.copy()
    payload["exp"] = datetime.utcnow() + timedelta(minutes=exp)
    return jwt.encode(payload, config.secret_key, algorithm=config.algoritmo_jwt)


def decodificar_token(token: str) -> dict:
    try:
        return jwt.decode(token, config.secret_key, algorithms=[config.algoritmo_jwt])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"erro": "TOKEN_INVALIDO", "mensagem": "Token inválido ou expirado"},
        )


def _extrair_usuario_atual(
    credenciais: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(obter_sessao),
) -> Usuario:
    payload = decodificar_token(credenciais.credentials)
    usuario_id: Optional[int] = payload.get("sub")
    if usuario_id is None:
        raise HTTPException(status_code=401, detail={"erro": "TOKEN_INVALIDO"})

    usuario = db.query(Usuario).filter(Usuario.id == int(usuario_id), Usuario.ativo == True).first()
    if not usuario:
        raise HTTPException(status_code=401, detail={"erro": "USUARIO_NAO_ENCONTRADO"})
    return usuario


def usuario_atual(usuario: Usuario = Depends(_extrair_usuario_atual)) -> Usuario:
    return usuario


def exigir_perfis(*perfis: PerfilUsuario):
    """Fábrica de dependências para controle de acesso por perfil."""
    def verificador(usuario: Usuario = Depends(usuario_atual)) -> Usuario:
        if usuario.perfil not in perfis:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "erro": "SEM_PERMISSAO",
                    "mensagem": f"Perfil '{usuario.perfil}' não tem acesso a este recurso",
                },
            )
        return usuario
    return verificador
