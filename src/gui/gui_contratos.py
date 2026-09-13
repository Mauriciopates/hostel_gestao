"""Ecrãs de Contratos e Reservas: criação de um contrato de
arrendamento mensal (NovoContratoMensal), registo de uma reserva
Airbnb (NovaReservaAirbnb, 07/09/2026 — ver docstring da própria
classe) e listagem das ocupações já existentes, mensais e Airbnb
(ListaContratosMensais / ListaReservasAirbnb, com botão fixo "+
Novo Contrato" / "+ Nova Reserva Airbnb" e popup, ver docstring de
_ListaOcupacoesBase).

Só fala com os módulos de negócio (unidades, clientes, responsaveis,
contratos, validacoes, impressao) — nunca com repositorio
diretamente, mesma disciplina de gui/gui_unidades.py.

Mockup validado com o aluno em 06/09/2026 (capturas
screenshot_contrato_vazio.png / screenshot_contrato_preenchido.png,
fluxo completo testado com Xvfb + contratos.criar_mensal real e
dados falsos). Decisões tomadas nessa validação:

1. Todos os campos ficam sempre visíveis — não há campos que
   aparecem/desaparecem consoante o que se escreve nos outros. A
   obrigatoriedade condicional (ex.: responsável do desconto só é
   exigido quando a renda praticada é menor que a calculada) só é
   validada ao submeter.

2. Confirmação do desconto na renda: ao contrário do CLI (que
   pergunta "confirmas o desconto?" antes de pedir o responsável),
   aqui escolher o responsável no dropdown já vale como confirmação
   — não há uma pergunta extra.

3. Confirmação da caução: como este caso não tem responsável
   associado (validacoes.validar_caucao só devolve um sinal
   True/False de "exige confirmação"), usa-se uma caixa de
   confirmação ("Confirmo esta caução") que só bloqueia a criação
   quando é mesmo necessário — equivalente ao confirmar() do CLI.

4. O dropdown de lugar mostra o estado ao vivo (livre/parcial/
   ocupado, com contagem) recalculado sempre que a unidade muda.
   Não usa o estado "reservado" da Planta de Lugares — aqui só
   interessa saber se ainda cabe mais gente.

5. Fecha o ciclo com a Planta de Lugares (unidades.PlantaLugares):
   o construtor aceita 'unidade_id' e 'lugar_id' opcionais, para ser
   aberto já pré-preenchido a partir de um clique numa caixa livre/
   reservada da planta. Essa ligação (o próprio clique a abrir este
   ecrã) fica para quando os ecrãs estiverem ligados ao mesmo
   controlador/menu — não é feita aqui.

6. Erros de validação/negócio (contratos.criar_mensal a levantar
   ValueError, ou erro de formato num campo) e a confirmação de
   sucesso aparecem num popup nativo (componentes.mostrar_erro/
   mostrar_sucesso — ícone, mensagem, botão OK), não numa legenda no
   ecrã — decisão do aluno, 06/09/2026, ao testar este ecrã pela
   primeira vez. É a convenção a partir de agora para toda a
   interface gráfica, não só aqui; não há legenda nenhuma no rodapé,
   só o botão "Criar contrato".

7. Depois de criar com sucesso, o formulário limpa-se sozinho
   (_limpar_formulario) para o próximo registo — o aluno reparou
   que os campos ficavam com os valores do contrato anterior depois
   de fechar o popup. Mantém a unidade escolhida (comum criar vários
   contratos seguidos na mesma unidade); cliente, datas, valores e a
   confirmação da caução voltam ao vazio, e lugar/cliente/responsável
   são recarregados, para já refletirem o contrato acabado de criar.

8. NovaReservaAirbnb (07/09/2026): mockup (imagem, sem código real)
   validado com o aluno antes de codar, mesmo padrão de botão fixo
   + popup já fechado em "Contrato Mensal". Duas perguntas feitas ao
   aluno (AskUserQuestion) sobre pontos sem convenção prévia — ambas
   respondidas com a opção recomendada:
   - Recalcular o "Preço calculado" ao sair do campo de data
     (<FocusOut>, só quando as duas datas já estão preenchidas e
     válidas) — não há aqui um combo único (como a Unidade, no
     mensal) que dispare um evento de recálculo.
   - Combo "Cliente" já vem pré-selecionado com o primeiro da lista
     (mesmo comportamento de NovoContratoMensal), em vez de vazio.
   Ver a docstring da própria classe para as restantes decisões
   (sem "Lugar", sem "Nacionalidade"/"Data de nascimento").

9. EncerrarContratoModal (07/09/2026): mockup (imagem) validado com
   o aluno antes de codar — botão "Encerrar" no cartão de cada
   contrato mensal ativo (contorno cinzento, não vermelho: o
   vermelho fica para o botão de confirmação dentro do modal, mesma
   convenção de _AnonimizarModal em gui_clientes.py) e modal com
   Data de fim + Motivo, os mesmos campos do CLI
   (cli.py:_encerrar_contrato_mensal). Duas perguntas feitas ao
   aluno (AskUserQuestion) — ambas respondidas com a opção
   recomendada:
   - Data de fim já pré-preenchida com a data de hoje, em vez de
     vazia (o caso normal é encerrar hoje).
   - Avisos de duração abaixo do mínimo / aviso prévio insuficiente
     mostrados AO VIVO, antes de encerrar (caixa amarela que só
     aparece quando se aplicam), em vez de só depois no popup de
     sucesso como o CLI faz. Os avisos continuam a não bloquear
     nada (decisão 14: regra da casa, não imposição legal) e são
     calculados por `contratos.avisos_encerramento` — a regra fica
     no módulo de negócio, a GUI só a mostra.

10. CancelarReservaModal (07/09/2026): botão "Cancelar" no cartão de
   cada reserva Airbnb ativa (mesmo contorno cinzento do
   "Encerrar", nunca vermelho — o vermelho fica só para o botão de
   confirmação dentro do modal, mesma convenção do ponto anterior).
   Mais simples que EncerrarContratoModal porque `contratos.
   cancelar_airbnb` não pede nem altera nenhuma data (a reserva já
   tem 'data_fim' desde a criação) nem tem avisos a calcular — só
   o motivo, opcional, os mesmos campos do CLI
   (cli.py:_cancelar_reserva_airbnb). O botão que fecha o modal sem
   cancelar chama-se "Voltar", não "Cancelar" — única exceção ao
   rótulo "Cancelar" usado para fechar em todos os outros modais do
   projeto (NovoClienteModal, EditarClienteModal, _AnonimizarModal,
   EncerrarContratoModal) — para não ficar ambíguo ao lado do botão
   vermelho "Cancelar reserva", que é a ação de negócio em si.

11. REESTRUTURAÇÃO DO ECRÃ "CONTRATO MENSAL" (13/09/2026) — decisão
   do aluno, mockup HTML aprovado em duas rondas antes de codar:

   - O ecrã deixa de desenhar cartões empilhados (o que tinha desde
     07/09) e passa a ser uma TABELA igual à de Gestão de
     Propriedades (o "padrão base" do sistema). Colunas: ID,
     NOME UNIDADE, NOME DO CLIENTE, DATA, STATUS, AÇÕES — a
     mesma estrutura de `componentes.Tabela` já usada por
     Propriedades, Produtos, Movimentos, Responsáveis, Devoluções,
     Requisições e Unidades da Propriedade. Deixa de ter cartões e
     passa a ser uma linha por contrato.
   - O botão "Encerrar" que estava em cada cartão sai da linha —
     a linha passa a ter só um botão "Gerir", que abre um popup
     (`_AcoesContratoModal`, padrão do `_AcoesPropriedadeModal`).
   - O popup "Gerir contrato" tem três ações: Encerrar (só se
     ativo), Reativar (só se encerrado) e Imprimir contrato. A
     única que já não existia era Imprimir — ver ponto 12.
   - `_ListaOcupacoesBase` deixa de existir: agora que Contrato
     Mensal é tabela e Reservas Airbnb continua com cartões (o
     aluno confirmou que só o mensal muda — Pergunta 1a), a base
     comum só um dos dois usava na forma original. `ListaReservas
     Airbnb` passa a ser autónoma, com o `_desenhar_ocupacao` que
     já tinha via a base, copiado para dentro dele. Não há
     herança nem fator comum a manter entre os dois.

12. IMPRIMIR CONTRATO (13/09/2026) — nova funcionalidade, a
   pedido do aluno, baseada na minuta
   `Minuta-Contrato-de-Arrendamento-de-Quarto.pdf` que ele forneceu.
   Decisões tomadas em conversa antes de codar:

   - O PDF é gerado num módulo novo, `impressao.py` (raiz de
     `src/`, não dentro de `gui/`) — módulo puro, recebe
     dicionários e devolve o caminho do ficheiro, não fala com
     base de dados. O `gui_contratos.py` é que faz as leituras
     (`contratos.detalhes_mensal`, `clientes.procurar`,
     `unidades.procurar`, `propriedades.procurar`,
     `responsaveis.procurar`) e passa tudo ao `impressao.
     gerar_contrato_pdf`. Escolha "b" (dois módulos) em vez de
     "a" (tudo em `gui_contratos.py`) — quando o módulo de
     Relatórios chegar, vai usar o mesmo `impressao.py`, e fazia
     sentido que ele já estivesse fora da GUI.
   - O botão "Imprimir contrato" abre um popup próprio
     (`_ImprimirContratoModal`), ANTES de gerar o PDF. O popup
     pede duas coisas: o SENHORIO (dropdown de responsáveis — é
     a pessoa que assina do lado do senhorio, e que a minuta
     chama "Primeiro Contraente") e o LOCAL (caixa de texto
     livre — a cidade, porque não existe em lado nenhum do
     sistema). O "Segundo Contraente" é o cliente do contrato,
     que já lá está — não se escolhe.
   - Cliente anonimizado NÃO pode imprimir (decisão do aluno,
     confirmada). O botão "Imprimir contrato" não aparece de todo
     dentro do `_AcoesContratoModal` quando o cliente está
     anonimizado — em vez dele, uma linha de texto cinzenta a
     explicar porquê. Isto evita a situação ridícula de gerar um
     PDF com dados pessoais de um titular cujos dados foram
     apagados por RGPD.
   - O IBAN que sai na Cláusula 3ª é o da PROPRIEDADE (não do
     cliente, como tínhamos planeado antes de a conversa evoluir)
     — porque na minuta original o NIB/IBAN é para onde o
     inquilino paga a renda, e isso é do senhorio, não do
     cliente. `propriedades.criar` e `propriedades.atualizar`
     ganharam o campo `iban` (opcional) e o
     `gui_propriedades.py` ganhou o campo nos dois modais.
   - Nome do ficheiro: `CNT-003_2026-09-13_15h42.pdf` na pasta
     `contratos_gerados/` na raiz do projeto (fora do controlo
     de versões, mesma convenção dos backups — decisão 13). A
     hora no nome resolve o caso de gerar o mesmo contrato duas
     vezes no mesmo dia.
   - Texto do PDF é fiel à minuta original, com as correções das
     gralhas tipográficas óbvias aprovadas pelo aluno (documentadas
     no próprio `impressao.py`).
   - Datas com espaços à volta das barras ("13 / 09 / 2026"),
     números só com algarismos ("350,00 euros") — sem extenso.
   - Parágrafo de abertura a identificar as partes e zona de
     assinaturas no fim foram ACRESCENTADOS (não estão na minuta
     original, que começa direto na Cláusula 1ª e acaba na linha
     local/data, sem sítio para assinar). Confirmado pelo aluno
     — sem eles, o senhorio e o inquilino nunca apareceriam com
     nome no PDF.

13. PÓS-ENTREGA (13/09/2026, mesmo dia, ao testar no PC do aluno):

   a) PDF abria só com aviso "ficou guardado em...", sem abrir o
      ficheiro. Corrigido: depois de gerar, `_ImprimirContratoModal.
      _abrir_no_sistema(caminho)` chama a função nativa de cada SO
      (`os.startfile` no Windows, `open` no macOS, `xdg-open` no
      Linux). Se falhar, o PDF continua gravado e a mensagem de
      sucesso continua a mostrar o caminho — não rebenta.

   b) Popups ficavam abertos depois de gerar o PDF. Corrigido:
      o `_ImprimirContratoModal` recebe agora o popup pai (o
      `_AcoesContratoModal`) como parâmetro opcional `popup_pai`, e
      fecha-o explicitamente no fim do `_gerar_pdf` — para além de
      se fechar a si próprio. Fica a interface a voltar à tabela
      sem nada pendurado em cima.
"""

