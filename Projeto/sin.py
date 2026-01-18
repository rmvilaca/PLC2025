import ply.yacc as yacc
from lex import tokens, lexer

# Precedência e associatividade dos operadores
precedence = (
    ('left', 'OR'),
    ('left', 'AND'),
    ('right', 'NOT'),
    ('left', 'EQUALS', 'NOT_EQUALS', 'LESS_THAN', 'LESS_THAN_OR_EQUAL_TO', 
             'GREATER_THAN', 'GREATER_THAN_OR_EQUAL_TO'),
    ('left', '+', '-'),
    ('left', '*', '/', 'DIV', 'MOD'),
    ('right', 'UMINUS'),  # Para menos unário
)


# ESTRUTURA PRINCIPAL DO PROGRAMA

def p_gramatica(p):
    '''gramatica : programa '.' '''
    p[0] = ('gramatica', p[1])


def p_programa(p):
    '''programa : cabecalho corpo'''
    p[0] = ('programa', p[1], p[2])


def p_cabecalho(p):
    '''cabecalho : titulo declaracoes_variaveis declaracao_subprogramas declaracoes_variaveis_finais'''
    # Combina vars iniciais e finais
    vars_iniciais = p[2]
    vars_finais = p[4]
    # Junta as duas secções de variáveis
    if vars_iniciais and vars_finais:
        # Ambas existem - combinar declarações
        decls_ini = vars_iniciais[1] if vars_iniciais else []
        decls_fim = vars_finais[1] if vars_finais else []
        vars_combinadas = ('var_section', decls_ini + decls_fim)
    elif vars_iniciais:
        vars_combinadas = vars_iniciais
    elif vars_finais:
        vars_combinadas = vars_finais
    else:
        vars_combinadas = None
    p[0] = ('cabecalho', p[1], p[3], vars_combinadas)


def p_declaracoes_variaveis_finais(p):
    '''declaracoes_variaveis_finais : VAR declaracoes
                                    | empty'''
    if len(p) == 3:
        p[0] = ('var_section', p[2])
    else:
        p[0] = None


def p_titulo(p):
    '''titulo : PROGRAM ID ';' '''
    p[0] = ('titulo', p[2])


# DECLARAÇÃO DE SUBPROGRAMAS (PROCEDURES E FUNCTIONS)

def p_declaracao_subprogramas(p):
    '''declaracao_subprogramas : declaracao_subprogramas procedure_declaration
                               | declaracao_subprogramas function_declaration
                               | empty'''
    if len(p) == 2:
        p[0] = []
    else:
        p[0] = p[1] + [p[2]]


def p_procedure_declaration(p):
    '''procedure_declaration : PROCEDURE ID ';' bloco_subprograma ';'
                             | PROCEDURE ID '(' parametros ')' ';' bloco_subprograma ';' '''
    if len(p) == 6:
        p[0] = ('procedure', p[2], [], p[4])
    else:
        p[0] = ('procedure', p[2], p[4], p[7])


def p_function_declaration(p):
    '''function_declaration : FUNCTION ID ':' tipo ';' bloco_subprograma ';'
                            | FUNCTION ID '(' parametros ')' ':' tipo ';' bloco_subprograma ';' '''
    if len(p) == 8:
        p[0] = ('function', p[2], [], p[4], p[6])
    else:
        p[0] = ('function', p[2], p[4], p[7], p[9])


def p_bloco_subprograma(p):
    '''bloco_subprograma : declaracoes_variaveis corpo'''
    p[0] = ('bloco', p[1], p[2])


def p_parametros(p):
    '''parametros : lista_parametros
                  | empty'''
    p[0] = p[1] if p[1] else []


def p_lista_parametros(p):
    '''lista_parametros : lista_id ':' tipo
                        | lista_id ':' tipo ';' lista_parametros'''
    if len(p) == 4:
        p[0] = [('param', p[1], p[3])]
    else:
        p[0] = [('param', p[1], p[3])] + p[5]


# DECLARAÇÕES DE VARIÁVEIS

