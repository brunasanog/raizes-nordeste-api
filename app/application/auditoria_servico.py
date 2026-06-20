from typing import Optional
from sqlalchemy.orm import Session
from app.domain.models import LogAuditoria


def registrar(
    db: Session,
    acao: str,
    recurso: Optional[str] = None,
    recurso_id: Optional[int] = None,
    usuario_id: Optional[int] = None,
    detalhes: Optional[str] = None,
    ip: Optional[str] = None,
) -> None:
    """Registra uma ação sensível no log de auditoria."""
    entrada = LogAuditoria(
        usuario_id=usuario_id,
        acao=acao,
        recurso=recurso,
        recurso_id=recurso_id,
        detalhes=detalhes,
        ip=ip,
    )
    db.add(entrada)
    db.commit()