import datetime
import os
import subprocess
import sys
from decimal import Decimal, InvalidOperation

import customtkinter as ctk

import clientes
import config
import contratos
import impressao
import propriedades
import responsaveis
import unidades
import validacoes
from gui import componentes, tema


def _formatar_valor(valor):
    return f"{valor:.2f} €".replace(".", ",")


def _rotulo_lugar(lugar, ocupantes, capacidade):
    """Rótulo do dropdown de lugar: nome + estado ao vivo.

    Só distingue livre/parcial/ocupado (nunca "reservado" — decisão
    4 do módulo): aqui só interessa saber se ainda cabe mais gente.
    """
    if ocupantes == 0:
        estado = "livre"
    elif ocupantes >= capacidade:
        estado = "ocupado"
    else:
        estado = "parcial"

    return f"{lugar['nome']} · {estado} ({ocupantes}/{capacidade})"


class NovoContratoMensal(ctk.CTkFrame):
    """Formulário de criação de um contrato de arrendamento mensal."""

    def __init__(self, master, controlador, unidade_id=None, lugar_id=None):
        super().__init__(master, fg_color=tema.COR_FUNDO)
        self.controlador = controlador
        self.unidade_selecionada = None
        self.lugares_da_unidade = []
        self.lugar_id_pendente = lugar_id

        componentes.Cabecalho(self, "Novo Contrato Mensal").pack(fill="x")

        self.area = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.area.pack(fill="both", expand=True, padx=24, pady=16)

        self._montar_cartao_unidade()
        self._montar_cartao_cliente()
        self._montar_cartao_contrato()
        self._montar_rodape()

        self._recarregar_unidades(unidade_id)
        self._recarregar_clientes()
        self._recarregar_responsaveis()

    # -- montagem dos widgets ------------------------------------------

    def _criar_cartao(self, titulo):
        cartao = ctk.CTkFrame(
            self.area,
            fg_color=tema.COR_FUNDO,
            border_width=1,
            border_color=tema.COR_BORDA,
            corner_radius=tema.RAIO_CARTAO,
        )
        cartao.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(
            cartao,
            text=titulo,
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(anchor="w", padx=18, pady=(14, 6))
        corpo = ctk.CTkFrame(cartao, fg_color="transparent")
        corpo.pack(fill="x", padx=18, pady=(0, 16))
        corpo.grid_columnconfigure(0, weight=0)
        corpo.grid_columnconfigure(1, weight=1)
        return corpo

    def _linha(self, corpo, linha, rotulo):
        ctk.CTkLabel(
            corpo,
            text=rotulo,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=12),
            anchor="w",
            width=160,
        ).grid(row=linha, column=0, sticky="w", pady=6, padx=(0, 12))

    def _montar_cartao_unidade(self):
        corpo = self._criar_cartao("Unidade e lugar")

        self._linha(corpo, 0, "Unidade *")
        self.combo_unidade = ctk.CTkOptionMenu(
            corpo,
            values=["—"],
            command=self._ao_escolher_unidade,
        )
        self.combo_unidade.grid(row=0, column=1, sticky="ew", pady=6)

        self._linha(corpo, 1, "Lugar (opcional)")
        self.combo_lugar = ctk.CTkOptionMenu(corpo, values=["— Nenhum —"])
        self.combo_lugar.grid(row=1, column=1, sticky="ew", pady=6)

    def _montar_cartao_cliente(self):
        corpo = self._criar_cartao("Cliente")

        self._linha(corpo, 0, "Cliente *")
        self.combo_cliente = ctk.CTkOptionMenu(corpo, values=["—"])
        self.combo_cliente.grid(row=0, column=1, sticky="ew", pady=6)

    def _montar_cartao_contrato(self):
        corpo = self._criar_cartao("Datas e valores")

        self._linha(corpo, 0, "Data de início *")
        self.campo_data_inicio = ctk.CTkEntry(
            corpo, placeholder_text="dd/mm/aaaa"
        )
        self.campo_data_inicio.grid(row=0, column=1, sticky="ew", pady=6)

        self._linha(corpo, 1, "Dia de vencimento")
        self.campo_dia_vencimento = ctk.CTkEntry(
            corpo, placeholder_text=f"Enter para {config.DIA_VENCIMENTO}"
        )
        self.campo_dia_vencimento.grid(row=1, column=1, sticky="ew", pady=6)

        self._linha(corpo, 2, "Renda calculada")
        self.rotulo_renda_calculada = ctk.CTkLabel(
            corpo,
            text="— (escolhe a unidade)",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            anchor="w",
        )
        self.rotulo_renda_calculada.grid(row=2, column=1, sticky="ew", pady=6)

        self._linha(corpo, 3, "Renda praticada *")
        self.campo_renda_praticada = ctk.CTkEntry(
            corpo, placeholder_text="0,00"
        )
        self.campo_renda_praticada.grid(row=3, column=1, sticky="ew", pady=6)

        self._linha(corpo, 4, "Motivo da diferença")
        self.campo_motivo_renda = ctk.CTkEntry(
            corpo, placeholder_text="opcional — só se a renda for diferente"
        )
        self.campo_motivo_renda.grid(row=4, column=1, sticky="ew", pady=6)

        self._linha(corpo, 5, "Responsável do desconto")
        self.combo_responsavel = ctk.CTkOptionMenu(
            corpo, values=["— Nenhum —"]
        )
        self.combo_responsavel.grid(row=5, column=1, sticky="ew", pady=6)
        ctk.CTkLabel(
            corpo,
            text="obrigatório quando a renda praticada é inferior à "
            "calculada",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
        ).grid(row=6, column=1, sticky="w")

        self._linha(corpo, 7, "Caução *")
        self.campo_caucao = ctk.CTkEntry(corpo, placeholder_text="0,00")
        self.campo_caucao.grid(row=7, column=1, sticky="ew", pady=6)

        self.confirma_caucao = ctk.CTkCheckBox(
            corpo,
            text="Confirmo esta caução (nula ou superior à renda "
            "praticada)",
        )
        self.confirma_caucao.grid(row=8, column=1, sticky="w", pady=(0, 6))

        self._linha(corpo, 9, "Motivo da caução")
        self.campo_motivo_caucao = ctk.CTkEntry(
            corpo, placeholder_text="opcional"
        )
        self.campo_motivo_caucao.grid(row=9, column=1, sticky="ew", pady=6)

    def _montar_rodape(self):
        rodape = ctk.CTkFrame(self.area, fg_color="transparent")
        rodape.pack(fill="x", pady=(4, 0))

        ctk.CTkButton(
            rodape,
            text="Criar contrato",
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            corner_radius=tema.RAIO_BOTAO,
            command=self._criar,
        ).pack(side="right")

    # -- carregamento de dados -------------------------------------

    def _recarregar_unidades(self, unidade_id_inicial=None):
        self.unidades_mensais = unidades.listar(tipo="mensal")
        nomes = [
            f"{u['id']} · {u['nome']}" for u in self.unidades_mensais
        ] or ["— Sem unidades mensais —"]
        self.combo_unidade.configure(values=nomes)

        alvo = None
        if unidade_id_inicial:
            alvo = next(
                (
                    u
                    for u in self.unidades_mensais
                    if u["id"] == unidade_id_inicial
                ),
                None,
            )
        if alvo is None and self.unidades_mensais:
            alvo = self.unidades_mensais[0]

        if alvo is not None:
            indice = self.unidades_mensais.index(alvo)
            self.combo_unidade.set(nomes[indice])
            self._ao_escolher_unidade(nomes[indice])

    def _recarregar_clientes(self):
        self.clientes_disponiveis = clientes.listar()
        nomes = [
            f"{c['id']} · {c['nome']} (NIF {c['nif'] or '—'})"
            for c in self.clientes_disponiveis
        ] or ["— Sem clientes —"]
        self.combo_cliente.configure(values=nomes)
        if self.clientes_disponiveis:
            self.combo_cliente.set(nomes[0])

    def _recarregar_responsaveis(self):
        self.responsaveis_disponiveis = responsaveis.listar()
        nomes = ["— Nenhum —"] + [
            f"{r['id']} · {r['nome']}" for r in self.responsaveis_disponiveis
        ]
        self.combo_responsavel.configure(values=nomes)
        self.combo_responsavel.set(nomes[0])

    def _ao_escolher_unidade(self, _valor_escolhido):
        indice = self.combo_unidade.cget("values").index(
            self.combo_unidade.get()
        )
        if indice >= len(self.unidades_mensais):
            self.unidade_selecionada = None
            self.rotulo_renda_calculada.configure(text="—")
            self.combo_lugar.configure(values=["— Nenhum —"])
            self.combo_lugar.set("— Nenhum —")
            return

        self.unidade_selecionada = self.unidades_mensais[indice]
        self.rotulo_renda_calculada.configure(
            text=_formatar_valor(self.unidade_selecionada["preco_base"])
        )
        self._recarregar_lugares()

    def _recarregar_lugares(self):
        self.lugares_da_unidade = []
        opcoes = ["— Nenhum —"]

        if self.unidade_selecionada is None:
            self.combo_lugar.configure(values=opcoes)
            self.combo_lugar.set(opcoes[0])
            return

        contratos_da_unidade = contratos.listar(
            unidade_id=self.unidade_selecionada["id"], tipo="mensal"
        )

        for quarto in unidades.listar_quartos(
            unidade_id=self.unidade_selecionada["id"]
        ):
            for lugar in unidades.listar_lugares(quarto_id=quarto["id"]):
                ocupantes = sum(
                    1
                    for c in contratos_da_unidade
                    if c["lugar_id"] == lugar["id"]
                )
                self.lugares_da_unidade.append(lugar)
                opcoes.append(
                    _rotulo_lugar(lugar, ocupantes, lugar["capacidade"])
                )

        self.combo_lugar.configure(values=opcoes)
        self.combo_lugar.set(opcoes[0])

        if self.lugar_id_pendente:
            for i, lugar in enumerate(self.lugares_da_unidade):
                if lugar["id"] == self.lugar_id_pendente:
                    self.combo_lugar.set(opcoes[i + 1])
                    break
            self.lugar_id_pendente = None

    # -- submissão ----------------------------------------------------

    def _mostrar_erro(self, texto):
        componentes.mostrar_erro(texto)

    def _mostrar_sucesso(self, texto):
        componentes.mostrar_sucesso(texto)

    def _lugar_escolhido_id(self):
        indice = self.combo_lugar.cget("values").index(self.combo_lugar.get())
        if indice == 0:
            return ""
        return self.lugares_da_unidade[indice - 1]["id"]

    def _responsavel_escolhido_id(self):
        indice = self.combo_responsavel.cget("values").index(
            self.combo_responsavel.get()
        )
        if indice == 0:
            return ""
        return self.responsaveis_disponiveis[indice - 1]["id"]

    def _cliente_escolhido_id(self):
        indice = self.combo_cliente.cget("values").index(
            self.combo_cliente.get()
        )
        return self.clientes_disponiveis[indice]["id"]

    def _criar(self):
        if self.unidade_selecionada is None:
            self._mostrar_erro("Escolhe uma unidade mensal.")
            return

        try:
            data_inicio = datetime.datetime.strptime(
                self.campo_data_inicio.get().strip(), "%d/%m/%Y"
            ).date()
        except ValueError:
            self._mostrar_erro("Data de início inválida (usa dd/mm/aaaa).")
            return

        texto_dia = self.campo_dia_vencimento.get().strip()
        dia_vencimento = None
        if texto_dia:
            if not texto_dia.isdigit():
                self._mostrar_erro("O dia de vencimento tem de ser um número.")
                return
            dia_vencimento = int(texto_dia)

        try:
            renda_praticada = Decimal(
                self.campo_renda_praticada.get().strip().replace(",", ".")
            )
            caucao = Decimal(self.campo_caucao.get().strip().replace(",", "."))
        except InvalidOperation:
            self._mostrar_erro("Renda ou caução com formato inválido.")
            return

        if renda_praticada < self.unidade_selecionada["preco_base"]:
            if not self._responsavel_escolhido_id():
                self._mostrar_erro(
                    "É preciso escolher um responsável para autorizar o "
                    "desconto na renda."
                )
                return

        try:
            exige_confirmacao = validacoes.validar_caucao(
                caucao, renda_praticada, config.MULTIPLICADOR_MAXIMO_CAUCAO
            )
        except ValueError as erro:
            self._mostrar_erro(str(erro))
            return

        if exige_confirmacao and not self.confirma_caucao.get():
            self._mostrar_erro(
                "Confirma a caução (nula ou superior à renda praticada) "
                "na caixa de confirmação."
            )
            return

        try:
            ocupacao, _mensal = contratos.criar_mensal(
                self.unidade_selecionada["id"],
                self._cliente_escolhido_id(),
                data_inicio,
                renda_praticada,
                caucao,
                responsavel_desconto_renda_id=self._responsavel_escolhido_id(),
                lugar_id=self._lugar_escolhido_id(),
                dia_vencimento=dia_vencimento,
                motivo_alteracao_renda=self.campo_motivo_renda.get(),
                motivo_alteracao_caucao=self.campo_motivo_caucao.get(),
            )
        except ValueError as erro:
            self._mostrar_erro(str(erro))
            return

        aviso = (
            " (aviso: documento expira durante a estadia)"
            if (ocupacao["aviso_documento"])
            else ""
        )
        self._mostrar_sucesso(
            f"Contrato criado com sucesso: {ocupacao['id']}{aviso}"
        )
        self._limpar_formulario()

    def _limpar_formulario(self):
        """Repõe o formulário no estado inicial depois de criar um
        contrato com sucesso, para o próximo registo — sem isto, os
        campos ficavam com os valores do contrato anterior (apanhado
        pelo aluno a testar, não era intencional). Mantém a unidade
        escolhida (é comum criar vários contratos seguidos na mesma
        unidade); tudo o resto volta ao valor por omissão, e as
        listas de lugares/clientes/responsáveis são recarregadas,
        para refletirem o contrato que acabou de ser criado (ex.: o
        lugar escolhido já aparece com um ocupante a mais).
        """
        self.campo_data_inicio.delete(0, "end")
        self.campo_dia_vencimento.delete(0, "end")
        self.campo_renda_praticada.delete(0, "end")
        self.campo_motivo_renda.delete(0, "end")
        self.campo_caucao.delete(0, "end")
        self.campo_motivo_caucao.delete(0, "end")
        self.confirma_caucao.deselect()

        self._recarregar_clientes()
        self._recarregar_responsaveis()
        self._recarregar_lugares()


