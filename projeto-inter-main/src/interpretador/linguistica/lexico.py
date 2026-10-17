"""Léxico explícito: formas desconhecidas não recebem um infinitivo inventado.

As famílias abaixo são fechadas. As terminações só se aplicam aos infinitivos
registrados, nunca a todas as palavras com a mesma sequência de letras.
"""

VERBOS = {
    "abandonou": "abandonar", "acredita": "acreditar", "assinasse": "assinar",
    "assinado": "assinar", "assinou": "assinar", "bombardeou": "bombardear",
    "construiu": "construir", "desistiu": "desistir", "encontrada": "encontrar",
    "encontrado": "encontrar", "enviou": "enviar", "enviado": "enviar",
    "esgotando": "esgotar", "frear": "frear", "havia": "haver", "morreu": "morrer",
    "morria": "morrer", "murmurou": "murmurar", "percebeu": "perceber",
    "perder": "perder", "revisando": "revisar", "sentou": "sentar", "seria": "ser",
    "tivesse": "ter", "transformando": "transformar", "foi": "ser", "era": "ser",
    "sido": "ser", "é": "ser", "são": "ser", "está": "estar", "estava": "estar",
    "pode": "poder", "poderia": "poder", "deve": "dever", "deveria": "dever",
    "quer": "querer", "queria": "querer", "disse": "dizer", "afirmou": "afirmar",
    "contou": "contar", "pensou": "pensar", "imaginou": "imaginar", "viu": "ver",
    "ouviu": "ouvir", "chegou": "chegar", "fez": "fazer", "tinha": "ter",
    "tem": "ter", "terá": "ter", "sofreu": "sofrer", "reagiu": "reagir",
    "respondeu": "responder", "criticou": "criticar", "insistiu": "insistir",
    "acabava": "acabar", "acabou": "acabar", "leu": "ler", "viaja": "viajar",
    "viaje": "viajar", "trabalha": "trabalhar", "escreveu": "escrever",
    "saiu": "sair", "correu": "correr", "choveu": "chover", "fracassou": "fracassar",
    "permaneceu": "permanecer", "falou": "falar", "perguntou": "perguntar",
    "chegaria": "chegar", "frearia": "frear", "abandonar": "abandonar",
    "assinar": "assinar", "enviar": "enviar", "desistir": "desistir",
    "viajar": "viajar", "trabalhar": "trabalhar",
}

# Tempos menos ambíguos das famílias registradas. Evita regras irrestritas como
# converter "classe", "passe" ou "comando" em predicados por sua terminação.
_FAMILIAS_AR = {
    "abandonar", "acenar", "achar", "acreditar", "afirmar", "apontar", "arrumar",
    "assinar", "atrasar", "atualizar", "bombardear", "brincar", "buscar", "cantar",
    "chamar", "chegar", "contar", "criticar", "dançar", "deixar", "demonstrar",
    "detestar", "engrenar", "encontrar", "enviar", "enxugar", "esgotar", "esperar",
    "estudar", "falar", "ficar", "frear", "gostar", "imaginar", "inspecionar",
    "mudar", "murmurar", "observar", "olhar", "passar", "pegar", "pensar",
    "perguntar", "retornar", "revisar", "secar", "segurar", "sentar", "tentar",
    "terminar", "testar", "tomar", "trabalhar", "transformar", "viajar", "voltar",
}
_FAMILIAS_ER = {"beber", "correr", "escrever", "perceber", "perder", "responder"}
_FAMILIAS_IR = {"decidir", "desistir", "exigir", "imprimir", "partir"}
for _infinitivo in _FAMILIAS_AR | _FAMILIAS_ER | _FAMILIAS_IR:
    _radical, _classe = _infinitivo[:-2], _infinitivo[-2:]
    VERBOS[_infinitivo] = _infinitivo
    _terminacoes = {
        "ar": ("ava", "avam", "ávamos", "aram", "ara", "asse", "assem", "ássemos", "ando"),
        "er": ("ia", "iam", "íamos", "eram", "era", "esse", "essem", "êssemos", "endo"),
        "ir": ("ia", "iam", "íamos", "iram", "ira", "isse", "issem", "íssemos", "indo"),
    }[_classe]
    for _terminacao in _terminacoes:
        VERBOS[_radical + _terminacao] = _infinitivo

# Formas verificadas, incluindo alternâncias de grafia e formas irregulares.
VERBOS.update({
    "decidi": "decidir", "achei": "achar", "iria": "ir", "diminuir": "diminuir",
    "exigia": "exigir", "passou": "passar", "olhou": "olhar", "enxugado": "enxugar",
    "respondi": "responder", "peguei": "pegar", "pegou": "pegar", "sentindo": "sentir",
    "sentia": "sentir", "subindo": "subir", "estar": "estar", "fazer": "fazer",
    "saí": "sair", "saíram": "sair", "saísse": "sair", "sair": "sair", "será": "ser",
    "atrasei": "atrasar", "terminei": "terminar", "enviei": "enviar", "fiquei": "ficar",
    "chamou": "chamar", "apontou": "apontar", "deixei": "deixar", "corri": "correr",
    "arrumei": "arrumar", "imprimi": "imprimir", "voltei": "voltar", "deu": "dar",
    "retornei": "retornar", "parece": "parecer", "consegue": "conseguir",
    "acenou": "acenar", "enxuguei": "enxugar",
    "cantou": "cantar", "cantaram": "cantar", "estudei": "estudar", "bebeu": "beber",
    "partiu": "partir", "escrevi": "escrever", "exigiu": "exigir",
})

AUXILIARES_LEXICAIS = {
    "havia", "tivesse", "foi", "era", "seria", "estava", "está", "tinha", "terá",
    "sido", "iria", "pode", "poderia", "deve", "deveria", "quer", "queria",
}
_CLASSES_FUNCIONAIS = {
    "ADV": {"ainda", "não", "nunca", "sempre", "já", "só", "ali", "aqui", "finalmente", "hoje", "talvez", "mesmo", "exatamente"},
    "SCONJ": {"quando", "enquanto", "embora", "porque", "que", "se", "como"},
    "CCONJ": {"e", "nem", "mas", "porém", "ou", "pois"},
    "ADP": {"a", "ao", "aos", "à", "às", "ante", "antes", "após", "até", "com", "contra", "de", "do", "da", "dos", "das", "durante", "em", "no", "na", "nos", "nas", "para", "pelo", "pela", "pelos", "pelas", "por", "sem", "sob", "sobre", "através", "apesar"},
    "PRON": {"eu", "tu", "você", "vocês", "nós", "ele", "ela", "eles", "elas", "me", "mim", "si", "isso", "alguém", "nada", "dela", "dele", "delas", "deles"},
    "DET": {"o", "os", "as", "um", "uma", "uns", "umas", "meu", "minha", "meus", "minhas", "seu", "sua", "seus", "suas", "esse", "essa", "nesse", "nessa", "aquele", "aquela", "nenhum", "nenhuma", "outra", "outro"},
}


def lematizar_palavra(palavra: str) -> str | None:
    """Retorna somente lemas verbais sustentados pelo léxico fechado."""
    return VERBOS.get(palavra.casefold())


def pos_local(palavra: str) -> str | None:
    normalizada = palavra.casefold()
    if normalizada in VERBOS:
        return "AUX" if normalizada in AUXILIARES_LEXICAIS else "VERB"
    for classe, palavras in _CLASSES_FUNCIONAIS.items():
        if normalizada in palavras:
            return classe
    if palavra and not any(letra.isalnum() for letra in palavra):
        return "PUNCT"
    return None
