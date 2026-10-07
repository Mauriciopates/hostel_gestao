"""Relatórios da área Contratos: ocupações, contratos mensais,
reservas Airbnb e encerramentos."""

from datetime import date

import customtkinter as ctk

import clientes
import contratos
import unidades

from .. import componentes
from .. import tema
from . import gui_relat_comum
from .gui_relat_base import RelatorioBase

# Helpers partilhados — alias local, mesmo padrão do
# gui_est_aprovacao.py (nomes públicos em gui_relat_comum).
_formatar_data = gui_relat_comum.formatar_data
_formatar_valor = gui_relat_comum.formatar_valor
_mapa_por_id = gui_relat_comum.mapa_por_id
_celula_entidade = gui_relat_comum.celula_entidade


class RelatContratos(RelatorioBase):
    """Relatórios da área Contratos: ocupações, contratos mensais,
    reservas Airbnb e encerramentos.

    Só desenhadores `_desenhar_<id>` e os seus auxiliares. A base
    chama-os por `getattr` em `_recarregar_conteudo`; a classe
    final `RelatorioModal` (gui_relat_hub.py) junta as três áreas.
    """

    # =================================================================
    # RELATÓRIOS — ÁREA CONTRATOS
    # =================================================================

    # -- 6. OCUPAÇÕES NO PERÍODO --------------------------------------

    def _desenhar_ocupacoes(self, master):
        """Relatório "Ocupações no período" — listagem de registos
        individuais. Sem total.
        """
        tocadas = contratos.listar(
            incluir_inativas=True,
            data_inicio=self.data_inicio,
            data_fim=self.data_fim,
        )

        # Ordena por data de início, mais recentes primeiro.
        tocadas.sort(
            key=lambda o: o["data_inicio"] or date.min,
            reverse=True,
        )

        # Mapas de unidades e clientes — uma leitura só cada, em
        # memória.
        mapa_unidades = _mapa_por_id(unidades.listar(incluir_inativas=True))
        mapa_clientes = _mapa_por_id(clientes.listar(incluir_inativos=True))

        self._titulo_relatorio(master, "Ocupações no período")

        colunas = (
            componentes.Coluna("ID", minimo=110, espaco=6),
            componentes.Coluna("Unidade", peso=3, minimo=180),
            componentes.Coluna("Cliente", peso=3, minimo=160),
            componentes.Coluna("Tipo", minimo=80, alinhamento="centro"),
            componentes.Coluna("Início", minimo=100, alinhamento="centro"),
            componentes.Coluna("Fim", minimo=100, alinhamento="centro"),
            componentes.Coluna("Estado", minimo=100, alinhamento="centro"),
            componentes.Coluna(
                "Aviso doc.", minimo=100, alinhamento="centro", espaco=8
            ),
        )

        tabela = componentes.Tabela(
            master,
            rolagem_horizontal=True,
            colunas=colunas,
            altura_linha=52,
            mensagem_vazia="Sem ocupações no período.",
            tom_alternado=True,
        )
        tabela.pack(fill="x")

        if not tocadas:
            tabela.mostrar_vazio()
            self._rodape_export(
                master,
                "ocupacoes",
                colunas=(
                    "ID",
                    "Unidade",
                    "Cliente",
                    "Tipo",
                    "Início",
                    "Fim",
                    "Estado",
                    "Aviso doc.",
                ),
                linhas=[],
            )
            return

        linhas_export = []
        for ocupacao in tocadas:
            unidade = mapa_unidades.get(ocupacao["unidade_id"])
            cliente = mapa_clientes.get(ocupacao["cliente_id"])
            nome_unidade = (
                unidade["nome"] if unidade else ocupacao["unidade_id"]
            )
            nome_cliente = (
                cliente["nome"] if cliente else ocupacao["cliente_id"]
            )

            estado = "ativo" if ocupacao["ativo"] else "encerrado"
            cor_estado = (
                tema.TEXTO_LIVRE
                if ocupacao["ativo"]
                else tema.TEXTO_INDISPONIVEL
            )
            fundo_estado = (
                tema.VERDE_LIVRE
                if ocupacao["ativo"]
                else tema.CINZA_INDISPONIVEL
            )

            linha = tabela.nova_linha()

            tabela.colocar(
                linha,
                0,
                ctk.CTkLabel(
                    linha,
                    text=ocupacao["id"],
                    text_color=tema.AZUL_PRINCIPAL,
                    fg_color=tema.ID_CHIP_FUNDO,
                    corner_radius=6,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    anchor="w",
                ),
            )

            tabela.colocar(
                linha,
                1,
                ctk.CTkLabel(
                    linha,
                    text=_celula_entidade(
                        nome_unidade, ocupacao["unidade_id"]
                    ),
                    text_color=tema.COR_TEXTO,
                    font=ctk.CTkFont(size=11),
                    anchor="w",
                    justify="left",
                ),
            )

            tabela.colocar(
                linha,
                2,
                ctk.CTkLabel(
                    linha,
                    text=_celula_entidade(
                        nome_cliente, ocupacao["cliente_id"]
                    ),
                    text_color=tema.COR_TEXTO,
                    font=ctk.CTkFont(size=11),
                    anchor="w",
                    justify="left",
                ),
            )

            tabela.colocar(
                linha,
                3,
                ctk.CTkLabel(
                    linha,
                    text=ocupacao["tipo"],
                    text_color=tema.COR_TEXTO_SECUNDARIO,
                    font=ctk.CTkFont(size=11),
                    anchor="center",
                ),
            )

            tabela.colocar(
                linha,
                4,
                ctk.CTkLabel(
                    linha,
                    text=_formatar_data(ocupacao["data_inicio"]),
                    text_color=tema.COR_TEXTO_SECUNDARIO,
                    font=ctk.CTkFont(size=11),
                    anchor="center",
                ),
            )

            tabela.colocar(
                linha,
                5,
                ctk.CTkLabel(
                    linha,
                    text=_formatar_data(ocupacao["data_fim"]),
                    text_color=tema.COR_TEXTO_SECUNDARIO,
                    font=ctk.CTkFont(size=11),
                    anchor="center",
                ),
            )

            tabela.colocar(
                linha,
                6,
                ctk.CTkLabel(
                    linha,
                    text=estado,
                    text_color=cor_estado,
                    fg_color=fundo_estado,
                    corner_radius=6,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    anchor="center",
                ),
            )

            tabela.colocar(
                linha,
                7,
                ctk.CTkLabel(
                    linha,
                    text="⚠ doc." if ocupacao["aviso_documento"] else "",
                    text_color=tema.TEXTO_AVISO,
                    fg_color=(
                        tema.AMARELO_AVISO
                        if ocupacao["aviso_documento"]
                        else "transparent"
                    ),
                    corner_radius=6,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    anchor="center",
                ),
            )

            linhas_export.append(
                [
                    ocupacao["id"],
                    f"{nome_unidade} ({ocupacao['unidade_id']})",
                    f"{nome_cliente} ({ocupacao['cliente_id']})",
                    ocupacao["tipo"],
                    ocupacao["data_inicio"],
                    ocupacao["data_fim"],
                    estado,
                    "Sim" if ocupacao["aviso_documento"] else "Não",
                ]
            )

        self._rodape_export(
            master,
            "ocupacoes",
            colunas=(
                "ID",
                "Unidade",
                "Cliente",
                "Tipo",
                "Início",
                "Fim",
                "Estado",
                "Aviso doc.",
            ),
            linhas=linhas_export,
        )

    # -- 7. CONTRATOS MENSAIS -----------------------------------------

    def _desenhar_contratos_mensais(self, master):
        """Relatório "Contratos mensais" — colunas específicas do
        regime mensal (renda, caução, vencimento, autorização).
        """
        tocadas = contratos.listar(
            incluir_inativas=True, tipo="mensal",
            data_inicio=self.data_inicio,
            data_fim=self.data_fim,
        )
        tocadas.sort(
            key=lambda o: o["data_inicio"] or date.min,
            reverse=True,
        )

        mapa_unidades = _mapa_por_id(unidades.listar(incluir_inativas=True))
        mapa_clientes = _mapa_por_id(clientes.listar(incluir_inativos=True))

        self._titulo_relatorio(master, "Contratos mensais")

        colunas = (
            componentes.Coluna("ID", minimo=100, espaco=6),
            componentes.Coluna("Unidade", peso=2, minimo=150),
            componentes.Coluna("Cliente", peso=2, minimo=140),
            componentes.Coluna("Início", minimo=95, alinhamento="centro"),
            componentes.Coluna("Fim", minimo=95, alinhamento="centro"),
            componentes.Coluna("Renda calc.", minimo=100, alinhamento="e"),
            componentes.Coluna("Renda prat.", minimo=100, alinhamento="e"),
            componentes.Coluna("Caução", minimo=95, alinhamento="e"),
            componentes.Coluna("Venc.", minimo=60, alinhamento="centro"),
            componentes.Coluna("Autoriz.", minimo=90, alinhamento="centro"),
            componentes.Coluna(
                "Estado", minimo=95, alinhamento="centro", espaco=8
            ),
        )

        tabela = componentes.Tabela(
            master,
            rolagem_horizontal=True,
            colunas=colunas,
            altura_linha=52,
            mensagem_vazia="Sem contratos mensais no período.",
            tom_alternado=True,
        )
        tabela.pack(fill="x")

        if not tocadas:
            tabela.mostrar_vazio()
            self._rodape_export(
                master,
                "contratos_mensais",
                colunas=tuple(c.titulo for c in colunas),
                linhas=[],
            )
            return

        linhas_export = []
        for ocupacao in tocadas:
            mensal = contratos.detalhes_mensal(ocupacao["id"])
            if mensal is None:
                # Inconsistência nos dados — salta em vez de rebentar.
                continue

            unidade = mapa_unidades.get(ocupacao["unidade_id"])
            cliente = mapa_clientes.get(ocupacao["cliente_id"])
            nome_unidade = (
                unidade["nome"] if unidade else ocupacao["unidade_id"]
            )
            nome_cliente = (
                cliente["nome"] if cliente else ocupacao["cliente_id"]
            )

            renda_calc = mensal["renda_calculada"]
            renda_prat = mensal["renda_praticada"]
            tem_desconto = renda_prat < renda_calc

            linha = tabela.nova_linha()

            tabela.colocar(
                linha,
                0,
                ctk.CTkLabel(
                    linha,
                    text=ocupacao["id"],
                    text_color=tema.AZUL_PRINCIPAL,
                    fg_color=tema.ID_CHIP_FUNDO,
                    corner_radius=6,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    anchor="w",
                ),
            )

            tabela.colocar(
                linha,
                1,
                ctk.CTkLabel(
                    linha,
                    text=_celula_entidade(
                        nome_unidade, ocupacao["unidade_id"]
                    ),
                    text_color=tema.COR_TEXTO,
                    font=ctk.CTkFont(size=11),
                    anchor="w",
                    justify="left",
                ),
            )

            tabela.colocar(
                linha,
                2,
                ctk.CTkLabel(
                    linha,
                    text=nome_cliente,
                    text_color=tema.COR_TEXTO,
                    font=ctk.CTkFont(size=11),
                    anchor="w",
                    justify="left",
                ),
            )

            tabela.colocar(
                linha,
                3,
                ctk.CTkLabel(
                    linha,
                    text=_formatar_data(ocupacao["data_inicio"]),
                    text_color=tema.COR_TEXTO_SECUNDARIO,
                    font=ctk.CTkFont(size=11),
                    anchor="center",
                ),
            )

            tabela.colocar(
                linha,
                4,
                ctk.CTkLabel(
                    linha,
                    text=_formatar_data(ocupacao["data_fim"]),
                    text_color=tema.COR_TEXTO_SECUNDARIO,
                    font=ctk.CTkFont(size=11),
                    anchor="center",
                ),
            )

            tabela.colocar(
                linha,
                5,
                ctk.CTkLabel(
                    linha,
                    text=_formatar_valor(renda_calc),
                    text_color=tema.COR_TEXTO,
                    font=ctk.CTkFont(size=11),
                    anchor="e",
                ),
            )

            tabela.colocar(
                linha,
                6,
                ctk.CTkLabel(
                    linha,
                    text=_formatar_valor(renda_prat),
                    text_color=(
                        tema.TEXTO_ERRO if tem_desconto else tema.COR_TEXTO
                    ),
                    font=ctk.CTkFont(size=11),
                    anchor="e",
                ),
            )

            tabela.colocar(
                linha,
                7,
                ctk.CTkLabel(
                    linha,
                    text=_formatar_valor(mensal["caucao"]),
                    text_color=tema.COR_TEXTO,
                    font=ctk.CTkFont(size=11),
                    anchor="e",
                ),
            )

            tabela.colocar(
                linha,
                8,
                ctk.CTkLabel(
                    linha,
                    text=str(mensal["dia_vencimento"]),
                    text_color=tema.COR_TEXTO_SECUNDARIO,
                    font=ctk.CTkFont(size=11),
                    anchor="center",
                ),
            )

            tabela.colocar(
                linha,
                9,
                ctk.CTkLabel(
                    linha,
                    text=(
                        mensal["responsavel_desconto_renda_id"]
                        if tem_desconto
                        else ""
                    ),
                    text_color=tema.AZUL_PRINCIPAL,
                    fg_color=(
                        tema.ID_CHIP_FUNDO if tem_desconto else "transparent"
                    ),
                    corner_radius=6,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    anchor="center",
                ),
            )

            tabela.colocar(
                linha,
                10,
                ctk.CTkLabel(
                    linha,
                    text="ativo" if ocupacao["ativo"] else "encerrado",
                    text_color=(
                        tema.TEXTO_LIVRE
                        if ocupacao["ativo"]
                        else tema.TEXTO_INDISPONIVEL
                    ),
                    fg_color=(
                        tema.VERDE_LIVRE
                        if ocupacao["ativo"]
                        else tema.CINZA_INDISPONIVEL
                    ),
                    corner_radius=6,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    anchor="center",
                ),
            )

            linhas_export.append(
                [
                    ocupacao["id"],
                    f"{nome_unidade} ({ocupacao['unidade_id']})",
                    nome_cliente,
                    ocupacao["data_inicio"],
                    ocupacao["data_fim"],
                    renda_calc,
                    renda_prat,
                    mensal["caucao"],
                    mensal["dia_vencimento"],
                    (
                        mensal["responsavel_desconto_renda_id"]
                        if tem_desconto
                        else ""
                    ),
                    "ativo" if ocupacao["ativo"] else "encerrado",
                ]
            )

        self._rodape_export(
            master,
            "contratos_mensais",
            colunas=tuple(c.titulo for c in colunas),
            linhas=linhas_export,
        )

    # -- 8. RESERVAS AIRBNB -------------------------------------------

    def _desenhar_reservas_airbnb(self, master):
        """Relatório "Reservas Airbnb" — colunas específicas do
        regime airbnb (preço, check-in tardio, multas, autorizações).
        """
        tocadas = contratos.listar(
            incluir_inativas=True, tipo="airbnb",
            data_inicio=self.data_inicio,
            data_fim=self.data_fim,
        )
        tocadas.sort(
            key=lambda o: o["data_inicio"] or date.min,
            reverse=True,
        )

        mapa_unidades = _mapa_por_id(unidades.listar(incluir_inativas=True))
        mapa_clientes = _mapa_por_id(clientes.listar(incluir_inativos=True))

        self._titulo_relatorio(master, "Reservas Airbnb")

        colunas = (
            componentes.Coluna("ID", minimo=95, espaco=6),
            componentes.Coluna("Unidade", peso=2, minimo=140),
            componentes.Coluna("Cliente", peso=2, minimo=130),
            componentes.Coluna("Início", minimo=95, alinhamento="centro"),
            componentes.Coluna("Fim", minimo=95, alinhamento="centro"),
            componentes.Coluna("Preço calc.", minimo=100, alinhamento="e"),
            componentes.Coluna("Preço prat.", minimo=100, alinhamento="e"),
            componentes.Coluna("Check-in", minimo=85, alinhamento="centro"),
            componentes.Coluna("Hora", minimo=60, alinhamento="centro"),
            componentes.Coluna("Multa calc.", minimo=95, alinhamento="e"),
            componentes.Coluna("Multa prat.", minimo=95, alinhamento="e"),
            componentes.Coluna("Aut. preço", minimo=90, alinhamento="centro"),
            componentes.Coluna("Aut. multa", minimo=90, alinhamento="centro"),
            componentes.Coluna(
                "Estado", minimo=90, alinhamento="centro", espaco=8
            ),
        )

        tabela = componentes.Tabela(
            master,
            rolagem_horizontal=True,
            colunas=colunas,
            altura_linha=52,
            mensagem_vazia="Sem reservas Airbnb no período.",
            tom_alternado=True,
        )
        tabela.pack(fill="x")

        if not tocadas:
            tabela.mostrar_vazio()
            self._rodape_export(
                master,
                "reservas_airbnb",
                colunas=tuple(c.titulo for c in colunas),
                linhas=[],
            )
            return

        linhas_export = []
        for ocupacao in tocadas:
            airbnb = contratos.detalhes_airbnb(ocupacao["id"])
            if airbnb is None:
                continue

            unidade = mapa_unidades.get(ocupacao["unidade_id"])
            cliente = mapa_clientes.get(ocupacao["cliente_id"])
            nome_unidade = (
                unidade["nome"] if unidade else ocupacao["unidade_id"]
            )
            nome_cliente = (
                cliente["nome"] if cliente else ocupacao["cliente_id"]
            )

            preco_calc = airbnb["preco_calculado"]
            preco_prat = airbnb["preco_praticado"]
            tem_desc_preco = preco_prat < preco_calc

            tem_checkin_tardio = airbnb["check_in_tardio"]
            multa_calc = airbnb["multa_calculada"]
            multa_prat = airbnb["multa_praticada"]
            tem_desc_multa = tem_checkin_tardio and multa_prat < multa_calc

            linha = tabela.nova_linha()

            # Colunas 0-5
            tabela.colocar(
                linha,
                0,
                ctk.CTkLabel(
                    linha,
                    text=ocupacao["id"],
                    text_color=tema.AZUL_PRINCIPAL,
                    fg_color=tema.ID_CHIP_FUNDO,
                    corner_radius=6,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    anchor="w",
                ),
            )
            tabela.colocar(
                linha,
                1,
                ctk.CTkLabel(
                    linha,
                    text=_celula_entidade(
                        nome_unidade, ocupacao["unidade_id"]
                    ),
                    text_color=tema.COR_TEXTO,
                    font=ctk.CTkFont(size=11),
                    anchor="w",
                    justify="left",
                ),
            )
            tabela.colocar(
                linha,
                2,
                ctk.CTkLabel(
                    linha,
                    text=nome_cliente,
                    text_color=tema.COR_TEXTO,
                    font=ctk.CTkFont(size=11),
                    anchor="w",
                    justify="left",
                ),
            )
            tabela.colocar(
                linha,
                3,
                ctk.CTkLabel(
                    linha,
                    text=_formatar_data(ocupacao["data_inicio"]),
                    text_color=tema.COR_TEXTO_SECUNDARIO,
                    font=ctk.CTkFont(size=11),
                    anchor="center",
                ),
            )
            tabela.colocar(
                linha,
                4,
                ctk.CTkLabel(
                    linha,
                    text=_formatar_data(ocupacao["data_fim"]),
                    text_color=tema.COR_TEXTO_SECUNDARIO,
                    font=ctk.CTkFont(size=11),
                    anchor="center",
                ),
            )
            tabela.colocar(
                linha,
                5,
                ctk.CTkLabel(
                    linha,
                    text=_formatar_valor(preco_calc),
                    text_color=tema.COR_TEXTO,
                    font=ctk.CTkFont(size=11),
                    anchor="e",
                ),
            )
            tabela.colocar(
                linha,
                6,
                ctk.CTkLabel(
                    linha,
                    text=_formatar_valor(preco_prat),
                    text_color=(
                        tema.TEXTO_ERRO if tem_desc_preco else tema.COR_TEXTO
                    ),
                    font=ctk.CTkFont(size=11),
                    anchor="e",
                ),
            )

            # Check-in tardio + hora
            tabela.colocar(
                linha,
                7,
                ctk.CTkLabel(
                    linha,
                    text="tardio" if tem_checkin_tardio else "",
                    text_color=tema.TEXTO_AVISO,
                    fg_color=(
                        tema.AMARELO_AVISO
                        if tem_checkin_tardio
                        else "transparent"
                    ),
                    corner_radius=6,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    anchor="center",
                ),
            )
            tabela.colocar(
                linha,
                8,
                ctk.CTkLabel(
                    linha,
                    text=airbnb["hora_chegada"] or "—",
                    text_color=tema.COR_TEXTO_SECUNDARIO,
                    font=ctk.CTkFont(size=11),
                    anchor="center",
                ),
            )

            # Multas
            tabela.colocar(
                linha,
                9,
                ctk.CTkLabel(
                    linha,
                    text=(
                        _formatar_valor(multa_calc)
                        if tem_checkin_tardio
                        else "—"
                    ),
                    text_color=tema.COR_TEXTO,
                    font=ctk.CTkFont(size=11),
                    anchor="e",
                ),
            )
            tabela.colocar(
                linha,
                10,
                ctk.CTkLabel(
                    linha,
                    text=(
                        _formatar_valor(multa_prat)
                        if tem_checkin_tardio
                        else "—"
                    ),
                    text_color=(
                        tema.TEXTO_ERRO if tem_desc_multa else tema.COR_TEXTO
                    ),
                    font=ctk.CTkFont(size=11),
                    anchor="e",
                ),
            )

            # Autorizações
            tabela.colocar(
                linha,
                11,
                ctk.CTkLabel(
                    linha,
                    text=(
                        airbnb["responsavel_desconto_preco_id"]
                        if tem_desc_preco
                        else ""
                    ),
                    text_color=tema.AZUL_PRINCIPAL,
                    fg_color=(
                        tema.ID_CHIP_FUNDO if tem_desc_preco else "transparent"
                    ),
                    corner_radius=6,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    anchor="center",
                ),
            )
            tabela.colocar(
                linha,
                12,
                ctk.CTkLabel(
                    linha,
                    text=(
                        airbnb["responsavel_desconto_multa_id"]
                        if tem_desc_multa
                        else ""
                    ),
                    text_color=tema.AZUL_PRINCIPAL,
                    fg_color=(
                        tema.ID_CHIP_FUNDO if tem_desc_multa else "transparent"
                    ),
                    corner_radius=6,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    anchor="center",
                ),
            )

            tabela.colocar(
                linha,
                13,
                ctk.CTkLabel(
                    linha,
                    text="ativa" if ocupacao["ativo"] else "encerrada",
                    text_color=(
                        tema.TEXTO_LIVRE
                        if ocupacao["ativo"]
                        else tema.TEXTO_INDISPONIVEL
                    ),
                    fg_color=(
                        tema.VERDE_LIVRE
                        if ocupacao["ativo"]
                        else tema.CINZA_INDISPONIVEL
                    ),
                    corner_radius=6,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    anchor="center",
                ),
            )

            linhas_export.append(
                [
                    ocupacao["id"],
                    f"{nome_unidade} ({ocupacao['unidade_id']})",
                    nome_cliente,
                    ocupacao["data_inicio"],
                    ocupacao["data_fim"],
                    preco_calc,
                    preco_prat,
                    "Sim" if tem_checkin_tardio else "Não",
                    airbnb["hora_chegada"] or "",
                    multa_calc if tem_checkin_tardio else None,
                    multa_prat if tem_checkin_tardio else None,
                    (
                        airbnb["responsavel_desconto_preco_id"]
                        if tem_desc_preco
                        else ""
                    ),
                    (
                        airbnb["responsavel_desconto_multa_id"]
                        if tem_desc_multa
                        else ""
                    ),
                    "ativa" if ocupacao["ativo"] else "encerrada",
                ]
            )

        self._rodape_export(
            master,
            "reservas_airbnb",
            colunas=tuple(c.titulo for c in colunas),
            linhas=linhas_export,
        )

    # -- 9. ENCERRAMENTOS ---------------------------------------------

    def _desenhar_encerramentos(self, master):
        """Relatório "Encerramentos" — contratos mensais encerrados
        fora das regras da casa: duração abaixo do mínimo OU aviso
        prévio insuficiente.

        A flag `duracao_abaixo_minima` e `aviso_previo_insuficiente`
        já são gravadas pelo `contratos.encerrar_mensal`, no registo
        `ocupacoes_mensal`. Aqui só se filtram os que têm pelo menos
        uma das duas — o resto dos encerramentos (dentro das regras)
        não aparece.

        Listagem individual, sem total — como as outras listagens
        da área Contratos. A coluna Avisos mostra um chip por cada
        condição; um contrato pode ter os dois em simultâneo.
        """
        # ---- 1. Contratos com pelo menos um dos avisos, do fim
        # mais recente para o mais antigo (regra no contratos.py).
        candidatas = contratos.encerramentos_fora_das_regras()

        # ---- 4. Mapas de unidades e clientes — uma leitura só
        mapa_unidades = _mapa_por_id(unidades.listar(incluir_inativas=True))
        mapa_clientes = _mapa_por_id(clientes.listar(incluir_inativos=True))

        self._titulo_relatorio(master, "Encerramentos")

        colunas = (
            componentes.Coluna("ID", minimo=100, espaco=6),
            componentes.Coluna("Unidade", peso=2, minimo=150),
            componentes.Coluna("Cliente", peso=2, minimo=140),
            componentes.Coluna("Início", minimo=95, alinhamento="centro"),
            componentes.Coluna("Fim", minimo=95, alinhamento="centro"),
            componentes.Coluna("Duração", minimo=80, alinhamento="centro"),
            componentes.Coluna("Renda prat.", minimo=105, alinhamento="e"),
            componentes.Coluna("Motivo", peso=3, minimo=180),
            componentes.Coluna(
                "Avisos", minimo=150, alinhamento="centro", espaco=8
            ),
        )

        tabela = componentes.Tabela(
            master,
            rolagem_horizontal=True,
            colunas=colunas,
            altura_linha=52,
            mensagem_vazia="Sem encerramentos fora das regras no período.",
            tom_alternado=True,
        )
        tabela.pack(fill="x")

        if not candidatas:
            tabela.mostrar_vazio()
            self._rodape_export(
                master,
                "encerramentos",
                colunas=tuple(c.titulo for c in colunas),
                linhas=[],
            )
            return

        linhas_export = []

        for ocupacao, mensal in candidatas:
            unidade = mapa_unidades.get(ocupacao["unidade_id"])
            cliente = mapa_clientes.get(ocupacao["cliente_id"])
            nome_unidade = (
                unidade["nome"] if unidade else ocupacao["unidade_id"]
            )
            nome_cliente = (
                cliente["nome"] if cliente else ocupacao["cliente_id"]
            )

            # Duração em meses — a mesma fórmula da duração mínima.
            meses = contratos.duracao_meses(ocupacao)
            texto_duracao = f"{meses} mes" if meses == 1 else f"{meses} meses"

            texto_motivo = mensal["motivo_encerramento"] or "—"

            # Dois chips possíveis — um ou os dois podem estar
            # presentes. Desenhados num bloco horizontal, ao lado
            # um do outro, com uma folga pequena.
            linha = tabela.nova_linha()

            tabela.colocar(
                linha,
                0,
                ctk.CTkLabel(
                    linha,
                    text=ocupacao["id"],
                    text_color=tema.AZUL_PRINCIPAL,
                    fg_color=tema.ID_CHIP_FUNDO,
                    corner_radius=6,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    anchor="w",
                ),
            )

            tabela.colocar(
                linha,
                1,
                ctk.CTkLabel(
                    linha,
                    text=_celula_entidade(
                        nome_unidade, ocupacao["unidade_id"]
                    ),
                    text_color=tema.COR_TEXTO,
                    font=ctk.CTkFont(size=11),
                    anchor="w",
                    justify="left",
                ),
            )

            tabela.colocar(
                linha,
                2,
                ctk.CTkLabel(
                    linha,
                    text=nome_cliente,
                    text_color=tema.COR_TEXTO,
                    font=ctk.CTkFont(size=11),
                    anchor="w",
                    justify="left",
                ),
            )

            tabela.colocar(
                linha,
                3,
                ctk.CTkLabel(
                    linha,
                    text=_formatar_data(ocupacao["data_inicio"]),
                    text_color=tema.COR_TEXTO_SECUNDARIO,
                    font=ctk.CTkFont(size=11),
                    anchor="center",
                ),
            )

            tabela.colocar(
                linha,
                4,
                ctk.CTkLabel(
                    linha,
                    text=_formatar_data(ocupacao["data_fim"]),
                    text_color=tema.COR_TEXTO_SECUNDARIO,
                    font=ctk.CTkFont(size=11),
                    anchor="center",
                ),
            )

            tabela.colocar(
                linha,
                5,
                ctk.CTkLabel(
                    linha,
                    text=texto_duracao,
                    text_color=tema.COR_TEXTO_SECUNDARIO,
                    font=ctk.CTkFont(size=11),
                    anchor="center",
                ),
            )

            tabela.colocar(
                linha,
                6,
                ctk.CTkLabel(
                    linha,
                    text=_formatar_valor(mensal["renda_praticada"]),
                    text_color=tema.COR_TEXTO,
                    font=ctk.CTkFont(size=11),
                    anchor="e",
                ),
            )

            tabela.colocar(
                linha,
                7,
                ctk.CTkLabel(
                    linha,
                    text=texto_motivo,
                    text_color=tema.COR_TEXTO_SECUNDARIO,
                    font=ctk.CTkFont(size=10),
                    anchor="w",
                    justify="left",
                ),
            )

            # Bloco de chips de aviso. Dois podem estar ativos ao
            # mesmo tempo; a coluna tem 150px, cabem lado a lado.
            bloco_avisos = ctk.CTkFrame(
                linha, fg_color="transparent", height=24
            )
            bloco_avisos.pack_propagate(False)

            if mensal["duracao_abaixo_minima"]:
                ctk.CTkLabel(
                    bloco_avisos,
                    text="curto",
                    text_color=tema.TEXTO_AVISO,
                    fg_color=tema.AMARELO_AVISO,
                    corner_radius=6,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    padx=8,
                    pady=2,
                ).pack(side="left")

            if mensal["aviso_previo_insuficiente"]:
                ctk.CTkLabel(
                    bloco_avisos,
                    text="aviso",
                    text_color=tema.TEXTO_AVISO,
                    fg_color=tema.AMARELO_AVISO,
                    corner_radius=6,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    padx=8,
                    pady=2,
                ).pack(side="left", padx=(6, 0))

            tabela.colocar(linha, 8, bloco_avisos)

            linhas_export.append(
                [
                    ocupacao["id"],
                    f"{nome_unidade} ({ocupacao['unidade_id']})",
                    nome_cliente,
                    ocupacao["data_inicio"],
                    ocupacao["data_fim"],
                    texto_duracao,
                    mensal["renda_praticada"],
                    texto_motivo,
                    # Os avisos vão como texto simples para o CSV/
                    # Excel — o chip é só uma apresentação.
                    " / ".join(
                        filter(
                            None,
                            (
                                (
                                    "curto"
                                    if mensal["duracao_abaixo_minima"]
                                    else None
                                ),
                                (
                                    "aviso"
                                    if mensal["aviso_previo_insuficiente"]
                                    else None
                                ),
                            ),
                        )
                    ),
                ]
            )

        self._rodape_export(
            master,
            "encerramentos",
            colunas=tuple(c.titulo for c in colunas),
            linhas=linhas_export,
        )
