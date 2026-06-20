"""
Seed inicial: cria dados de demonstração para avaliação/testes.
Execute: python seed.py
"""
from app.infrastructure.database.conexao import SessionLocal
from app.domain.models import (
    Base, Usuario, Unidade, Produto, Estoque, CardapioItem,
    PerfilUsuario
)
from app.application.auth_servico import hash_senha
from app.infrastructure.database.conexao import engine


def rodar():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        if db.query(Usuario).count() > 0:
            print("Seed já foi executado anteriormente. Nada feito.")
            return

        # ── Usuários ──────────────────────────────────────────────────────────
        usuarios = [
            Usuario(nome="Admin Raízes", email="admin@raizes.com",
                    senha_hash=hash_senha("Admin@123"), perfil=PerfilUsuario.ADMIN,
                    consentimento_lgpd=True),
            Usuario(nome="Gerente Recife", email="gerente@raizes.com",
                    senha_hash=hash_senha("Gerente@123"), perfil=PerfilUsuario.GERENTE,
                    consentimento_lgpd=True),
            Usuario(nome="Atendente João", email="atendente@raizes.com",
                    senha_hash=hash_senha("Atende@123"), perfil=PerfilUsuario.ATENDENTE,
                    consentimento_lgpd=True),
            Usuario(nome="Cozinha Maria", email="cozinha@raizes.com",
                    senha_hash=hash_senha("Cozinha@123"), perfil=PerfilUsuario.COZINHA,
                    consentimento_lgpd=True),
            Usuario(nome="Cliente Teste", email="cliente@raizes.com",
                    senha_hash=hash_senha("Cliente@123"), perfil=PerfilUsuario.CLIENTE,
                    consentimento_lgpd=True),
        ]
        db.add_all(usuarios)
        db.flush()

        # ── Fidelidade para o cliente ─────────────────────────────────────────
        from app.domain.models import PontosFidelidade
        db.add(PontosFidelidade(usuario_id=usuarios[4].id, saldo=120, total_acumulado=120))

        # ── Unidades ──────────────────────────────────────────────────────────
        unidades = [
            Unidade(nome="Raízes Recife Centro", cidade="Recife", estado="PE",
                    endereco="Rua da Aurora, 100", cozinha_completa=True),
            Unidade(nome="Raízes Fortaleza Aldeota", cidade="Fortaleza", estado="CE",
                    endereco="Av. Santos Dumont, 200", cozinha_completa=True),
            Unidade(nome="Raízes Natal Express", cidade="Natal", estado="RN",
                    endereco="Via Costeira, 50", cozinha_completa=False),
        ]
        db.add_all(unidades)
        db.flush()

        # ── Produtos ──────────────────────────────────────────────────────────
        produtos = [
            Produto(nome="Tapioca Nordestina", descricao="Tapioca com queijo coalho e manteiga de garrafa",
                    preco=12.90, categoria="Tapioca"),
            Produto(nome="Cuscuz Recheado", descricao="Cuscuz com ovo, carne seca e queijo",
                    preco=15.50, categoria="Cuscuz"),
            Produto(nome="Bolo de Macaxeira", descricao="Bolo tradicional de macaxeira com coco",
                    preco=8.00, categoria="Bolo"),
            Produto(nome="Café Passado na Hora", descricao="Café coado fresco",
                    preco=5.00, categoria="Bebida"),
            Produto(nome="Suco de Umbu", descricao="Suco natural de umbu",
                    preco=7.50, categoria="Bebida"),
            Produto(nome="Canjica Junina", descricao="Canjica especial de época junina",
                    preco=9.00, categoria="Doce", disponivel_periodo_junino=True),
        ]
        db.add_all(produtos)
        db.flush()

        # ── Cardápio por unidade ───────────────────────────────────────────────
        # Unidade 1 (Recife) — cardápio completo
        for p in produtos:
            db.add(CardapioItem(
                unidade_id=unidades[0].id,
                produto_id=p.id,
                disponivel=True,
            ))

        # Unidade 2 (Fortaleza) — todos menos canjica
        for p in produtos[:5]:
            db.add(CardapioItem(
                unidade_id=unidades[1].id,
                produto_id=p.id,
                disponivel=True,
            ))

        # Unidade 3 (Natal Express) — apenas fast items
        for p in [produtos[0], produtos[3], produtos[4]]:
            db.add(CardapioItem(
                unidade_id=unidades[2].id,
                produto_id=p.id,
                disponivel=True,
            ))

        db.flush()

        # ── Estoque ────────────────────────────────────────────────────────────
        estoques = [
            # Recife
            Estoque(unidade_id=unidades[0].id, produto_id=produtos[0].id, quantidade=50),
            Estoque(unidade_id=unidades[0].id, produto_id=produtos[1].id, quantidade=30),
            Estoque(unidade_id=unidades[0].id, produto_id=produtos[2].id, quantidade=20),
            Estoque(unidade_id=unidades[0].id, produto_id=produtos[3].id, quantidade=100),
            Estoque(unidade_id=unidades[0].id, produto_id=produtos[4].id, quantidade=40),
            Estoque(unidade_id=unidades[0].id, produto_id=produtos[5].id, quantidade=15),
            # Fortaleza
            Estoque(unidade_id=unidades[1].id, produto_id=produtos[0].id, quantidade=35),
            Estoque(unidade_id=unidades[1].id, produto_id=produtos[1].id, quantidade=20),
            Estoque(unidade_id=unidades[1].id, produto_id=produtos[3].id, quantidade=80),
            # Natal
            Estoque(unidade_id=unidades[2].id, produto_id=produtos[0].id, quantidade=25),
            Estoque(unidade_id=unidades[2].id, produto_id=produtos[3].id, quantidade=60),
        ]
        db.add_all(estoques)
        db.commit()

        print("✅ Seed executado com sucesso!")
        print("\n📋 Usuários criados:")
        print("  admin@raizes.com     → Admin@123   (ADMIN)")
        print("  gerente@raizes.com   → Gerente@123 (GERENTE)")
        print("  atendente@raizes.com → Atende@123  (ATENDENTE)")
        print("  cozinha@raizes.com   → Cozinha@123 (COZINHA)")
        print("  cliente@raizes.com   → Cliente@123 (CLIENTE)")

    except Exception as e:
        db.rollback()
        print(f"❌ Erro no seed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    rodar()
