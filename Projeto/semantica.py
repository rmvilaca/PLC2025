import sys
from sin import parse_file, parse_string

class TabelaSimbolos:
    def __init__(self):
        self.escopos = [{}]
        self.funcoes = {}

    def entrar_escopo(self):
        self.escopos.append({})

    def sair_escopo(self):
        self.escopos.pop()

    def declarar_variavel(self, nome, tipo_info):
        """
        tipo_info é um dicionário:
        Para tipos simples: {'categoria': 'INTEGER', 'tipo_base': None}
        Para arrays: {'categoria': 'ARRAY', 'min_index': 1, 'max_index': 5, 'tipo_base': 'INTEGER'}
        """
        escopo_atual = self.escopos[-1]
        if nome in escopo_atual:
            return False
        escopo_atual[nome] = tipo_info
        return True

    def procurar_variavel(self, nome):
        for escopo in reversed(self.escopos):
            if nome in escopo:
                return escopo[nome]
        return None

    def declarar_funcao(self, nome, tipo_retorno, params):
        if nome in self.funcoes:
            return False
        self.funcoes[nome] = {'tipo_retorno': tipo_retorno, 'params': params}
        return True

    def procurar_funcao(self, nome):
        return self.funcoes.get(nome)


class AnalisadorSemantico:
    def __init__(self):
        self.tabela = TabelaSimbolos()
        self.erros = []
        self.tipo_retorno_atual = None

    def registar_erro(self, msg):
        self.erros.append(f"Erro Semântico: {msg}")

    def visit(self, node):
        if node is None:
            return None
        
        if isinstance(node, list):
            for item in node:
                self.visit(item)
            return None

        # Valores primitivos retornam tipo diretamente
        if isinstance(node, bool):
            return {'categoria': 'BOOLEAN'}
        if isinstance(node, int):
            return {'categoria': 'INTEGER'}
        if isinstance(node, float):
            return {'categoria': 'REAL'}
        if isinstance(node, str):
            return {'categoria': 'STRING'}

        if isinstance(node, tuple):
            tipo_no = node[0]
            metodo_nome = f'visit_{tipo_no}'
            visitante = getattr(self, metodo_nome, self.visit_generico)
            return visitante(node)
        
        return None

    def visit_generico(self, node):
        return None

    # ESTRUTURA DO PROGRAMA

    def visit_gramatica(self, node):
        self.visit(node[1])

    def visit_programa(self, node):
        _, cabecalho, corpo = node
        self.visit(cabecalho)
        self.visit(corpo)

    def visit_cabecalho(self, node):
        _, titulo, subprogs, vars_globais = node
        
        if vars_globais:
            self.visit(vars_globais)
            
        if subprogs:
            self.visit(subprogs)

    # DECLARAÇÕES DE VARIÁVEIS

    def visit_var_section(self, node):
        self.visit(node[1])

    def visit_var_decl(self, node):
        _, lista_id, tipo_raw = node
        
        # Construir tipo_info estruturado
        if isinstance(tipo_raw, tuple) and tipo_raw[0] == 'array':
            # tipo_raw = ('array', min, max, tipo_base)
            tipo_info = {
                'categoria': 'ARRAY',
                'min_index': tipo_raw[1],
                'max_index': tipo_raw[2],
                'tipo_base': str(tipo_raw[3]).upper()
            }
        else:
            tipo_info = {
                'categoria': str(tipo_raw).upper(),
                'tipo_base': None
            }

        for nome_var in lista_id:
            sucesso = self.tabela.declarar_variavel(nome_var, tipo_info)
            if not sucesso:
                self.registar_erro(f"Variável '{nome_var}' já declarada neste escopo.")

    # SUBPROGRAMAS

    def visit_function(self, node):
        _, nome, params, tipo_ret, corpo = node
        
        tipos_params = []
        if params:
            for p in params:
                tipo_p = str(p[2]).upper()
                quantidade = len(p[1])
                for _ in range(quantidade):
                    tipos_params.append(tipo_p)

        tipo_ret_str = str(tipo_ret).upper()
        
        if not self.tabela.declarar_funcao(nome, tipo_ret_str, tipos_params):
            self.registar_erro(f"Função '{nome}' já definida.")

        self.tabela.entrar_escopo()
        self.tipo_retorno_atual = tipo_ret_str

        # Nome da função como variável de retorno
        self.tabela.declarar_variavel(nome, {'categoria': tipo_ret_str, 'tipo_base': None})

        if params:
            for p in params:
                ids_params = p[1]
                tipo_p = str(p[2]).upper()
                for pid in ids_params:
                    self.tabela.declarar_variavel(pid, {'categoria': tipo_p, 'tipo_base': None})

        self.visit(corpo)

        self.tabela.sair_escopo()
        self.tipo_retorno_atual = None

    def visit_procedure(self, node):
        _, nome, params, corpo = node
        
        tipos_params = []
        if params:
            for p in params:
                tipo_p = str(p[2]).upper()
                quantidade = len(p[1])
                for _ in range(quantidade):
                    tipos_params.append(tipo_p)

        if not self.tabela.declarar_funcao(nome, None, tipos_params):
            self.registar_erro(f"Procedimento '{nome}' já definido.")

        self.tabela.entrar_escopo()

        if params:
            for p in params:
                ids_params = p[1]
                tipo_p = str(p[2]).upper()
                for pid in ids_params:
                    self.tabela.declarar_variavel(pid, {'categoria': tipo_p, 'tipo_base': None})

        self.visit(corpo)
        self.tabela.sair_escopo()

    def visit_bloco(self, node):
        _, decls, corpo_instrucoes = node
        if decls:
            self.visit(decls)
        self.visit(corpo_instrucoes)

    # INSTRUÇÕES

    def visit_begin_end(self, node):
        self.visit(node[1])

    def visit_assign(self, node):
        _, var_node, expr_node = node
        
        tipo_var = self.visit(var_node)
        tipo_expr = self.visit(expr_node)

        if not tipo_var or not tipo_expr:
            return

        cat_var = tipo_var['categoria']
        cat_expr = tipo_expr['categoria']

        if cat_var == cat_expr:
            return
        
        #  INTEGER  REAL
        if cat_var == 'REAL' and cat_expr == 'INTEGER':
            return
        
        self.registar_erro(f"Atribuição incompatível: '{cat_expr}' -> '{cat_var}'")

    def visit_if(self, node):
        _, cond, stmt_then, stmt_else = node
        
        tipo_cond = self.visit(cond)
        if tipo_cond and tipo_cond['categoria'] != 'BOOLEAN':
            self.registar_erro(f"Condição IF deve ser BOOLEAN, não {tipo_cond['categoria']}")
        
        self.visit(stmt_then)
        if stmt_else:
            self.visit(stmt_else)

    def visit_while(self, node):
        _, cond, corpo = node
        tipo_cond = self.visit(cond)
        if tipo_cond and tipo_cond['categoria'] != 'BOOLEAN':
            self.registar_erro(f"Condição WHILE deve ser BOOLEAN, não {tipo_cond['categoria']}")
        self.visit(corpo)

    def visit_for(self, node):
        _, var_nome, inicio, fim, direcao, corpo = node
        
        var_info = self.tabela.procurar_variavel(var_nome)
        if not var_info:
            self.registar_erro(f"Variável de controlo '{var_nome}' não declarada.")
        elif var_info['categoria'] != 'INTEGER':
            self.registar_erro(f"Variável de controlo do FOR deve ser INTEGER.")

        t_inicio = self.visit(inicio)
        t_fim = self.visit(fim)
        
        if t_inicio and t_inicio['categoria'] != 'INTEGER':
            self.registar_erro("Limite inicial do FOR deve ser INTEGER.")
        if t_fim and t_fim['categoria'] != 'INTEGER':
            self.registar_erro("Limite final do FOR deve ser INTEGER.")
            
        self.visit(corpo)

    # EXPRESSÕES

    def visit_binop(self, node):
        _, op, esq, dir_node = node
        
        t_esq = self.visit(esq)
        t_dir = self.visit(dir_node)
        
        if not t_esq or not t_dir:
            return {'categoria': 'REAL'}  # Tipo dummy para evitar cascata de erros
        
        cat_esq = t_esq['categoria']
        cat_dir = t_dir['categoria']
        
        # Operações Aritméticas
        if op in ['+', '-', '*', '/', 'div', 'mod']:
            # Concatenação de strings (apenas com +)
            if op == '+' and (cat_esq == 'STRING' or cat_dir == 'STRING'):
                if cat_esq != 'STRING' or cat_dir != 'STRING':
                    self.registar_erro("Concatenação requer ambos os operandos STRING.")
                return {'categoria': 'STRING'}
            
            is_int = (cat_esq == 'INTEGER' and cat_dir == 'INTEGER')
            is_num = (cat_esq in ['INTEGER', 'REAL'] and cat_dir in ['INTEGER', 'REAL'])
            
            if not is_num:
                self.registar_erro(f"Operador '{op}' requer números, não {cat_esq} e {cat_dir}")
                return {'categoria': 'REAL'}
            
            if op == '/':
                return {'categoria': 'REAL'}  # Divisão real sempre retorna REAL
            
            if op in ['div', 'mod']:
                if not is_int:
                    self.registar_erro("DIV/MOD requerem operandos INTEGER.")
                return {'categoria': 'INTEGER'}
            
            # Para +, -, *: se houver REAL, resultado é REAL
            if cat_esq == 'REAL' or cat_dir == 'REAL':
                return {'categoria': 'REAL'}
            return {'categoria': 'INTEGER'}
        
        # Operações Relacionais
        if op in ['=', '<>', '!=', '<', '<=', '>', '>=']:
            if cat_esq != cat_dir:
                # Permite comparações entre números (INTEGER vs REAL)
                is_num = (cat_esq in ['INTEGER', 'REAL'] and cat_dir in ['INTEGER', 'REAL'])
                
                # Permite comparações entre CHAR e STRING (ex: bin[i] = '1')
                # Isto é comum em Pascal quando se indexa strings
                is_char_str = (cat_esq in ['CHAR', 'STRING'] and cat_dir in ['CHAR', 'STRING'])
                
                if not is_num and not is_char_str:
                    self.registar_erro(f"Comparação inválida: {cat_esq} vs {cat_dir}")
            
            return {'categoria': 'BOOLEAN'}
        
        # Operações Lógicas
        if op in ['and', 'or']:
            if cat_esq != 'BOOLEAN' or cat_dir != 'BOOLEAN':
                self.registar_erro(f"Operador lógico '{op}' requer operandos BOOLEAN.")
            return {'categoria': 'BOOLEAN'}
        
        return {'categoria': 'REAL'}

    def visit_unop(self, node):
        _, op, operand = node
        t = self.visit(operand)
        
        if not t:
            return None
        
        cat = t['categoria']
        
        if op == 'not':
            if cat != 'BOOLEAN':
                self.registar_erro("NOT requer BOOLEAN.")
            return {'categoria': 'BOOLEAN'}
        
        if op in ['+', '-']:
            if cat not in ['INTEGER', 'REAL']:
                self.registar_erro(f"Sinal unário '{op}' requer número.")
            return t
        
        return t

    # VARIÁVEIS E ACESSO

    def visit_var(self, node):
        nome = node[1]
        info = self.tabela.procurar_variavel(nome)
        if not info:
            self.registar_erro(f"Variável '{nome}' não declarada.")
            return None
        return info

    def visit_array_access(self, node):
        _, nome, expr_index = node
        info = self.tabela.procurar_variavel(nome)
        
        if not info:
            self.registar_erro(f"'{nome}' não foi declarado.")
            return None
        
        t_index = self.visit(expr_index)
        if t_index and t_index['categoria'] != 'INTEGER':
            self.registar_erro("Índice de array/string deve ser INTEGER.")

        # Strings podem ser indexadas retorna CHAR
        if info['categoria'] == 'STRING':
            return {'categoria': 'CHAR'}
        
        if info['categoria'] != 'ARRAY':
            self.registar_erro(f"'{nome}' não é array ou string.")
            return info

        return {'categoria': info['tipo_base']}

    def visit_call(self, node):
        _, nome, args = node

        # Built-in: LENGTH
        if nome.lower() == 'length':
            if len(args) != 1:
                self.registar_erro("LENGTH requer 1 argumento.")
            else:
                arg_tipo = self.visit(args[0])
                if arg_tipo and arg_tipo['categoria'] not in ['STRING', 'ARRAY']:
                    self.registar_erro("LENGTH requer STRING ou ARRAY.")
            return {'categoria': 'INTEGER'}

        func_info = self.tabela.procurar_funcao(nome)
        if not func_info:
            self.registar_erro(f"Função/Procedimento '{nome}' não declarado.")
            return None

        params_esperados = func_info['params']
        if len(args) != len(params_esperados):
            self.registar_erro(
                f"'{nome}' espera {len(params_esperados)} args, recebeu {len(args)}."
            )
            if func_info['tipo_retorno']:
                return {'categoria': func_info['tipo_retorno']}
            return None

        # Validar tipos
        for i, (arg_node, tipo_esp) in enumerate(zip(args, params_esperados)):
            tipo_passado = self.visit(arg_node)
            if tipo_passado:
                cat_pass = tipo_passado['categoria']
                if cat_pass != tipo_esp:
                    if not (tipo_esp == 'REAL' and cat_pass == 'INTEGER'):
                        self.registar_erro(
                            f"Arg {i+1} de '{nome}': esperava {tipo_esp}, recebeu {cat_pass}"
                        )

        if func_info['tipo_retorno']:
            return {'categoria': func_info['tipo_retorno']}
        return None

    def visit_readln(self, node):
        for v in node[1]:
            tipo = self.visit(v)
            # Verifica se é L-value válido (variável ou array access)
            if isinstance(v, tuple) and v[0] == 'var':
                if not self.tabela.procurar_variavel(v[1]):
                    self.registar_erro(f"Variável '{v[1]}' no readln não existe.")
    
    def visit_read(self, node):
        self.visit_readln(node)

    def visit_writeln(self, node):
        for expr in node[1]:
            self.visit(expr)
            
    def visit_write(self, node):
        self.visit_writeln(node)