def _formatar_data(valor):
    """Formata uma date para dd/mm/aaaa — "em aberto" quando None
    (contrato mensal ainda ativo, sem data de fim marcada).
    """
    if valor is None:
        return "em aberto"
    return valor.strftime("%d/%m/%Y")


def _identificar_unidade(unidade, unidade_id):
    """Devolve "nome (ID)" para mostrar num cartão de ocupação, ou só
    o ID se a unidade não existir — mesma convenção de
    cli.py:_identificar_unidade.
    """
    if unidade is None:
        return unidade_id
    return f"{unidade['nome']} ({unidade['id']})"


def _identificar_cliente(cliente, cliente_id):
    """Mesma ideia de `_identificar_unidade`, para clientes."""
    if cliente is None:
        return cliente_id
    return f"{cliente['nome']} ({cliente['id']})"


def _colocar_no_topo(janela):
    """Traz um popup para a frente da janela principal — mesma
    função de gui/gui_clientes.py e gui/gui_propriedades.py, repetida
    aqui porque cada módulo da GUI já a define localmente.
    """
    janela.after(
        10, lambda: (janela.lift(), janela.focus_force(), janela.grab_set())
    )


class NovoContratoModal(ctk.CTkToplevel):
    """Popup com o formulário de Novo Contrato Mensal."""

    def __init__(self, tela_lista, unidade_id=None, lugar_id=None):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista

        self.title("Novo Contrato Mensal")
        self.geometry("640x700")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _colocar_no_topo(self)
        self.protocol("WM_DELETE_WINDOW", self._fechar)

        NovoContratoMensal(
            self,
            controlador=tela_lista.controlador,
            unidade_id=unidade_id,
            lugar_id=lugar_id,
        ).pack(fill="both", expand=True)

    def _fechar(self):
        self.tela_lista._recarregar()
        self.destroy()


