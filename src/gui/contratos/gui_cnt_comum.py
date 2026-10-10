"""Helpers partilhados pelos ecrãs de Contratos (mensal) e Reservas
(Airbnb).

Mesmo papel do `gui_est_comum.py` / `gui_desp_comum.py`: nomes
públicos aqui; cada `gui_cnt_*` cria o alias privado no topo."""


_TIPOS_CAMA = {
    "solteiro": "Solteiro",
    "casal": "Casal",
    "beliche": "Beliche",
}


def rotulo_tipo_cama(lugar):
    """"Solteiro", "Casal" ou "Beliche" (com a posição, se houver:
    "Beliche superior"). Vazio se o lugar não tiver tipo."""
    tipo = _TIPOS_CAMA.get(lugar.get("tipo_cama") or "", "")
    posicao = lugar.get("posicao_beliche")
    if tipo == "Beliche" and posicao:
        return f"{tipo} {posicao}"
    return tipo


def rotulo_lugar(lugar, ocupantes, capacidade, nome_quarto=None):
    """Rótulo do dropdown de lugar: quarto · cama · tipo · estado.

    10/10/2026 (pedido do aluno): passou a levar o quarto e o tipo
    de cama — duas "Cama 1" de quartos diferentes apareciam iguais,
    e não se via se era solteiro, casal ou beliche.
    Ex.: "Quarto 2 · Cama 1 · Solteiro · livre (0/1)".

    Só distingue livre/parcial/ocupado (nunca "reservado" — decisão
    4 do módulo): aqui só interessa saber se ainda cabe mais gente.
    """
    if ocupantes == 0:
        estado = "livre"
    elif ocupantes >= capacidade:
        estado = "ocupado"
    else:
        estado = "parcial"

    partes = [nome_quarto, lugar["nome"], rotulo_tipo_cama(lugar)]
    inicio = " · ".join(p for p in partes if p)
    return f"{inicio} · {estado} ({ocupantes}/{capacidade})"


# =====================================================================
# Botão "+ Novo cliente" — partilhado entre os dois formulários
# =====================================================================


def abrir_novo_cliente(formulario, regime):
    """Abre o modal de novo cliente certo de `gui_clientes.py` a
    partir de um formulário (reserva Airbnb ou contrato mensal). O
    import é local, dentro da função, para evitar import circular
    entre `gui_contratos` e `gui_clientes`.

    ATUALIZADO 16/09/2026: `gui_clientes.NovoClienteModal` (um único
    formulário com seletor de Regime) foi substituído por dois
    modais dedicados — `NovoClienteMensalModal`/
    `NovoClienteAirbnbModal` — escolhidos normalmente por um popup
    prévio (`_SeletorRegimeClienteModal`). Aqui o regime já é
    conhecido pelo próprio formulário que chama (`NovoContratoMensal`
    passa "mensal", `NovaReservaAirbnb` passa "airbnb"), por isso
    abre-se logo o modal certo, sem passar pelo popup de escolha.

    Ao fechar o modal, recarrega a lista de clientes do formulário e
    pré-seleciona o cliente novo — se ele foi mesmo criado. O modal
    não devolve o cliente criado (chama `tela_lista._recarregar()`
    ou `_recarregar_clientes()` e fecha-se, ver
    `gui_clientes._recarregar_tela_lista`); para o pré-selecionar
    aqui, comparamos a lista antes e depois.
    """
    from gui.gui_clientes import (
        NovoClienteAirbnbModal,
        NovoClienteMensalModal,
    )

    classe_modal = (
        NovoClienteMensalModal
        if regime == "mensal"
        else NovoClienteAirbnbModal
    )

    ids_antes = {c["id"] for c in formulario.clientes_disponiveis}

    modal = classe_modal(formulario)
    formulario.wait_window(modal)

    formulario._recarregar_clientes()

    ids_agora = {c["id"] for c in formulario.clientes_disponiveis}
    novos = ids_agora - ids_antes

    if novos:
        # Só interessa o primeiro — o modal cria um cliente de cada
        # vez, nunca dois.
        cliente_novo_id = next(iter(novos))
        formulario._selecionar_cliente_por_id(cliente_novo_id)


def formatar_data(valor):
    """Formata uma date para dd/mm/aaaa — "em aberto" quando None
    (contrato mensal ainda ativo, sem data de fim marcada).
    """
    if valor is None:
        return "em aberto"
    return valor.strftime("%d/%m/%Y")


def identificar_unidade(unidade, unidade_id):
    """Devolve "nome (ID)" para mostrar num cartão de ocupação, ou só
    o ID se a unidade não existir.
    """
    if unidade is None:
        return unidade_id
    return f"{unidade['nome']} ({unidade['id']})"


def identificar_cliente(cliente, cliente_id):
    """Mesma ideia de `identificar_unidade`, para clientes."""
    if cliente is None:
        return cliente_id
    return f"{cliente['nome']} ({cliente['id']})"
