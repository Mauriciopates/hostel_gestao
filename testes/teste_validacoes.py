"""Testes das validações de dados de entrada.

Ao contrário dos testes da persistência, não é precisa preparação: as
funções não tocam em ficheiros nem guardam estado. Recebem valores e
devolvem resultado ou lançam erro.
"""

import sys
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import validacoes


class TesteNIF(unittest.TestCase):
    """Validação do NIF português pelo dígito de controlo."""

    def teste_nif_valido(self):
        """Um NIF com dígito de controlo correto é aceite."""
        self.assertTrue(validacoes.nif_valido("501442600"))

    def teste_nif_com_digito_de_controlo_errado(self):
        """Alterar o último dígito invalida o NIF."""
        self.assertFalse(validacoes.nif_valido("501442601"))

    def teste_nif_com_letras_e_recusado(self):
        """Um valor com caracteres não numéricos é recusado."""
        self.assertFalse(validacoes.nif_valido("50144260A"))

    def teste_nif_com_comprimento_errado_e_recusado(self):
        """Um NIF com menos ou mais de nove dígitos é recusado."""
        self.assertFalse(validacoes.nif_valido("50144260"))
        self.assertFalse(validacoes.nif_valido("5014426000"))

    def teste_nif_vazio_ou_nulo_e_recusado(self):
        """Ausência de valor é recusada sem produzir erro."""
        self.assertFalse(validacoes.nif_valido(""))
        self.assertFalse(validacoes.nif_valido(None))


class TesteValidarCliente(unittest.TestCase):
    """Campos obrigatórios e campos que apenas marcam incompleto."""

    def cliente_valido(self):
        """Devolve um cliente com todos os campos preenchidos."""
        return {
            "nome": "Ana Silva",
            "tipo_documento": "Cartão de Cidadão",
            "numero_documento": "12345678",
            "nif": "501442600",
            "email": "ana@exemplo.pt",
            "telefone": "912345678",
            "morada": "Rua do Porto, 12",
            "nacionalidade": "Portuguesa",
        }

    def teste_cliente_completo_nao_tem_campos_em_falta(self):
        """Com tudo preenchido, a lista devolvida é vazia."""
        em_falta = validacoes.validar_cliente(self.cliente_valido(), "mensal")
        self.assertEqual([], em_falta)

    def teste_nome_em_falta_bloqueia(self):
        """Sem nome, a gravação é recusada nos dois regimes."""
        dados = self.cliente_valido()
        dados["nome"] = ""

        with self.assertRaises(ValueError):
            validacoes.validar_cliente(dados, "mensal")

        with self.assertRaises(ValueError):
            validacoes.validar_cliente(dados, "airbnb")

    def teste_documento_em_falta_bloqueia(self):
        """O tipo e o número do documento bloqueiam nos dois regimes.

        A opção de check-in sem documento prevista na especificação foi
        eliminada: a identificação de hóspedes é obrigação legal e não
        conveniência do sistema.
        """
        for campo in ("tipo_documento", "numero_documento"):
            for regime in ("mensal", "airbnb"):
                dados = self.cliente_valido()
                dados[campo] = ""

                with self.assertRaises(ValueError):
                    validacoes.validar_cliente(dados, regime)

    def teste_tipo_de_documento_fora_da_lista_bloqueia(self):
        """Só são aceites os quatro tipos de documento previstos."""
        dados = self.cliente_valido()
        dados["tipo_documento"] = "Carta de Condução"

        with self.assertRaises(ValueError):
            validacoes.validar_cliente(dados, "mensal")

    def teste_nif_obrigatorio_apenas_no_regime_mensal(self):
        """O NIF bloqueia no mensal e é dispensável no Airbnb.

        O contrato de arrendamento gera obrigação fiscal; uma estadia de
        três noites não. Exigir NIF a um hóspede estrangeiro recusaria
        registos legítimos.
        """
        dados = self.cliente_valido()
        dados["nif"] = ""

        with self.assertRaises(ValueError):
            validacoes.validar_cliente(dados, "mensal")

        em_falta = validacoes.validar_cliente(dados, "airbnb")
        self.assertEqual([], em_falta)

    def teste_nif_invalido_bloqueia_no_regime_mensal(self):
        """Um NIF preenchido mas com dígito de controlo errado é recusado."""
        dados = self.cliente_valido()
        dados["nif"] = "501442601"

        with self.assertRaises(ValueError):
            validacoes.validar_cliente(dados, "mensal")

    def teste_campos_opcionais_marcam_incompleto(self):
        """Campos não essenciais não bloqueiam: são devolvidos na lista.

        É a decisão 11: bloqueia o essencial, avisa no resto. O aviso só
        produz efeito porque existe a listagem de registos incompletos.
        """
        dados = self.cliente_valido()
        dados["email"] = ""
        dados["telefone"] = ""

        em_falta = validacoes.validar_cliente(dados, "mensal")

        self.assertEqual(["email", "telefone"], em_falta)