class NovaReservaAirbnb(ctk.CTkFrame):
    """Formulário de registo de uma reserva Airbnb."""

    def __init__(self, master, controlador, unidade_id=None):
        super().__init__(master, fg_color=tema.COR_FUNDO)
        self.controlador = controlador
        self.unidade_selecionada = None

        componentes.Cabecalho(self, "Nova Reserva Airbnb").pack(fill="x")

        self.area = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.area.pack(fill="both", expand=True, padx=24, pady=16)

        self._montar_cartao_unidade_cliente()
        self._montar_cartao_estadia()
        self._montar_cartao_checkin_tardio()
        self._montar_rodape()

        self._recarregar_unidades(unidade_id)
        self._recarregar_clientes()
        self._recarregar_responsaveis()

    # -- montagem dos widgets ------------------------------------------

    def _criar_cartao(self, titulo):
        cartao = ctk.CTkFrame(
            self.area,
            fg_color=tema.COR_FUNDO,
            border_width=1,
            border_color=tema.COR_BORDA,
            corner_radius=tema.RAIO_CARTAO,
        )
        cartao.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(
            cartao,
            text=titulo,
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(anchor="w", padx=18, pady=(14, 6))
        corpo = ctk.CTkFrame(cartao, fg_color="transparent")
        corpo.pack(fill="x", padx=18, pady=(0, 16))
        corpo.grid_columnconfigure(0, weight=0)
        corpo.grid_columnconfigure(1, weight=1)
        return corpo

    def _linha(self, corpo, linha, rotulo):
        ctk.CTkLabel(
            corpo,
            text=rotulo,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=12),
            anchor="w",
            width=160,
        ).grid(row=linha, column=0, sticky="w", pady=6, padx=(0, 12))

    def _montar_cartao_unidade_cliente(self):
        corpo = self._criar_cartao("Unidade e cliente")

        self._linha(corpo, 0, "Unidade *")
        self.combo_unidade = ctk.CTkOptionMenu(
            corpo,
            values=["—"],
            command=self._ao_escolher_unidade,
        )
        self.combo_unidade.grid(row=0, column=1, sticky="ew", pady=6)

        self._linha(corpo, 1, "Cliente *")
        self.combo_cliente = ctk.CTkOptionMenu(corpo, values=["—"])
        self.combo_cliente.grid(row=1, column=1, sticky="ew", pady=6)

    def _montar_cartao_estadia(self):
        corpo = self._criar_cartao("Estadia e valores")

        self._linha(corpo, 0, "Data de entrada *")
        self.campo_data_inicio = ctk.CTkEntry(
            corpo, placeholder_text="dd/mm/aaaa"
        )
        self.campo_data_inicio.grid(row=0, column=1, sticky="ew", pady=6)
        self.campo_data_inicio.bind(
            "<FocusOut>", lambda _evento: self._recalcular_preco()
        )

        self._linha(corpo, 1, "Data de saída *")
        self.campo_data_fim = ctk.CTkEntry(
            corpo, placeholder_text="dd/mm/aaaa"
        )
        self.campo_data_fim.grid(row=1, column=1, sticky="ew", pady=6)
        self.campo_data_fim.bind(
            "<FocusOut>", lambda _evento: self._recalcular_preco()
        )

        self._linha(corpo, 2, "Preço calculado")
        self.rotulo_preco_calculado = ctk.CTkLabel(
            corpo,
            text="— (escolhe as datas)",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            anchor="w",
        )
        self.rotulo_preco_calculado.grid(row=2, column=1, sticky="ew", pady=6)

        self._linha(corpo, 3, "Preço praticado *")
        self.campo_preco_praticado = ctk.CTkEntry(
            corpo, placeholder_text="0,00"
        )
        self.campo_preco_praticado.grid(row=3, column=1, sticky="ew", pady=6)

        self._linha(corpo, 4, "Motivo da diferença")
        self.campo_motivo_preco = ctk.CTkEntry(
            corpo,
            placeholder_text="opcional — só se o preço for diferente",
        )
        self.campo_motivo_preco.grid(row=4, column=1, sticky="ew", pady=6)

        self._linha(corpo, 5, "Responsável do desconto")
        self.combo_responsavel_preco = ctk.CTkOptionMenu(
            corpo, values=["— Nenhum —"]
        )
        self.combo_responsavel_preco.grid(
            row=5, column=1, sticky="ew", pady=6
        )
        ctk.CTkLabel(
            corpo,
            text="obrigatório quando o preço praticado é inferior ao "
            "calculado",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
        ).grid(row=6, column=1, sticky="w")

    def _montar_cartao_checkin_tardio(self):
        corpo = self._criar_cartao("Check-in tardio")

        self.checkin_tardio = ctk.CTkCheckBox(corpo, text="Check-in tardio")
        self.checkin_tardio.grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 6)
        )

        self._linha(corpo, 1, "Hora de chegada")
        self.campo_hora_chegada = ctk.CTkEntry(
            corpo, placeholder_text="hh:mm"
        )
        self.campo_hora_chegada.grid(row=1, column=1, sticky="ew", pady=6)
        ctk.CTkLabel(
            corpo,
            text="obrigatória quando o check-in é tardio",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
        ).grid(row=2, column=1, sticky="w")

        self._linha(corpo, 3, "Multa calculada")
        self.rotulo_multa_calculada = ctk.CTkLabel(
            corpo,
            text="— (escolhe a unidade)",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            anchor="w",
        )
        self.rotulo_multa_calculada.grid(row=3, column=1, sticky="ew", pady=6)

        self._linha(corpo, 4, "Multa praticada")
        self.campo_multa_praticada = ctk.CTkEntry(
            corpo, placeholder_text="Enter para a multa calculada"
        )
        self.campo_multa_praticada.grid(row=4, column=1, sticky="ew", pady=6)

        self._linha(corpo, 5, "Responsável do desconto")
        self.combo_responsavel_multa = ctk.CTkOptionMenu(
            corpo, values=["— Nenhum —"]
        )
        self.combo_responsavel_multa.grid(
            row=5, column=1, sticky="ew", pady=6
        )
        ctk.CTkLabel(
            corpo,
            text="obrigatório quando a multa praticada é inferior à "
            "calculada",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
        ).grid(row=6, column=1, sticky="w")

    def _montar_rodape(self):
        rodape = ctk.CTkFrame(self.area, fg_color="transparent")
        rodape.pack(fill="x", pady=(4, 0))

        ctk.CTkButton(
            rodape,
            text="Registar reserva",
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            corner_radius=tema.RAIO_BOTAO,
            command=self._registar,
        ).pack(side="right")

    # -- carregamento de dados -------------------------------------

    def _recarregar_unidades(self, unidade_id_inicial=None):
        self.unidades_airbnb = unidades.listar(tipo="airbnb")
        nomes = [
            f"{u['id']} · {u['nome']}" for u in self.unidades_airbnb
        ] or ["— Sem unidades Airbnb —"]
        self.combo_unidade.configure(values=nomes)

        alvo = None
        if unidade_id_inicial:
            alvo = next(
                (
                    u
                    for u in self.unidades_airbnb
                    if u["id"] == unidade_id_inicial
                ),
                None,
            )
        if alvo is None and self.unidades_airbnb:
            alvo = self.unidades_airbnb[0]

        if alvo is not None:
            indice = self.unidades_airbnb.index(alvo)
            self.combo_unidade.set(nomes[indice])
            self._ao_escolher_unidade(nomes[indice])

    def _recarregar_clientes(self):
        self.clientes_disponiveis = clientes.listar()
        nomes = [
            f"{c['id']} · {c['nome']} (NIF {c['nif'] or '—'})"
            for c in self.clientes_disponiveis
        ] or ["— Sem clientes —"]
        self.combo_cliente.configure(values=nomes)
        if self.clientes_disponiveis:
            self.combo_cliente.set(nomes[0])

    def _recarregar_responsaveis(self):
        self.responsaveis_disponiveis = responsaveis.listar()
        nomes = ["— Nenhum —"] + [
            f"{r['id']} · {r['nome']}" for r in self.responsaveis_disponiveis
        ]
        self.combo_responsavel_preco.configure(values=nomes)
        self.combo_responsavel_preco.set(nomes[0])
        self.combo_responsavel_multa.configure(values=nomes)
        self.combo_responsavel_multa.set(nomes[0])

    def _ao_escolher_unidade(self, _valor_escolhido):
        indice = self.combo_unidade.cget("values").index(
            self.combo_unidade.get()
        )
        if indice >= len(self.unidades_airbnb):
            self.unidade_selecionada = None
        else:
            self.unidade_selecionada = self.unidades_airbnb[indice]

        self._atualizar_multa_calculada()
        self._recalcular_preco()

    # -- valores calculados ------------------------------------------

    def _ler_data(self, campo):
        texto = campo.get().strip()
        if not texto:
            return None
        try:
            return datetime.datetime.strptime(texto, "%d/%m/%Y").date()
        except ValueError:
            return None

    def _recalcular_preco(self):
        if self.unidade_selecionada is None:
            self.rotulo_preco_calculado.configure(text="—")
            return

        data_inicio = self._ler_data(self.campo_data_inicio)
        data_fim = self._ler_data(self.campo_data_fim)

        if data_inicio is None or data_fim is None or data_fim <= data_inicio:
            self.rotulo_preco_calculado.configure(
                text="— (escolhe as datas)"
            )
            return

        preco = contratos.calcular_preco_airbnb(
            self.unidade_selecionada, data_inicio, data_fim
        )
        self.rotulo_preco_calculado.configure(text=_formatar_valor(preco))

    def _atualizar_multa_calculada(self):
        if self.unidade_selecionada is None:
            self.rotulo_multa_calculada.configure(
                text="— (escolhe a unidade)"
            )
            return

        self.rotulo_multa_calculada.configure(
            text=_formatar_valor(
                self.unidade_selecionada["multa_check_in_tardio"]
            )
        )

    # -- submissão ----------------------------------------------------

    def _mostrar_erro(self, texto):
        componentes.mostrar_erro(texto)

    def _mostrar_sucesso(self, texto):
        componentes.mostrar_sucesso(texto)

    def _cliente_escolhido_id(self):
        indice = self.combo_cliente.cget("values").index(
            self.combo_cliente.get()
        )
        return self.clientes_disponiveis[indice]["id"]

    def _id_responsavel(self, combo):
        indice = combo.cget("values").index(combo.get())
        if indice == 0:
            return ""
        return self.responsaveis_disponiveis[indice - 1]["id"]

    def _registar(self):
        if self.unidade_selecionada is None:
            self._mostrar_erro("Escolhe uma unidade Airbnb.")
            return

        data_inicio = self._ler_data(self.campo_data_inicio)
        if data_inicio is None:
            self._mostrar_erro("Data de entrada inválida (usa dd/mm/aaaa).")
            return

        data_fim = self._ler_data(self.campo_data_fim)
        if data_fim is None:
            self._mostrar_erro("Data de saída inválida (usa dd/mm/aaaa).")
            return

        try:
            preco_praticado = Decimal(
                self.campo_preco_praticado.get().strip().replace(",", ".")
            )
        except InvalidOperation:
            self._mostrar_erro("Preço praticado com formato inválido.")
            return

        check_in_tardio = bool(self.checkin_tardio.get())
        hora_chegada = self.campo_hora_chegada.get().strip()

        texto_multa = self.campo_multa_praticada.get().strip()
        multa_praticada = None
        if texto_multa:
            try:
                multa_praticada = Decimal(texto_multa.replace(",", "."))
            except InvalidOperation:
                self._mostrar_erro("Multa praticada com formato inválido.")
                return

        try:
            ocupacao, _airbnb = contratos.registar_airbnb(
                self.unidade_selecionada["id"],
                self._cliente_escolhido_id(),
                data_inicio,
                data_fim,
                preco_praticado,
                responsavel_desconto_preco_id=self._id_responsavel(
                    self.combo_responsavel_preco
                ),
                check_in_tardio=check_in_tardio,
                hora_chegada=hora_chegada,
                multa_praticada=multa_praticada,
                responsavel_desconto_multa_id=self._id_responsavel(
                    self.combo_responsavel_multa
                ),
            )
        except ValueError as erro:
            self._mostrar_erro(str(erro))
            return

        aviso = (
            " (aviso: documento expira durante a estadia)"
            if (ocupacao["aviso_documento"])
            else ""
        )
        self._mostrar_sucesso(
            f"Reserva registada com sucesso: {ocupacao['id']}{aviso}"
        )
        self._limpar_formulario()

    def _limpar_formulario(self):
        """Mesma ideia de NovoContratoMensal._limpar_formulario."""
        self.campo_data_inicio.delete(0, "end")
        self.campo_data_fim.delete(0, "end")
        self.campo_preco_praticado.delete(0, "end")
        self.campo_motivo_preco.delete(0, "end")
        self.checkin_tardio.deselect()
        self.campo_hora_chegada.delete(0, "end")
        self.campo_multa_praticada.delete(0, "end")

        self._recarregar_clientes()
        self._recarregar_responsaveis()
        self._recalcular_preco()


