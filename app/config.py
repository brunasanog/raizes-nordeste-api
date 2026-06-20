from pydantic_settings import BaseSettings


class Configuracoes(BaseSettings):
    app_nome: str = "Raízes do Nordeste API"
    app_versao: str = "1.0.0"
    secret_key: str = "raizes-nordeste-chave-secreta-2026-troque-em-producao"
    algoritmo_jwt: str = "HS256"
    token_expiracao_minutos: int = 60
    database_url: str = "sqlite:///./raizes_nordeste.db"
    ambiente: str = "desenvolvimento"

    class Config:
        env_file = ".env"


config = Configuracoes()