def p_declaracoes_variaveis(p):
    '''declaracoes_variaveis : VAR declaracoes
                             | empty'''
    if len(p) == 3:
        p[0] = ('var_section', p[2])
    else:
        p[0] = None


def p_declaracoes(p):
    '''declaracoes : declaracao
                   | declaracao declaracoes'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = [p[1]] + p[2]


def p_declaracao(p):
    '''declaracao : lista_id ':' tipo ';' '''
    p[0] = ('var_decl', p[1], p[3])


def p_lista_id(p):
    '''lista_id : ID
                | lista_id ',' ID'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[3]]


# TIPOS

def p_tipo(p):
    '''tipo : INTEGER
            | REAL
            | BOOLEAN
            | CHAR
            | STRING
            | tipo_array'''
    p[0] = p[1] if isinstance(p[1], str) else p[1]


def p_tipo_array(p):
    '''tipo_array : ARRAY '[' NUMBER RANGE NUMBER ']' OF tipo'''
    p[0] = ('array', p[3], p[5], p[8])


# CORPO DO PROGRAMA

def p_corpo(p):
    '''corpo : BEGIN lista_instrucoes END'''
    p[0] = ('begin_end', p[2])


def p_lista_instrucoes(p):
    '''lista_instrucoes : instrucao
                        | lista_instrucoes ';' instrucao'''
    if len(p) == 2:
        p[0] = [p[1]] if p[1] is not None else []
    else:
        p[0] = p[1] + ([p[3]] if p[3] is not None else [])


# INSTRUÇÕES

def p_instrucao(p):
    '''instrucao : atribuicao
                 | leitura
                 | escrita
                 | if_statement
                 | while_statement
                 | for_statement
                 | chamada_procedimento
                 | bloco
                 | empty'''
    p[0] = p[1]


def p_bloco(p):
    '''bloco : BEGIN lista_instrucoes END'''
    p[0] = ('begin_end', p[2])


def p_atribuicao(p):
    '''atribuicao : variavel ASSIGN expressao'''
    p[0] = ('assign', p[1], p[3])


def p_chamada_procedimento(p):
    '''chamada_procedimento : ID '(' lista_expressao ')'
                            | ID'''
    if len(p) == 2:
        p[0] = ('call', p[1], [])
    else:
        p[0] = ('call', p[1], p[3])


# COMANDOS DE ENTRADA/SAÍDA

def p_leitura(p):
    '''leitura : READ '(' lista_variaveis ')'
               | READLN '(' lista_variaveis ')'
               | READLN'''
    if len(p) == 2:
        p[0] = ('readln', [])
    elif p[1].lower() == 'read':
        p[0] = ('read', p[3])
    else:
        p[0] = ('readln', p[3])


def p_escrita(p):
    '''escrita : WRITE '(' lista_expressao ')'
               | WRITELN '(' lista_expressao ')'
               | WRITELN'''
    if len(p) == 2:
        p[0] = ('writeln', [])
    elif p[1].lower() == 'write':
        p[0] = ('write', p[3])
    else:
        p[0] = ('writeln', p[3])


def p_lista_variaveis(p):
    '''lista_variaveis : variavel
                       | lista_variaveis ',' variavel'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[3]]


# ESTRUTURAS DE CONTROLE

def p_if_statement(p):
    '''if_statement : IF expressao THEN instrucao
                    | IF expressao THEN instrucao ELSE instrucao'''
    if len(p) == 5:
        p[0] = ('if', p[2], p[4], None)
    else:
        p[0] = ('if', p[2], p[4], p[6])


def p_while_statement(p):
    '''while_statement : WHILE expressao DO instrucao'''
    p[0] = ('while', p[2], p[4])


def p_for_statement(p):
    '''for_statement : FOR ID ASSIGN expressao TO expressao DO instrucao
                     | FOR ID ASSIGN expressao DOWNTO expressao DO instrucao'''
    p[0] = ('for', p[2], p[4], p[6], p[5].lower(), p[8])


# EXPRESSÕES

def p_lista_expressao(p):
    '''lista_expressao : expressao
                       | lista_expressao ',' expressao'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[3]]


def p_expressao(p):
    '''expressao : expressao_logica'''
    p[0] = p[1]