class NovaReservaAirbnbModal(ctk.CTkToplevel):
    """Popup com o formulário de Nova Reserva Airbnb."""

    def __init__(self, tela_lista):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista

        self.title("Nova Reserva Airbnb")
        self.geometry("640x700")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _colocar_no_topo(self)
        self.protocol("WM_DELETE_WINDOW", self._fechar)

        NovaReservaAirbnb(
            self, controlador=tela_lista.controlador
        ).pack(fill="both", expand=True)

    def _fechar(self):
        self.tela_lista._recarregar()
        self.destroy()


class EncerrarContratoModal(ctk.CTkToplevel):
    """Popup de encerramento de um contrato mensal."""

    def __init__(self, tela_lista, ocupacao):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.ocupacao = ocupacao

        self.title("Encerrar contrato mensal")
        self.geometry("420x400")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _colocar_no_topo(self)

        unidade = unidades.procurar(ocupacao["unidade_id"])
        cliente = clientes.procurar(ocupacao["cliente_id"])
        nome_unidade = _identificar_unidade(unidade, ocupacao["unidade_id"])
        nome_cliente = _identificar_cliente(cliente, ocupacao["cliente_id"])

        mensagem = (
            f"Encerrar o contrato {ocupacao['id']}?\n"
            f"{nome_cliente} · unidade {nome_unidade}\n"
            f"Início: {_formatar_data(ocupacao['data_inicio'])}"
        )
        ctk.CTkLabel(
            self,
            text=mensagem,
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=13),
            wraplength=370,
            justify="left",
        ).pack(padx=20, pady=(24, 14), fill="x")

        ctk.CTkLabel(
            self,
            text="Data de fim *",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20)

        self.campo_data_fim = ctk.CTkEntry(
            self,
            placeholder_text="dd/mm/aaaa",
            corner_radius=tema.RAIO_CAMPO,
        )
        self.campo_data_fim.insert(
            0, datetime.date.today().strftime("%d/%m/%Y")
        )
        self.campo_data_fim.pack(fill="x", padx=20, pady=(2, 10))
        self.campo_data_fim.bind(
            "<FocusOut>", lambda _evento: self._atualizar_avisos()
        )
        self.campo_data_fim.bind(
            "<Return>", lambda _evento: self._atualizar_avisos()
        )

        self.caixa_avisos = ctk.CTkLabel(
            self,
            text="",
            text_color=tema.TEXTO_AVISO,
            fg_color=tema.AMARELO_AVISO,
            corner_radius=8,
            font=ctk.CTkFont(size=11),
            justify="left",
            anchor="w",
            wraplength=350,
        )

        self.rotulo_motivo = ctk.CTkLabel(
            self,
            text="Motivo do encerramento (opcional)",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        )
        self.rotulo_motivo.pack(anchor="w", padx=20)

        self.campo_motivo = ctk.CTkEntry(
            self,
            placeholder_text="ex.: saída antecipada do inquilino",
            corner_radius=tema.RAIO_CAMPO,
        )
        self.campo_motivo.pack(fill="x", padx=20, pady=(2, 10))

        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=20, pady=20, side="bottom")
        ctk.CTkButton(
            rodape,
            text="Cancelar",
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(side="left")
        ctk.CTkButton(
            rodape,
            text="Encerrar contrato",
            fg_color=tema.TEXTO_ERRO,
            hover_color=tema.VERMELHO_ERRO,
            command=self._encerrar,
        ).pack(side="right")

        self._atualizar_avisos()

    # -- avisos ao vivo ------------------------------------------------

    def _ler_data_fim(self):
        """Devolve a data escrita, ou None se estiver vazia ou com
        formato inválido.
        """
        texto = self.campo_data_fim.get().strip()

        if not texto:
            return None

        try:
            return datetime.datetime.strptime(texto, "%d/%m/%Y").date()
        except ValueError:
            return None

    def _atualizar_avisos(self):
        data_fim = self._ler_data_fim()

        if data_fim is None:
            self.caixa_avisos.pack_forget()
            return

        avisos = contratos.avisos_encerramento(self.ocupacao, data_fim)
        linhas = []

        if avisos["duracao_abaixo_minima"]:
            linhas.append(
                f"⚠  Duração abaixo do mínimo "
                f"({config.DURACAO_MINIMA_MESES} meses)"
            )

        if avisos["aviso_previo_insuficiente"]:
            linhas.append(
                f"⚠  Aviso prévio insuficiente "
                f"({config.AVISO_PREVIO_DIAS} dias)"
            )

        if not linhas:
            self.caixa_avisos.pack_forget()
            return

        self.caixa_avisos.configure(text="\n".join(linhas))
        self.caixa_avisos.pack(
            fill="x",
            padx=20,
            pady=(0, 10),
            ipady=8,
            before=self.rotulo_motivo,
        )

    # -- ação ------------------------------------------------------------

    def _encerrar(self):
        texto = self.campo_data_fim.get().strip()

        try:
            data_fim = datetime.datetime.strptime(texto, "%d/%m/%Y").date()
        except ValueError:
            componentes.mostrar_erro(
                "Data de fim inválida (usa dd/mm/aaaa)."
            )
            return

        try:
            ocupacao, mensal = contratos.encerrar_mensal(
                self.ocupacao["id"],
                data_fim,
                motivo=self.campo_motivo.get().strip(),
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        avisos = []
        if mensal["duracao_abaixo_minima"]:
            avisos.append("duração abaixo do mínimo")
        if mensal["aviso_previo_insuficiente"]:
            avisos.append("aviso prévio insuficiente")

        texto_avisos = f" [{', '.join(avisos)}]" if avisos else ""

        componentes.mostrar_sucesso(
            f"Contrato {ocupacao['id']} encerrado em "
            f"{_formatar_data(data_fim)}{texto_avisos}."
        )
        self.destroy()
        self.tela_lista._recarregar()


class CancelarReservaModal(ctk.CTkToplevel):
    """Popup de cancelamento de uma reserva Airbnb."""

    def __init__(self, tela_lista, ocupacao):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.ocupacao = ocupacao

        self.title("Cancelar reserva Airbnb")
        self.geometry("420x300")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _colocar_no_topo(self)

        unidade = unidades.procurar(ocupacao["unidade_id"])
        cliente = clientes.procurar(ocupacao["cliente_id"])
        nome_unidade = _identificar_unidade(unidade, ocupacao["unidade_id"])
        nome_cliente = _identificar_cliente(cliente, ocupacao["cliente_id"])
        periodo = (
            f"{_formatar_data(ocupacao['data_inicio'])} → "
            f"{_formatar_data(ocupacao['data_fim'])}"
        )

        mensagem = (
            f"Cancelar a reserva {ocupacao['id']}?\n"
            f"{nome_cliente} · unidade {nome_unidade}\n"
            f"Estadia: {periodo}"
        )
        ctk.CTkLabel(
            self,
            text=mensagem,
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=13),
            wraplength=370,
            justify="left",
        ).pack(padx=20, pady=(24, 14), fill="x")

        ctk.CTkLabel(
            self,
            text="Motivo do cancelamento (opcional)",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20)

        self.campo_motivo = ctk.CTkEntry(
            self,
            placeholder_text="ex.: hóspede desistiu",
            corner_radius=tema.RAIO_CAMPO,
        )
        self.campo_motivo.pack(fill="x", padx=20, pady=(2, 10))

        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=20, pady=20, side="bottom")
        ctk.CTkButton(
            rodape,
            text="Voltar",
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(side="left")
        ctk.CTkButton(
            rodape,
            text="Cancelar reserva",
            fg_color=tema.TEXTO_ERRO,
            hover_color=tema.VERMELHO_ERRO,
            command=self._cancelar,
        ).pack(side="right")

    def _cancelar(self):
        try:
            ocupacao, airbnb = contratos.cancelar_airbnb(
                self.ocupacao["id"],
                motivo=self.campo_motivo.get().strip(),
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Reserva {ocupacao['id']} cancelada."
        )
        self.destroy()
        self.tela_lista._recarregar()


class ListaContratosMensais(ctk.CTkFrame):
    """Lista dos contratos mensais — ecrã "Contrato Mensal" da barra
    lateral.

    Reestruturado em 13/09/2026 (ver ponto 11 do docstring do
    módulo): deixou de desenhar cartões empilhados e passa a ser uma
    TABELA igual à de Gestão de Propriedades (o "padrão base" do
    sistema). Colunas: ID, NOME UNIDADE, NOME DO CLIENTE, DATA,
    STATUS, AÇÕES.

    Cada linha tem um único botão "Gerir" (mesmo padrão do
    `_AcoesPropriedadeModal`), que abre `_AcoesContratoModal` — o
    popup com Encerrar / Reativar / Imprimir contrato.

    A lista já não partilha base com `ListaReservasAirbnb`: o aluno
    confirmou que só o Contrato Mensal passa a tabela, e o Airbnb
    mantém os cartões (Pergunta 1a da conversa de 13/09/2026).
    """

    def __init__(self, master, controlador):
        super().__init__(master, fg_color=tema.COR_FUNDO)
        self.controlador = controlador

        componentes.Cabecalho(self, titulo="Contrato Mensal").pack(fill="x")

        # Botão de criação numa barra própria, logo abaixo do
        # cabeçalho e a verde — mesmo padrão de Contratos e Reservas.
        barra_criar = ctk.CTkFrame(self, fg_color="transparent")
        barra_criar.pack(fill="x", padx=20, pady=(4, 8))
        ctk.CTkButton(
            barra_criar,
            text="+ Novo Contrato",
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.VERDE,
            hover_color=tema.VERDE,
            command=lambda: NovoContratoModal(self),
        ).pack(side="left")

        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.pack(fill="x", padx=20, pady=(0, 4))

        self.combo_aviso = ctk.CTkOptionMenu(
            barra,
            values=["Todos", "Com aviso", "Sem aviso"],
            command=lambda _valor: self._recarregar(),
            width=130,
        )
        self.combo_aviso.set("Todos")
        self.combo_aviso.pack(side="right")

        self.mostrar_inativas = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            barra,
            text="Mostrar inativas/encerradas",
            variable=self.mostrar_inativas,
            command=self._recarregar,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(side="right", padx=(12, 0))

        self.tabela = componentes.Tabela(
            self,
            colunas=(
                componentes.Coluna("ID", minimo=110, espaco=8),
                componentes.Coluna(
                    "NOME UNIDADE", peso=3, minimo=180
                ),
                componentes.Coluna(
                    "NOME DO CLIENTE", peso=3, minimo=180
                ),
                componentes.Coluna(
                    "DATA", peso=2, minimo=180, alinhamento="w"
                ),
                componentes.Coluna(
                    "STATUS",
                    peso=1,
                    minimo=110,
                    alinhamento="centro",
                ),
                componentes.Coluna(
                    "AÇÕES", minimo=90, alinhamento="centro"
                ),
            ),
            altura_linha=52,
            mensagem_vazia="Nenhum contrato mensal encontrado.",
            tom_alternado=True,
        )
        self.tabela.pack(fill="both", expand=True, padx=20, pady=(4, 12))

        self._recarregar()

    # -- carregamento / atualização ----------------------------------

    def _aviso_selecionado(self):
        return {"Todos": None, "Com aviso": True, "Sem aviso": False}[
            self.combo_aviso.get()
        ]

    def _recarregar(self):
        """Limpa e volta a desenhar a tabela — chamada na abertura
        do ecrã, ao mexer nos filtros, e depois de qualquer criação/
        encerramento/reativação de contrato.
        """
        self.tabela.limpar()

        lista = contratos.listar(
            incluir_inativas=self.mostrar_inativas.get(),
            tipo="mensal",
            aviso_documento=self._aviso_selecionado(),
        )

        if not lista:
            self.tabela.mostrar_vazio()
            return

        for ocupacao in lista:
            self._desenhar_ocupacao(ocupacao)

    # -- desenho -------------------------------------------------------

    def _desenhar_ocupacao(self, ocupacao):
        """Desenha uma linha da tabela para um contrato mensal.

        Cada célula é um widget criado com a linha como master e
        colocado com `self.tabela.colocar`, que trata do grid, do
        alinhamento e das folgas. A altura, as divisórias e o tom
        das linhas são da tabela.
        """
        inativa = not ocupacao["ativo"]

        unidade = unidades.procurar(ocupacao["unidade_id"])
        cliente = clientes.procurar(ocupacao["cliente_id"])

        nome_unidade = unidade["nome"] if unidade else ocupacao["unidade_id"]
        id_unidade = ocupacao["unidade_id"]

        nome_cliente = (
            cliente["nome"] if cliente else ocupacao["cliente_id"]
        )
        id_cliente = ocupacao["cliente_id"]

        linha = self.tabela.nova_linha()

        # Coluna ID — chip, como nas outras tabelas do sistema.
        self.tabela.colocar(
            linha,
            0,
            ctk.CTkLabel(
                linha,
                text=ocupacao["id"],
                text_color=tema.AZUL_PRINCIPAL,
                fg_color=tema.ID_CHIP_FUNDO,
                corner_radius=6,
                font=ctk.CTkFont(size=11, weight="bold"),
                width=110,
                anchor="w",
            ),
            esticar="w",
        )

        # Coluna NOME UNIDADE — nome grande, ID pequeno por baixo.
        bloco_unidade = ctk.CTkFrame(linha, fg_color="transparent")
        ctk.CTkLabel(
            bloco_unidade,
            text=nome_unidade,
            text_color=(
                tema.TEXTO_INDISPONIVEL if inativa else tema.COR_TEXTO
            ),
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            bloco_unidade,
            text=id_unidade,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
            anchor="w",
        ).pack(fill="x")
        self.tabela.colocar(linha, 1, bloco_unidade)

        # Coluna NOME DO CLIENTE — mesma estrutura (nome + ID).
        bloco_cliente = ctk.CTkFrame(linha, fg_color="transparent")
        ctk.CTkLabel(
            bloco_cliente,
            text=nome_cliente,
            text_color=(
                tema.TEXTO_INDISPONIVEL if inativa else tema.COR_TEXTO
            ),
            font=ctk.CTkFont(size=13),
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            bloco_cliente,
            text=id_cliente,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
            anchor="w",
        ).pack(fill="x")
        self.tabela.colocar(linha, 2, bloco_cliente)

        # Coluna DATA — início → fim, ou "em aberto" se ainda não
        # encerrou. Fonte secundária (é metadado, não identidade).
        data_inicio = _formatar_data(ocupacao["data_inicio"])
        data_fim = _formatar_data(ocupacao["data_fim"])
        self.tabela.colocar(
            linha,
            3,
            ctk.CTkLabel(
                linha,
                text=f"{data_inicio} → {data_fim}",
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=11),
                anchor="w",
            ),
        )

        # Coluna STATUS — chip "Ativa" ou "Encerrado", e o chip de
        # aviso de documento a acompanhar quando aplicável.
        bloco_status = ctk.CTkFrame(linha, fg_color="transparent")

        if inativa:
            ctk.CTkLabel(
                bloco_status,
                text="Encerrado",
                text_color=tema.TEXTO_INDISPONIVEL,
                fg_color=tema.CINZA_INDISPONIVEL,
                corner_radius=8,
                font=ctk.CTkFont(size=10, weight="bold"),
                width=90,
                height=22,
            ).pack(side="left")

            if ocupacao["aviso_documento"]:
                ctk.CTkLabel(
                    bloco_status,
                    text="Doc. a expirar",
                    text_color=tema.TEXTO_AVISO,
                    fg_color=tema.AMARELO_AVISO,
                    corner_radius=8,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    width=100,
                    height=22,
                ).pack(side="left", padx=(6, 0))
        else:
            ctk.CTkLabel(
                bloco_status,
                text="Ativa",
                text_color=tema.TEXTO_LIVRE,
                fg_color=tema.VERDE_LIVRE,
                corner_radius=8,
                font=ctk.CTkFont(size=10, weight="bold"),
                width=70,
                height=22,
            ).pack(side="left")

            if ocupacao["aviso_documento"]:
                ctk.CTkLabel(
                    bloco_status,
                    text="Doc. a expirar",
                    text_color=tema.TEXTO_AVISO,
                    fg_color=tema.AMARELO_AVISO,
                    corner_radius=8,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    width=100,
                    height=22,
                ).pack(side="left", padx=(6, 0))

        self.tabela.colocar(linha, 4, bloco_status)

        # Coluna AÇÕES — um único botão "Gerir", que abre o popup
        # com todas as ações (Encerrar / Reativar / Imprimir).
        acoes = self.tabela.celula_acoes(linha, 5)
        acoes.adicionar(
            ctk.CTkButton(
                acoes,
                text="Gerir",
                width=76,
                height=26,
                corner_radius=tema.RAIO_BOTAO,
                fg_color="transparent",
                border_width=1,
                border_color=tema.COR_BORDA,
                text_color=tema.COR_TEXTO,
                hover_color=tema.COR_BORDA,
                command=lambda: _AcoesContratoModal(self, ocupacao),
            )
        )

    # -- ações -------------------------------------------------------

    def _reativar(self, ocupacao):
        pergunta = f"Reativar o contrato {ocupacao['id']}?"
        if not componentes.confirmar(pergunta):
            return

        try:
            contratos.reativar(ocupacao["id"])
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Contrato {ocupacao['id']} reativado."
        )
        self._recarregar()