class TesteValidadeDocumento(unittest.TestCase):
    """Aviso quando o documento caduca durante a permanência."""

    def teste_documento_valido_durante_toda_a_estadia(self):
        """Um documento que caduca depois da saída não é assinalado."""
        self.assertFalse(
            validacoes.documento_expira_durante_estadia(
                date(2027, 1, 1), date(2026, 3, 10), date(2026, 3, 15)
            )
        )

    def teste_documento_caduca_a_meio_da_estadia(self):
        """Um documento que expira entre a entrada e a saída é assinalado."""
        self.assertTrue(
            validacoes.documento_expira_durante_estadia(
                date(2026, 3, 12), date(2026, 3, 10), date(2026, 3, 15)
            )
        )

    def teste_documento_caduca_no_dia_da_saida(self):
        """A validade no dia da saída não é assinalada.

        A unidade de contagem é a noite: o hóspede já não dorme lá nessa
        noite, e o documento foi válido em todas as que passou.
        """
        self.assertFalse(
            validacoes.documento_expira_durante_estadia(
                date(2026, 3, 15), date(2026, 3, 10), date(2026, 3, 15)
            )
        )

    def teste_documento_caduca_no_dia_da_entrada(self):
        """A validade no dia da entrada é assinalada.

        O documento é apresentado e conferido nesse dia, mas caduca antes
        da primeira noite: as restantes noites são passadas com documento
        caducado.
        """
        self.assertTrue(
            validacoes.documento_expira_durante_estadia(
                date(2026, 3, 10), date(2026, 3, 10), date(2026, 3, 15)
            )
        )

    def teste_validade_nula_nao_e_assinalada(self):
        """Sem validade registada não há nada a avaliar.

        Ausência de informação não é problema detetado. Se a validade for
        essencial e não estiver preenchida, é a validação do cliente que
        a apanha como campo em falta.
        """
        self.assertFalse(
            validacoes.documento_expira_durante_estadia(
                None, date(2026, 3, 10), date(2026, 3, 15)
            )
        )

    def teste_contrato_sem_termo_compara_apenas_com_o_inicio(self):
        """Num contrato mensal em vigor não há fim para delimitar.

        A data de fim fica nula enquanto o contrato vigora. O que se pode
        verificar é se o documento já estava caducado à entrada, situação
        mais grave do que expirar a meio de uma estadia curta.
        """
        self.assertTrue(
            validacoes.documento_expira_durante_estadia(
                date(2026, 2, 1), date(2026, 3, 10), None
            )
        )

        self.assertFalse(
            validacoes.documento_expira_durante_estadia(
                date(2027, 1, 1), date(2026, 3, 10), None
            )
        )


class TesteCaucao(unittest.TestCase):
    """Caução calculada a partir da renda praticada (decisão 14)."""

    def teste_caucao_de_uma_renda_nao_exige_confirmacao(self):
        """O valor sugerido é aceite sem sinalização."""
        exige_confirmacao = validacoes.validar_caucao(
            Decimal("250.00"), Decimal("250.00"), Decimal("2")
        )
        self.assertFalse(exige_confirmacao)

    def teste_caucao_acima_do_sugerido_exige_confirmacao(self):
        """Entre uma e duas rendas é aceite, mas sinalizado."""
        exige_confirmacao = validacoes.validar_caucao(
            Decimal("400.00"), Decimal("250.00"), Decimal("2")
        )
        self.assertTrue(exige_confirmacao)

    def teste_caucao_acima_do_teto_e_recusada(self):
        """Acima de duas rendas a gravação é recusada.

        O teto é regra da casa e não imposição legal, mas não tem
        confirmação que o contorne: o limite existe para ser limite.
        """
        with self.assertRaises(ValueError):
            validacoes.validar_caucao(
                Decimal("600.00"), Decimal("250.00"), Decimal("2")
            )

    def teste_caucao_exatamente_no_teto_e_aceite(self):
        """O teto está incluído: duas rendas exatas passam."""
        exige_confirmacao = validacoes.validar_caucao(
            Decimal("500.00"), Decimal("250.00"), Decimal("2")
        )
        self.assertTrue(exige_confirmacao)

    def teste_caucao_nula_exige_confirmacao(self):
        """Uma caução de zero é legítima mas excecional."""
        exige_confirmacao = validacoes.validar_caucao(
            Decimal("0.00"), Decimal("250.00"), Decimal("2")
        )
        self.assertTrue(exige_confirmacao)

    def teste_caucao_omitida_e_recusada(self):
        """Um valor nulo não é o mesmo que caução de zero.

        Zero significa caução dispensada por decisão; nulo significa que
        ninguém preencheu o campo. Tratá-los igual faria um esquecimento
        parecer uma decisão.
        """
        with self.assertRaises(ValueError):
            validacoes.validar_caucao(None, Decimal("250.00"), Decimal("2"))