def p_expressao_logica(p):
    '''expressao_logica : expressao_logica OR expressao_relacional
                        | expressao_logica AND expressao_relacional
                        | expressao_relacional'''
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = ('binop', p[2].lower(), p[1], p[3])


def p_expressao_relacional(p):
    '''expressao_relacional : expressao_aritmetica operador_relacional expressao_aritmetica
                            | expressao_aritmetica'''
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = ('binop', p[2], p[1], p[3])


def p_operador_relacional(p):
    '''operador_relacional : EQUALS
                           | NOT_EQUALS
                           | LESS_THAN
                           | LESS_THAN_OR_EQUAL_TO
                           | GREATER_THAN
                           | GREATER_THAN_OR_EQUAL_TO'''
    p[0] = p[1]


def p_expressao_aritmetica(p):
    '''expressao_aritmetica : expressao_aritmetica '+' termo
                            | expressao_aritmetica '-' termo
                            | termo'''
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = ('binop', p[2], p[1], p[3])


def p_termo(p):
    '''termo : termo '*' fator
             | termo '/' fator
             | termo DIV fator
             | termo MOD fator
             | fator'''
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = ('binop', p[2].lower() if isinstance(p[2], str) and p[2].isupper() else p[2], p[1], p[3])


def p_fator(p):
    '''fator : NUMBER
             | REAL_NUMBER
             | STRING_LITERAL
             | TRUE
             | FALSE
             | variavel
             | chamada_funcao
             | '(' expressao ')' '''
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = p[2]


def p_fator_not(p):
    '''fator : NOT fator'''
    p[0] = ('unop', 'not', p[2])


def p_fator_menos_unario(p):
    '''fator : '-' fator %prec UMINUS'''
    p[0] = ('unop', '-', p[2])


def p_fator_mais_unario(p):
    '''fator : '+' fator %prec UMINUS'''
    p[0] = ('unop', '+', p[2])


# VARIÁVEIS E CHAMADAS DE FUNÇÃO

def p_variavel(p):
    '''variavel : ID
                | ID '[' expressao ']' '''
    if len(p) == 2:
        p[0] = ('var', p[1])
    else:
        p[0] = ('array_access', p[1], p[3])


def p_chamada_funcao(p):
    '''chamada_funcao : ID '(' lista_expressao ')'
                      | LENGTH '(' expressao ')' '''
    if len(p) == 5 and p[1].lower() == 'length':
        p[0] = ('call', 'length', [p[3]])
    else:
        p[0] = ('call', p[1], p[3])


# Empty

def p_empty(p):
    '''empty :'''
    pass


# TRATAMENTO DE ERROS

def p_error(p):
    if p:
        print(f"Erro de sintaxe no token '{p.value}' (tipo: {p.type}) na linha {p.lineno}")
        parser.errok()
    else:
        print("Erro de sintaxe: fim de arquivo inesperado")


# PARSER
parser = yacc.yacc()

# Auxiliar
def print_ast(node, indent=0):
    """Imprime a AST de forma hierárquica"""
    spacing = "  " * indent
    
    if isinstance(node, tuple):
        print(f"{spacing}({node[0]}")
        for child in node[1:]:
            if child is not None:
                print_ast(child, indent + 1)
        print(f"{spacing})")
    elif isinstance(node, list):
        if node:  # Só imprime se a lista não estiver vazia
            print(f"{spacing}[")
            for item in node:
                if item is not None:
                    print_ast(item, indent + 1)
            print(f"{spacing}]")
    else:
        print(f"{spacing}{repr(node)}")

# para testar com: python3 sin.py
def parse_file(filename):
    """Lê um arquivo e retorna a AST"""
    try:
        with open(filename, 'r') as f:
            data = f.read()
        return parser.parse(data, lexer=lexer)
    except FileNotFoundError:
        print(f"Erro: Arquivo '{filename}' não encontrado.")
        return None

def parse_string(code):
    return parser.parse(code, lexer=lexer)

# if __name__ == '__main__':
#     print("Teste do Parser")
#     code = "program Teste; begin writeln('Ola'); end."
#     result = parse_string(code)
#     print(result)