class _AcoesContratoModal(ctk.CTkToplevel):
    """Popup pequeno com as ações de um contrato mensal — aberto
    pelo botão "Gerir" de cada linha em `ListaContratosMensais`
    (13/09/2026, ver ponto 11 do docstring do módulo).

    Mesmo padrão dos popups de propriedade, unidade e produto:
    título com nome da unidade, subtítulo com o ID do contrato e o
    cliente, botões com a mesma forma, separador antes da ação
    destrutiva.

    Três ações:
    - Encerrar contrato (só se ativo) — abre EncerrarContratoModal.
    - Reativar contrato (só se encerrado) — direto, sem modal.
    - Imprimir contrato — abre `_ImprimirContratoModal`. Se o
      cliente estiver anonimizado, o botão NÃO aparece; em vez
      dele, uma linha cinzenta a explicar porquê (decisão do
      aluno, ponto 12 do docstring do módulo).
    """

    def __init__(self, tela_lista, ocupacao):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.ocupacao = ocupacao

        unidade = unidades.procurar(ocupacao["unidade_id"])
        cliente = clientes.procurar(ocupacao["cliente_id"])
        nome_unidade = unidade["nome"] if unidade else ocupacao["unidade_id"]
        nome_cliente = (
            cliente["nome"] if cliente else ocupacao["cliente_id"]
        )

        self.title(f"Ações — {ocupacao['id']}")
        self.geometry("340x300")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text=nome_unidade,
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=14, weight="bold"),
            wraplength=280,
        ).pack(padx=20, pady=(20, 2))

        ctk.CTkLabel(
            self,
            text=f"{ocupacao['id']} · {nome_cliente}",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            wraplength=280,
        ).pack(pady=(0, 14))

        # As ações variam com o estado do contrato.
        if ocupacao["ativo"]:
            self._botao(
                "Encerrar contrato",
                text_color=tema.COR_TEXTO,
                hover_color=tema.COR_BORDA,
                acao=lambda: EncerrarContratoModal(
                    self.tela_lista, ocupacao
                ),
            )
        else:
            self._botao(
                "Reativar contrato",
                text_color=tema.TEXTO_LIVRE,
                hover_color=tema.VERDE_LIVRE,
                acao=lambda: self.tela_lista._reativar(ocupacao),
            )

        # Imprimir contrato — bloqueado se cliente anonimizado.
        # Quando bloqueado, em vez de um botão que não fazia nada,
        # fica uma linha cinzenta a explicar porquê (decisão do
        # aluno, ponto 12 do docstring do módulo).
        cliente_anonimizado = bool(
            cliente and cliente["anonimizado"]
        )

        if cliente_anonimizado:
            ctk.CTkLabel(
                self,
                text=(
                    "Impressão indisponível — o cliente deste "
                    "contrato foi anonimizado (RGPD), e os dados "
                    "pessoais foram apagados."
                ),
                text_color=tema.TEXTO_INDISPONIVEL,
                font=ctk.CTkFont(size=10),
                wraplength=280,
                justify="left",
                anchor="w",
            ).pack(fill="x", padx=20, pady=(10, 6))
        else:
            ctk.CTkFrame(
                self, height=1, fg_color=tema.COR_BORDA
            ).pack(fill="x", padx=20, pady=(8, 5))

            self._botao(
                "Imprimir contrato",
                text_color=tema.AZUL_PRINCIPAL,
                hover_color=tema.ID_CHIP_FUNDO,
                # Passa-se `self` como terceiro argumento — o
                # `_ImprimirContratoModal` guarda-o em `popup_pai`
                # e fecha-o no fim do `_gerar_pdf`, para não ficar
                # pendurado em cima da tabela depois de gerar.
                acao=lambda: _ImprimirContratoModal(
                    self.tela_lista, ocupacao, self
                ),
            )

        ctk.CTkButton(
            self,
            text="Fechar",
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(side="bottom", fill="x", padx=20, pady=(10, 16))

    def _botao(self, texto, text_color, hover_color, acao):
        """Botão de ação: fecha este popup antes de agir.

        A ordem importa — as ações abrem outro popup ou fazem
        `_recarregar` na tabela por trás; deixar este aberto por
        cima deixava-o pendurado sobre coisas que entretanto
        mudaram.
        """

        def executar():
            self.destroy()
            acao()

        ctk.CTkButton(
            self,
            text=texto,
            height=34,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            hover_color=hover_color,
            text_color=text_color,
            border_width=1,
            border_color=tema.COR_BORDA,
            command=executar,
        ).pack(fill="x", padx=20, pady=3)


class _ImprimirContratoModal(ctk.CTkToplevel):
    """Popup intermédio do "Imprimir contrato" — pede o senhorio e o
    local, antes de gerar o PDF (13/09/2026, ver ponto 12 do
    docstring do módulo).

    Só dois campos:

    - **Senhorio / Primeiro Contraente** (dropdown de responsáveis)
      — é a pessoa que assina do lado do senhorio, e a que a
      minuta chama "Primeiro Contraente". O aluno confirmou que
      Senhorio e Primeiro Contraente são a mesma pessoa, por isso
      há um só dropdown — não dois.
    - **Local** (caixa de texto) — a cidade onde o contrato é
      assinado. Vai para a linha final, onde a minuta tem
      "... (local), ... / ... / ...". Não existe em lado nenhum
      do sistema, por isso é escrito à mão a cada impressão.

    O Segundo Contraente é o cliente do contrato — já está lá,
    não se escolhe. Este popup não pergunta nada sobre ele.

    Recebe opcionalmente `popup_pai` — o `_AcoesContratoModal` que
    o abriu. Ao gerar o PDF, fecha esse popup pai a seguir a fechar
    a si mesmo, para a interface voltar à tabela sem nada pendurado
    em cima (decisão do aluno, 13/09/2026, ponto 13b do docstring
    do módulo).
    """

    def __init__(self, tela_lista, ocupacao, popup_pai=None):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.ocupacao = ocupacao
        self.popup_pai = popup_pai

        unidade = unidades.procurar(ocupacao["unidade_id"])
        cliente = clientes.procurar(ocupacao["cliente_id"])
        nome_unidade = unidade["nome"] if unidade else ocupacao["unidade_id"]
        nome_cliente = (
            cliente["nome"] if cliente else ocupacao["cliente_id"]
        )

        self.title(f"Imprimir contrato — {ocupacao['id']}")
        self.geometry("460x400")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text="Identificar as partes do contrato",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(22, 2))

        ctk.CTkLabel(
            self,
            text=f"{ocupacao['id']} · {nome_unidade} · {nome_cliente}",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            wraplength=410,
            justify="left",
        ).pack(anchor="w", padx=24, pady=(0, 18))

        # ---- Senhorio ------------------------------------------------
        ctk.CTkLabel(
            self,
            text="Senhorio / Primeiro Contraente",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=24)

        self.responsaveis_disponiveis = responsaveis.listar()
        nomes = ["— Escolher responsável —"] + [
            f"{r['id']} · {r['nome']}"
            for r in self.responsaveis_disponiveis
        ]
        self.combo_senhorio = ctk.CTkOptionMenu(
            self, values=nomes, corner_radius=tema.RAIO_CAMPO
        )
        self.combo_senhorio.set(nomes[0])
        self.combo_senhorio.pack(fill="x", padx=24, pady=(2, 2))

        ctk.CTkLabel(
            self,
            text=(
                "Assina do lado do senhorio. Aparece no PDF como "
                "\"Primeiro Contraente\"."
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
            wraplength=410,
            justify="left",
        ).pack(anchor="w", padx=24, pady=(0, 12))

        # ---- Local ---------------------------------------------------
        ctk.CTkLabel(
            self,
            text="Local",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=24)

        self.campo_local = ctk.CTkEntry(
            self,
            corner_radius=tema.RAIO_CAMPO,
            placeholder_text="ex.: Porto",
        )
        self.campo_local.pack(fill="x", padx=24, pady=(2, 2))

        ctk.CTkLabel(
            self,
            text=(
                "Cidade onde o contrato é assinado. Aparece na "
                "linha final do PDF."
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
            wraplength=410,
            justify="left",
        ).pack(anchor="w", padx=24, pady=(0, 12))

        # ---- rodapé --------------------------------------------------
        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=24, pady=(16, 20), side="bottom")

        ctk.CTkButton(
            rodape,
            text="Cancelar",
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(side="left")

        ctk.CTkButton(
            rodape,
            text="Gerar PDF",
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._gerar_pdf,
        ).pack(side="right")

    # -- ação --------------------------------------------------------

    def _responsavel_escolhido_id(self):
        indice = self.combo_senhorio.cget("values").index(
            self.combo_senhorio.get()
        )
        if indice == 0:
            return ""
        return self.responsaveis_disponiveis[indice - 1]["id"]

    def _gerar_pdf(self):
        """Valida os dois campos, vai buscar todos os dados do
        contrato e chama `impressao.gerar_contrato_pdf`. O
        `impressao.py` é que desenha o PDF — este método só faz as
        leituras e trata do resultado.

        Depois de gerar com sucesso, abre o PDF no visualizador
        predefinido do sistema, e fecha este popup mais o popup
        "Gerir contrato" que o abriu — para a interface voltar à
        tabela, sem ficar nada pendurado em cima (ponto 13 do
        docstring do módulo).
        """
        senhorio_id = self._responsavel_escolhido_id()

        if not senhorio_id:
            componentes.mostrar_erro(
                "Escolhe o senhorio que assina pelo lado do Primeiro "
                "Contraente."
            )
            return

        local = self.campo_local.get().strip()

        if not local:
            componentes.mostrar_erro(
                "Escreve o local (cidade) onde o contrato é assinado."
            )
            return

        # Leituras que o impressao.py não faz — é este ecrã que
        # vai buscar os dados todos, e passa-os prontos (o
        # impressao.py é módulo puro, ver docstring dele).
        senhorio = responsaveis.procurar(senhorio_id)

        if senhorio is None:
            componentes.mostrar_erro(
                f"O responsável {senhorio_id} já não existe."
            )
            return

        mensal = contratos.detalhes_mensal(self.ocupacao["id"])

        if mensal is None:
            componentes.mostrar_erro(
                "Faltam os dados mensais deste contrato (inconsistência "
                "nos dados)."
            )
            return

        unidade = unidades.procurar(self.ocupacao["unidade_id"])

        if unidade is None:
            componentes.mostrar_erro(
                "A unidade deste contrato já não existe."
            )
            return

        propriedade = propriedades.procurar(unidade["propriedade_id"])

        if propriedade is None:
            componentes.mostrar_erro(
                "A propriedade desta unidade já não existe."
            )
            return

        cliente = clientes.procurar(self.ocupacao["cliente_id"])

        if cliente is None:
            componentes.mostrar_erro(
                "O cliente deste contrato já não existe."
            )
            return

        # Se o cliente for anonimizado, o botão nem chegou a
        # aparecer no popup anterior (`_AcoesContratoModal`). Esta
        # verificação é uma segunda linha de defesa, caso alguém
        # chegue aqui por outro caminho no futuro.
        if cliente["anonimizado"]:
            componentes.mostrar_erro(
                "Não é possível imprimir um contrato cujo cliente "
                "foi anonimizado (RGPD)."
            )
            return

        try:
            caminho = impressao.gerar_contrato_pdf(
                ocupacao=self.ocupacao,
                mensal=mensal,
                cliente=cliente,
                unidade=unidade,
                propriedade=propriedade,
                senhorio=senhorio,
                local=local,
            )
        except Exception as erro:
            # O gerador é um módulo puro e não devia rebentar, mas
            # se o fpdf2 se queixar de algo, mostramos a mensagem
            # em vez de deixar a exceção subir e derrubar a GUI.
            componentes.mostrar_erro(
                f"Erro ao gerar o PDF: {erro}"
            )
            return

        # ---- fechar os popups antes de abrir o PDF ------------------
        # Fecha este popup (o "Imprimir contrato") e, se houver,
        # o que o abriu (o "Gerir contrato"). A ordem importa: as
        # destruições correm antes de abrir o PDF, para o
        # utilizador voltar à tabela antes de o visualizador tomar
        # o foco.
        popup_pai = self.popup_pai
        self.destroy()

        if popup_pai is not None:
            try:
                if popup_pai.winfo_exists():
                    popup_pai.destroy()
            except Exception:
                # Se o popup pai já foi destruído entretanto (por
                # exemplo, o `_botao` do `_AcoesContratoModal` já
                # fez `self.destroy()` antes de chamar esta ação),
                # não há nada a fazer.
                pass

        # ---- abrir o PDF no visualizador do sistema -----------------
        self._abrir_no_sistema(caminho)

        # ---- mostrar confirmação ------------------------------------
        # Só DEPOIS de abrir o PDF é que aparece o popup de
        # sucesso — assim o utilizador vê primeiro o contrato e
        # depois o "ficou guardado em..." (o pedido era "abrir já
        # o PDF, não só avisar onde ficou").
        componentes.mostrar_sucesso(
            f"Contrato gerado e aberto:\n{caminho}"
        )

    @staticmethod
    def _abrir_no_sistema(caminho):
        """Abre um ficheiro no programa predefinido do sistema
        operativo (no caso do PDF, o leitor de PDF).

        Usa a função nativa de cada SO: `os.startfile` no Windows,
        `open` no macOS, `xdg-open` no Linux. Se falhar — por
        exemplo, uma máquina sem leitor de PDF associado, ou sem
        `xdg-open` instalado — não deixa a exceção subir; o
        utilizador continua a ver o caminho na mensagem de
        sucesso, e abre-o à mão.

        Não usa `subprocess.run(check=True)`: se o comando não
        existir, o `FileNotFoundError` é tratado; se existir mas o
        SO não tiver nenhuma app associada, o erro fica do lado do
        SO e não do programa — o utilizador continua a poder abrir
        o PDF à mão.
        """
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(caminho))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(caminho)])
            else:
                subprocess.Popen(["xdg-open", str(caminho)])
        except (FileNotFoundError, OSError):
            # Não há nada a fazer — o ficheiro está gravado, o
            # utilizador tem o caminho na mensagem de sucesso.
            pass