class TesteIntervalo(unittest.TestCase):
    """Coerência de datas e limites de duração da estadia."""

    def teste_intervalo_valido_nao_produz_erro(self):
        """Um intervalo coerente dentro dos limites passa em silêncio."""
        validacoes.validar_intervalo(
            date(2026, 3, 10), date(2026, 3, 15), minimo=2, maximo=28
        )

    def teste_fim_igual_ao_inicio_e_recusado(self):
        """Entrada e saída no mesmo dia não contém nenhuma noite."""
        with self.assertRaises(ValueError):
            validacoes.validar_intervalo(date(2026, 3, 10), date(2026, 3, 10))

    def teste_fim_anterior_ao_inicio_e_recusado(self):
        """Uma saída antes da entrada é impossível."""
        with self.assertRaises(ValueError):
            validacoes.validar_intervalo(date(2026, 3, 15), date(2026, 3, 10))

    def teste_estadia_abaixo_do_minimo_e_recusada(self):
        """Uma noite é inferior ao mínimo de duas do regime Airbnb."""
        with self.assertRaises(ValueError):
            validacoes.validar_intervalo(date(2026, 3, 10),
            date(2026, 3, 11), minimo=2)

    def teste_estadia_acima_do_maximo_e_recusada(self):
        """Trinta noites excedem o máximo de vinte e oito."""
        with self.assertRaises(ValueError):
            validacoes.validar_intervalo(date(2026, 3, 1),
            date(2026, 3, 31), maximo=28)

    def teste_contrato_sem_termo_e_aceite(self):
        """Um contrato mensal em vigor não tem fim para validar.

        A data de fim fica nula enquanto o contrato vigora: preenchê-la
        com a data da próxima renovação criaria a ficção de que o
        contrato acaba nesse dia.
        """
        validacoes.validar_intervalo(date(2026, 3, 10), None)


class TesteCapacidadeLugar(unittest.TestCase):
    """Capacidade declarada no lugar, não derivada do tipo de cama."""

    def teste_capacidade_de_um_e_dois_sao_aceites(self):
        """Solteiro e casal passam sem sinalização."""
        self.assertFalse(validacoes.validar_capacidade_lugar(1))
        self.assertFalse(validacoes.validar_capacidade_lugar(2))

    def teste_capacidade_acima_de_dois_exige_confirmacao(self):
        """Três ou mais é possível mas invulgar: apanha erros de digitação."""
        self.assertTrue(validacoes.validar_capacidade_lugar(3))

    def teste_capacidade_invalida_e_recusada(self):
        """Zero, negativos, nulo e valores não inteiros são recusados."""
        for valor in (0, -1, None, "2", 1.5, True):
            with self.assertRaises(ValueError):
                validacoes.validar_capacidade_lugar(valor)


class TesteTipoUnidade(unittest.TestCase):
    """Restrição rígida entre o tipo da unidade e o da ocupação."""

    def teste_tipos_coincidentes_sao_aceites(self):
        """Mensal com mensal e Airbnb com Airbnb passam."""
        validacoes.validar_tipo_unidade("mensal", "mensal")
        validacoes.validar_tipo_unidade("airbnb", "airbnb")

    def teste_tipos_diferentes_sao_recusados(self):
        """Uma unidade mensal não aceita reserva Airbnb, nem o inverso."""
        with self.assertRaises(ValueError):
            validacoes.validar_tipo_unidade("mensal", "airbnb")

        with self.assertRaises(ValueError):
            validacoes.validar_tipo_unidade("airbnb", "mensal")

    def teste_tipo_desconhecido_e_recusado(self):
        """Um valor fora dos dois tipos previstos é recusado.

        A mensagem distingue tipo desconhecido de tipos incompatíveis:
        "Mensal" com maiúscula falharia a comparação e daria a mensagem
        errada sem esta verificação.
        """
        with self.assertRaises(ValueError):
            validacoes.validar_tipo_unidade("Mensal", "mensal")

        with self.assertRaises(ValueError):
            validacoes.validar_tipo_unidade("mensal", "hotel")


class TesteEpocaAlta(unittest.TestCase):
    """Época alta exige indicador manual E data no 

    período(nunca automática).
    
    """

    def teste_data_no_periodo_com_indicador_ativo(self):
        """As duas condições reunidas dão época alta."""
        self.assertTrue(
            validacoes.em_epoca_alta(
                date(2026, 8, 15), True, (7, 1), (9, 30)
            )
        )

    def teste_data_no_periodo_sem_indicador(self):
        """Sem o indicador manual não há época alta, mesmo em agosto.

        A época alta nunca é automática: uma unidade pode estar em pleno
        verão com preço base se o proprietário não a ativou.
        """
        self.assertFalse(
            validacoes.em_epoca_alta(
                date(2026, 8, 15), False, (7, 1), (9, 30)
            )
        )

    def teste_data_fora_do_periodo_com_indicador_ativo(self):
        """Com o indicador ligado mas fora do período, é preço base."""
        self.assertFalse(
            validacoes.em_epoca_alta(
                date(2026, 3, 15), True, (7, 1), (9, 30)
            )
        )

    def teste_limites_do_periodo_estao_incluidos(self):
        """O primeiro e o último dia do período contam como época alta."""
        self.assertTrue(
            validacoes.em_epoca_alta(
                date(2026, 7, 1), True, (7, 1), (9, 30)
            )
        )
        self.assertTrue(
            validacoes.em_epoca_alta(
                date(2026, 9, 30), True, (7, 1), (9, 30)
            )
        )

if __name__ == "__main__":
    unittest.main()
