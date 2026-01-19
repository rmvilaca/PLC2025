import re
from dataclasses import dataclass
from typing import Iterator, Optional

# -----------------------------
# Token definition
# -----------------------------
@dataclass
class Token:
    type: str
    value: str
    line: int
    col: int

class LexError(Exception):
    pass


# -----------------------------
# Lexer
# -----------------------------
KEYWORDS = {
    "select": "SELECT",
    "where": "WHERE",
    "limit": "LIMIT",
}

# Em SPARQL, "a" é um atalho para rdf:type.
SPECIAL = {
    "a": "A",
}

TOKEN_SPECS = [
    # ordem importa (maior especificidade primeiro)
    ("COMMENT",  r"#.*"),
    ("WS",       r"[ \t\r\n]+"),

    # símbolos
    ("LBRACE",   r"\{"),
    ("RBRACE",   r"\}"),
    ("DOT",      r"\."),
    ("SEMI",     r";"),
    ("COMMA",    r","),

    # variáveis ?nome
    ("VAR",      r"\?[A-Za-z_][A-Za-z0-9_]*"),

    # literais "..." com escapes básicos e opcional @lang
    ("STRING",   r"\"(?:\\.|[^\"\\])*\"(?:@[A-Za-z]+(?:-[A-Za-z0-9]+)*)?"),

    # números (para LIMIT, etc.)
    ("INT",      r"\d+"),

    # nomes qualificados tipo dbo:artist, foaf:name
    # prefixo: [A-Za-z_][\w.-]*  local: [A-Za-z_][\w.-]*
    ("QNAME",    r"[A-Za-z_][A-Za-z0-9_.-]*:[A-Za-z_][A-Za-z0-9_.-]*"),

    # identificadores "soltos" (ex: a, prefixos mal-encadeados, etc.)
    ("IDENT",    r"[A-Za-z_][A-Za-z0-9_-]*"),
]

MASTER_RE = re.compile("|".join(f"(?P<{name}>{pattern})" for name, pattern in TOKEN_SPECS))

def lex(text: str) -> Iterator[Token]:
    line = 1
    col = 1
    pos = 0
    n = len(text)

    while pos < n:
        m = MASTER_RE.match(text, pos)
        if not m:
            snippet = text[pos:pos+30]
            raise LexError(f"Carácter inesperado na linha {line}, coluna {col}: {snippet!r}")

        kind = m.lastgroup
        value = m.group(kind)

        if kind == "WS":
            # atualizar linha/coluna
            newlines = value.count("\n")
            if newlines:
                line += newlines
                col = 1 + len(value) - (value.rfind("\n") + 1)
            else:
                col += len(value)
        elif kind == "COMMENT":
            # comentário ignora, mas atualiza posição/coluna
            col += len(value)
        else:
            # keywords / special handling
            if kind == "IDENT":
                low = value.lower()
                if low in KEYWORDS:
                    kind = KEYWORDS[low]
                elif low in SPECIAL:
                    kind = SPECIAL[low]
                else:
                    kind = "IDENT"

            yield Token(kind, value, line, col)
            col += len(value)

        pos = m.end()

        
if __name__ == "__main__":
    import sys

    if sys.stdin.isatty():
        sample = '''# DBPedia: obras de Chuck Berry
select ?nome ?desc where {
 ?s a dbo:MusicalArtist.
 ?s foaf:name "Chuck Berry"@en .
 ?w dbo:artist ?s.
 ?w foaf:name ?nome.
 ?w dbo:abstract ?desc
} LIMIT 1000
'''
        text = sample
    else:
        text = sys.stdin.read()

    for tok in lex(text):
        print(f"{tok.line}:{tok.col}\t{tok.type:8}\t{tok.value}")
