from .models import Mention, Referent, ReferenceResolution


def validar_mencoes(texto: str, mencoes: list[Mention]) -> None:
    ids = {mencao.id for mencao in mencoes}
    if len(ids) != len(mencoes):
        raise ValueError("IDs de menção duplicados.")

    por_id = {mencao.id: mencao for mencao in mencoes}
    for mencao in mencoes:
        trecho = texto[mencao.intervalo.inicio:mencao.intervalo.fim]
        if trecho != mencao.texto:
            raise ValueError(f"Intervalo incompatível com o texto da menção {mencao.id}.")
        if mencao.mencao_pai_id is None:
            continue
        if mencao.mencao_pai_id not in ids:
            raise ValueError(f"Menção pai inexistente em {mencao.id}.")
        pai = por_id[mencao.mencao_pai_id]
        if not (
            pai.intervalo.inicio <= mencao.intervalo.inicio
            and pai.intervalo.fim >= mencao.intervalo.fim
        ):
            raise ValueError(f"Menção pai não contém o intervalo de {mencao.id}.")


def validar_referencias(
    mencoes: list[Mention],
    referentes: list[Referent],
    resolucoes: list[ReferenceResolution],
) -> None:
    mencoes_por_id = {item.id: item for item in mencoes}
    referentes_por_id = {item.id: item for item in referentes}
    if len(referentes_por_id) != len(referentes):
        raise ValueError("IDs de referente duplicados.")
    if len({item.mencao_id for item in resolucoes}) != len(resolucoes):
        raise ValueError("Uma menção possui mais de uma decisão referencial.")

    participacoes: dict[str, str] = {}
    for referente in referentes:
        for mencao_id in referente.mencoes:
            if mencao_id not in mencoes_por_id:
                raise ValueError(f"Menção inexistente no referente {referente.id}.")
            if mencao_id in participacoes:
                raise ValueError(f"A menção {mencao_id} pertence a dois referentes.")
            participacoes[mencao_id] = referente.id

    for resolucao in resolucoes:
        if resolucao.mencao_id not in mencoes_por_id:
            raise ValueError("Resolução aponta para uma menção inexistente.")
        if resolucao.referente_id and resolucao.referente_id not in referentes_por_id:
            raise ValueError("Resolução aponta para um referente inexistente.")
        if resolucao.referente_id and participacoes.get(resolucao.mencao_id) != resolucao.referente_id:
            raise ValueError("Resolução e agrupamento referencial divergem.")
        for evidencia in resolucao.evidencias:
            mencao = mencoes_por_id.get(evidencia.mencao_id)
            if mencao is None or evidencia.texto != mencao.texto or evidencia.intervalo != mencao.intervalo:
                raise ValueError("Evidência referencial incompatível com a menção original.")