class ListaReservasAirbnb(ctk.CTkFrame):
    """Lista das reservas Airbnb — ecrã "Reservas Airbnb" da barra
    lateral.

    Ao contrário de `ListaContratosMensais`, este ecrã mantém os
    cartões empilhados que já tinha antes (decisão do aluno,
    13/09/2026, Pergunta 1a da conversa: só o Contrato Mensal passa
    a tabela; o Airbnb fica com o formato original).

    Antes, os dois ecrãs partilhavam a base `_ListaOcupacoesBase`
    (que tinha filtros comuns e um `_desenhar_ocupacao` genérico).
    Ao separar, esta classe passa a ser autónoma — tem o seu próprio
    `__init__`, os seus próprios filtros, e o seu próprio
    `_desenhar_ocupacao` (o mesmo de antes, sem alterações).

    Botões do cartão ativo: "Cancelar" (abre CancelarReservaModal).
    O ecrã não tem "Imprimir" — a impressão é só do contrato mensal
    (decisão do aluno, 13/09/2026).
    """

    def __init__(self, master, controlador):
        super().__init__(master, fg_color=tema.COR_FUNDO)
        self.controlador = controlador

        componentes.Cabecalho(self, titulo="Reservas Airbnb").pack(fill="x")

        barra_criar = ctk.CTkFrame(self, fg_color="transparent")
        barra_criar.pack(fill="x", padx=20, pady=(4, 8))
        ctk.CTkButton(
            barra_criar,
            text="+ Nova Reserva Airbnb",
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.VERDE,
            hover_color=tema.VERDE,
            command=lambda: NovaReservaAirbnbModal(self),
        ).pack(side="left")

        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.pack(fill="x", padx=20, pady=(0, 4))

        self.combo_aviso = ctk.CTkOptionMenu(
            barra,
            values=["Todos", "Com aviso", "Sem aviso"],
            command=lambda _valor: self._recarregar(),
            width=130,
        )
        self.combo_aviso.set("Todos")
        self.combo_aviso.pack(side="right")

        self.mostrar_inativas = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            barra,
            text="Mostrar inativas/encerradas",
            variable=self.mostrar_inativas,
            command=self._recarregar,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(side="right", padx=(12, 0))

        self.area_lista = ctk.CTkScrollableFrame(
            self, fg_color="transparent"
        )
        self.area_lista.pack(fill="both", expand=True, padx=16, pady=(8, 16))

        self._recarregar()

    # -- carregamento / atualização ----------------------------------

    def _aviso_selecionado(self):
        return {"Todos": None, "Com aviso": True, "Sem aviso": False}[
            self.combo_aviso.get()
        ]

    def _recarregar(self):
        """Limpa e volta a desenhar a lista inteira — chamada na
        abertura do ecrã, ao mexer nos filtros, depois de cancelar
        uma reserva, e ao fechar o popup de Nova Reserva.
        """
        for widget in self.area_lista.winfo_children():
            widget.destroy()

        lista = contratos.listar(
            incluir_inativas=self.mostrar_inativas.get(),
            tipo="airbnb",
            aviso_documento=self._aviso_selecionado(),
        )

        if not lista:
            ctk.CTkLabel(
                self.area_lista,
                text="Nenhuma reserva Airbnb encontrada.",
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=13),
            ).pack(pady=40)
            return

        for ocupacao in lista:
            self._desenhar_ocupacao(ocupacao)

    # -- desenho -------------------------------------------------------

    def _desenhar_ocupacao(self, ocupacao):
        """Desenha o cartão de uma reserva Airbnb. Mesmo formato que
        o ecrã tinha antes da reestruturação de 13/09/2026 — copiado
        da antiga `_ListaOcupacoesBase._desenhar_ocupacao`, sem
        alterações.
        """
        inativa = not ocupacao["ativo"]

        unidade = unidades.procurar(ocupacao["unidade_id"])
        cliente = clientes.procurar(ocupacao["cliente_id"])
        nome_unidade = _identificar_unidade(unidade, ocupacao["unidade_id"])
        nome_cliente = _identificar_cliente(cliente, ocupacao["cliente_id"])

        cartao = ctk.CTkFrame(
            self.area_lista,
            corner_radius=tema.RAIO_CARTAO,
            fg_color=tema.COR_FUNDO,
            border_width=1,
            border_color=tema.COR_BORDA,
        )
        cartao.pack(fill="x", pady=6)

        linha = ctk.CTkFrame(cartao, fg_color="transparent")
        linha.pack(fill="x", padx=16, pady=12)

        bloco_texto = ctk.CTkFrame(linha, fg_color="transparent")
        bloco_texto.pack(side="left", anchor="w")

        cor_titulo = tema.COR_TEXTO_SECUNDARIO if inativa else tema.COR_TEXTO
        ctk.CTkLabel(
            bloco_texto,
            text=f"{ocupacao['id']} · {nome_unidade}",
            text_color=cor_titulo,
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        ).pack(anchor="w")

        periodo = (
            f"{_formatar_data(ocupacao['data_inicio'])} → "
            f"{_formatar_data(ocupacao['data_fim'])}"
        )
        ctk.CTkLabel(
            bloco_texto,
            text=f"{nome_cliente} · {periodo}",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(anchor="w")

        bloco_direita = ctk.CTkFrame(linha, fg_color="transparent")
        bloco_direita.pack(side="right")

        if inativa:
            self._etiqueta(
                bloco_direita,
                "Cancelada",
                tema.CINZA_INDISPONIVEL,
                tema.TEXTO_INDISPONIVEL,
            )
        else:
            self._etiqueta(
                bloco_direita, "Ativa", tema.VERDE_LIVRE, tema.TEXTO_LIVRE
            )

        if ocupacao["aviso_documento"]:
            self._etiqueta(
                bloco_direita,
                "Doc. a expirar",
                tema.AMARELO_AVISO,
                tema.TEXTO_AVISO,
            )

        if inativa:
            ctk.CTkButton(
                bloco_direita,
                text="Reativar",
                width=80,
                height=26,
                corner_radius=tema.RAIO_BOTAO,
                fg_color=tema.VERDE,
                hover_color=tema.VERDE,
                command=lambda: self._reativar(ocupacao),
            ).pack(side="left", padx=(10, 0))
        else:
            ctk.CTkButton(
                bloco_direita,
                text="Cancelar",
                width=80,
                height=26,
                corner_radius=tema.RAIO_BOTAO,
                fg_color="transparent",
                border_width=1,
                border_color=tema.COR_BORDA,
                text_color=tema.COR_TEXTO,
                hover_color=tema.COR_BORDA,
                command=lambda: CancelarReservaModal(self, ocupacao),
            ).pack(side="left", padx=(10, 0))

    def _etiqueta(self, master, texto, fundo, cor_texto):
        ctk.CTkLabel(
            master,
            text=texto,
            text_color=cor_texto,
            fg_color=fundo,
            corner_radius=8,
            font=ctk.CTkFont(size=11, weight="bold"),
            width=110,
            height=22,
        ).pack(side="left", padx=(6, 0))

    # -- ações -------------------------------------------------------

    def _reativar(self, ocupacao):
        pergunta = f"Reativar a reserva {ocupacao['id']}?"
        if not componentes.confirmar(pergunta):
            return

        try:
            contratos.reativar(ocupacao["id"])
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(f"Reserva {ocupacao['id']} reativada.")
        self._recarregar()