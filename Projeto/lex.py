import sys
import re
import ply.lex as lex


# PALAVRAS RESERVADAS
# Dicionário reserved que mapeia palavras-chave (em minúsculas) para os tokens, isto garante case-insensitivity automático e uniforme para todo o Pascal

reserved = {
    'program': 'PROGRAM',
    'procedure': 'PROCEDURE',
    'function': 'FUNCTION',
    'var': 'VAR',
    'array': 'ARRAY',
    'of': 'OF',
    'begin': 'BEGIN',
    'end': 'END',
    'readln': 'READLN',
    'read': 'READ',
    'writeln': 'WRITELN',
    'write': 'WRITE',
    'if': 'IF',
    'then': 'THEN',
    'else': 'ELSE',
    'while': 'WHILE',
    'downto': 'DOWNTO',
    'for': 'FOR',
    'to': 'TO',
    'do': 'DO',
    'true': 'TRUE',
    'false': 'FALSE',
    'div': 'DIV',
    'mod': 'MOD',
    'not': 'NOT',
    'and': 'AND',
    'or': 'OR',
    'string': 'STRING',
    'char': 'CHAR',
    'boolean': 'BOOLEAN',
    'real': 'REAL',
    'integer': 'INTEGER',
    'length': 'LENGTH',
}


# LISTA DE TOKENS

tokens = [
    'ID', 'REAL_NUMBER', 'NUMBER', 'STRING_LITERAL',
    'ASSIGN', 'EQUALS', 'NOT_EQUALS',
    'LESS_THAN', 'LESS_THAN_OR_EQUAL_TO',
    'GREATER_THAN', 'GREATER_THAN_OR_EQUAL_TO',
    'RANGE'
] + list(reserved.values())


# LITERALS

literals = [';', ',', '(', ')', '.', ':', '[', ']', '+', '-', '*', '/']


# EXPRESSÕES REGULARES DOS TOKENS

t_ignore = ' \t'

def t_ASSIGN(t):
    r':='
    return t

def t_EQUALS(t):
    r'='
    return t

def t_NOT_EQUALS(t):
    r'<>|!='
    return t

def t_LESS_THAN_OR_EQUAL_TO(t):
    r'<='
    return t

def t_GREATER_THAN_OR_EQUAL_TO(t):
    r'>='
    return t

def t_LESS_THAN(t):
    r'<'
    return t

def t_GREATER_THAN(t):
    r'>'
    return t

def t_RANGE(t):
    r'\.\.'
    return t

def t_STRING_LITERAL(t):
    r"'([^']|'')*'"
    # Remove aspas externas e converte '' para '
    t.value = t.value[1:-1].replace("''", "'")
    return t

def t_REAL_NUMBER(t):
    r'\d+\.\d+'
    t.value = float(t.value)
    return t

def t_NUMBER(t):
    r'\d+'
    t.value = int(t.value)
    return t

# ID deve vir DEPOIS de todos os tokens de palavras-chave para garantir que palavras reservadas não sejam reconhecidas como IDs

def t_ID(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    # Verifica se é palavra reservada (case-insensitive)
    t.type = reserved.get(t.value.lower(), 'ID')
    if t.type == 'TRUE':
        t.value = True
    elif t.type == 'FALSE':
        t.value = False
    return t

# Comentários estilo { ... }
def t_COMMENT_BRACE(t):
    r'\{[^}]*\}'
    # Conta novas linhas dentro do comentário
    t.lexer.lineno += t.value.count('\n')
    pass  # ignora comentários

# Comentários estilo (* ... *)
def t_COMMENT_PAREN(t):
    r'\(\*(.|\n)*?\*\)'
    t.lexer.lineno += t.value.count('\n')
    pass

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

def t_error(t):
    print(f"Caracter ilegal: {t.value[0]} na linha {t.lexer.lineno}")
    t.lexer.skip(1)
  
lexer = lex.lex()