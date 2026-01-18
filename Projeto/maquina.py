import sys
from sin import parse_file
from semantica import AnalisadorSemantico

class GeradorCodigo:
    def __init__(self):
        self.codigo = []
        self.contador_labels = 0
        self.tabela_simbolos = {}  # {nome: {'addr': int, 'size': int, 'tipo': str}}
        self.endereco_atual = 0
        self.funcoes = {} 
        self.funcao_atual = None 
        self.info_arrays = {}  # {nome: {'min': int, 'max': int, 'tipo_base': str}}
        self.funcoes_processadas = set()
        self.params_locais = {}  # {nome_param: {'offset': int, 'tipo': str}} - parâmetros de funções
        self.vars_locais = {}    # {nome_var: {'offset': int, 'tipo': str}} - variáveis locais
        self.local_offset = 0    # Contador para variáveis locais

    def novo_label(self):
        self.contador_labels += 1
        return f"label{self.contador_labels}"
    
    def obter_endereco(self, nome_var, size=1, tipo='INTEGER'):
        if nome_var not in self.tabela_simbolos:
            self.tabela_simbolos[nome_var] = {
                'addr': self.endereco_atual,
                'size': size,
                'tipo': tipo
            }
            self.endereco_atual += size
        return self.tabela_simbolos[nome_var]['addr']

    def emitir(self, op, arg=None):
        if arg is None:
            self.codigo.append(f"{op}")
        else:
            self.codigo.append(f"{op} {arg}")

    def visit_generico(self, node):
        """Fallback para nós não implementados"""
        if isinstance(node, tuple) and len(node) > 0:
            print(f"AVISO: Nó não implementado: {node[0]}")
        return None

    def visit(self, node):
        if node is None: 
            return None
        if isinstance(node, list):
            for item in node: 
                self.visit(item)
            return None

        if isinstance(node, bool):
            valor = 1 if node else 0
            self.emitir('PUSHI', valor)
            return 'BOOLEAN'

        if isinstance(node, int):
            self.emitir('PUSHI', node)
            return 'INTEGER'
        if isinstance(node, float):
            self.emitir('PUSHF', node)
            return 'REAL'
        if isinstance(node, str):
            self.emitir('PUSHS', f'"{node}"')
            # Se é um único caractere, converter para código ASCII para comparações
            if len(node) == 1:
                self.emitir('CHRCODE')
                return 'CHAR'
            return 'STRING'
        
        if isinstance(node, tuple):
            tipo = node[0]
            metodo = getattr(self, f'visit_{tipo}', self.visit_generico)
            return metodo(node)
        
        return None

    def inferir_tipo(self, node):
        """Infere o tipo de uma expressão sem gerar código"""
        if node is None:
            return 'INTEGER'
        if isinstance(node, bool):
            return 'BOOLEAN'
        if isinstance(node, int):
            return 'INTEGER'
        if isinstance(node, float):
            return 'REAL'
        if isinstance(node, str):
            return 'STRING'
        if isinstance(node, tuple):
            if node[0] == 'var':
                nome = node[1]
                if nome in self.tabela_simbolos:
                    return self.tabela_simbolos[nome].get('tipo', 'INTEGER')
                return 'INTEGER'
            elif node[0] == 'array_access':
                nome = node[1]
                if nome in self.info_arrays:
                    return self.info_arrays[nome].get('tipo_base', 'INTEGER')
                # Se não é array, pode ser string
                if nome in self.tabela_simbolos:
                    if self.tabela_simbolos[nome].get('tipo') == 'STRING':
                        return 'CHAR'
                return 'INTEGER'
            elif node[0] == 'binop':
                op = node[1]
                if op in ['=', '<>', '!=', '<', '<=', '>', '>=', 'and', 'or']:
                    return 'BOOLEAN'
                elif op == '/':
                    return 'REAL'
                else:
                    t1 = self.inferir_tipo(node[2])
                    t2 = self.inferir_tipo(node[3])
                    if t1 == 'REAL' or t2 == 'REAL':
                        return 'REAL'
                    if t1 == 'STRING' or t2 == 'STRING':
                        return 'STRING'
                    return 'INTEGER'
            elif node[0] == 'unop':
                if node[1] == 'not':
                    return 'BOOLEAN'
                return self.inferir_tipo(node[2])
            elif node[0] == 'call':
                nome = node[1]
                if nome.lower() == 'length':
                    return 'INTEGER'
                if nome in self.funcoes:
                    return 'INTEGER'
        return 'INTEGER'

    def visit_var_decl(self, node):
        """Processa declarações de variáveis para alocar espaço"""
        _, lista_id, tipo_raw = node
        
        if isinstance(tipo_raw, tuple) and tipo_raw[0] == 'array':
            min_idx = tipo_raw[1]
            max_idx = tipo_raw[2]
            tipo_base = str(tipo_raw[3]).upper() if isinstance(tipo_raw[3], str) else 'INTEGER'
            tamanho = max_idx - min_idx + 1
            
            for nome_var in lista_id:
                self.obter_endereco(nome_var, tamanho, 'ARRAY')
                self.info_arrays[nome_var] = {'min': min_idx, 'max': max_idx, 'tipo_base': tipo_base}
        else:
            tipo = str(tipo_raw).upper() if tipo_raw else 'INTEGER'
            for nome_var in lista_id:
                self.obter_endereco(nome_var, 1, tipo)

    def visit_declaracao_subprogramas(self, node):
        pass
    
    def visit_procedure(self, node):
        _, nome, params, corpo = node
        
        if nome in self.funcoes_processadas:
            return
        self.funcoes_processadas.add(nome)
        
        self.funcoes[nome] = {'label': nome, 'num_params': 0, 'tipo': 'VOID'}
        self.emitir('LABEL', f"{nome}:")
        # Guardar contexto anterior
        old_func = self.funcao_atual
        old_params = self.params_locais.copy()
        self.funcao_atual = nome
        
        # Mapear parâmetros para offsets locais (negativos a partir do fp)
        self.params_locais = {}
        if params:
            todos_params = []
            for p in params:
                tipo_param = str(p[2]).upper() if len(p) > 2 else 'INTEGER'
                for pid in p[1]:
                    todos_params.append((pid, tipo_param))
            
            # Parâmetros são empilhados da esquerda para direita
            # Então o último parâmetro está em fp[-1], o penúltimo em fp[-2], etc.
            n_params = len(todos_params)
            for i, (param_id, tipo) in enumerate(todos_params):
                offset = -(n_params - i)  # primeiro param: -n, último: -1
                self.params_locais[param_id] = {'offset': offset, 'tipo': tipo}
        
        if corpo and corpo[0] == 'bloco':
            decls_locais = corpo[1]
            if decls_locais:
                self.processar_declaracoes(decls_locais)
        
        self.visit(corpo)
        self.emitir('RETURN')
        
        # Restaurar contexto
        self.funcao_atual = old_func
        self.params_locais = old_params 

    # ESTRUTURA E BLOCOS

    def visit_gramatica(self, node): 
        self.visit(node[1]) 
    
    def visit_programa(self, node):
        label_main = "main"
        self.emitir('JUMP', label_main)
        
        cabecalho = node[1]
        
        # processar variáveis globais para saber quantas são
        if len(cabecalho) > 3 and cabecalho[3]:
            self.processar_declaracoes(cabecalho[3])
        
        # gerar código dos subprogramas (que também declaram variáveis)
        if len(cabecalho) > 2 and cabecalho[2]:
            subprogs = cabecalho[2]
            if isinstance(subprogs, list):
                for subprog in subprogs:
                    if subprog:
                        self.visit(subprog)
        
        # gerar o main
        self.emitir('LABEL', f"{label_main}:")
        self.emitir('START')
        
        # IMPORTANTE: Alocar espaço para TODAS as variáveis globais
        if self.endereco_atual > 0:
            self.emitir('PUSHN', self.endereco_atual)
        
        self.visit(node[2])
        self.emitir('STOP')

    def visit_cabecalho(self, node):
        pass

    def processar_declaracoes(self, var_section):
        """Processa declarações para alocar endereços globais"""
        if var_section and var_section[0] == 'var_section':
            for decl in var_section[1]:
                if decl[0] == 'var_decl':
                    self.visit_var_decl(decl)

    def processar_declaracoes_locais(self, var_section):
        """Processa declarações de variáveis locais dentro de funções"""
        if var_section and var_section[0] == 'var_section':
            for decl in var_section[1]:
                if decl[0] == 'var_decl':
                    ids = decl[1]
                    tipo = str(decl[2]).upper() if len(decl) > 2 else 'INTEGER'
                    for nome in ids:
                        # Variáveis locais usam offsets positivos a partir de fp[0]
                        self.vars_locais[nome] = {'offset': self.local_offset, 'tipo': tipo}
                        self.local_offset += 1

    def visit_bloco(self, node):
        _, decls, corpo = node
        self.visit(corpo)
    
    def visit_function(self, node):
        nome = node[1]
        
        if nome in self.funcoes_processadas:
            return
        self.funcoes_processadas.add(nome)
        
        params = node[2]
        tipo_retorno = str(node[3]).upper() if node[3] else 'INTEGER'
        corpo = node[4]
        
        # Guardar info da função
        self.funcoes[nome] = {'label': nome, 'num_params': 0, 'tipo': tipo_retorno}
        self.emitir('LABEL', f"{nome}:")
        
        # Mapear parâmetros para posições locais (relativas ao fp)
        # Na EWVM, após CALL, os parâmetros estão em fp[-n], fp[-n+1], ..., fp[-1]
        params_info = []
        if params:
            for p in params:
                tipo_param = str(p[2]).upper() if len(p) > 2 else 'INTEGER'
                for pid in p[1]:
                    params_info.append((pid, tipo_param))
        
        self.funcoes[nome]['num_params'] = len(params_info)
        
        # Guardar contexto da função
        old_func = self.funcao_atual
        old_params = getattr(self, 'params_locais', {}).copy()
        old_locais = getattr(self, 'vars_locais', {}).copy()
        self.funcao_atual = nome
        
        # Mapear parâmetros: o primeiro parâmetro está em fp[-num_params], etc.
        self.params_locais = {}
        for i, (pid, tipo) in enumerate(params_info):
            # Parâmetros estão "abaixo" do fp: índice negativo
            self.params_locais[pid] = {'offset': -(len(params_info) - i), 'tipo': tipo}
        
        # Processar variáveis locais da função
        self.vars_locais = {}
        self.local_offset = 0  # Variáveis locais começam em fp[0], fp[1], etc.
        
        if corpo and corpo[0] == 'bloco':
            decls_locais = corpo[1]
            if decls_locais:
                self.processar_declaracoes_locais(decls_locais)
        
        # Alocar espaço para variáveis locais
        if self.local_offset > 0:
            self.emitir('PUSHN', self.local_offset)
        
        self.visit(corpo)
        
        # Retorno: o valor já foi guardado em fp[-(num_params+1)] pelo BinToInt := valor
        # Precisamos carregar esse valor para a stack antes de RETURN
        num_params = len(params_info)
        self.emitir('PUSHL', -(num_params + 1))
        self.emitir('RETURN')
        
        # Restaurar contexto
        self.funcao_atual = old_func
        self.params_locais = old_params
        self.vars_locais = old_locais

    # CHAMADAS E ACESSOS

    def visit_call(self, node):
        nome = node[1]
        args = node[2]
        
        if nome.lower() == 'length':
            if args:
                self.visit(args[0])
                self.emitir('STRLEN') 
            return 'INTEGER'

        if nome in self.funcoes:
            func_info = self.funcoes[nome]
            is_procedure = func_info.get('tipo', 'INTEGER') == 'VOID'
            
            # Reservar espaço para o valor de retorno (apenas para funções, não procedures)
            if not is_procedure:
                self.emitir('PUSHI', 0)
            
            for arg in args:
                self.visit(arg)
            
            self.emitir('PUSHA', nome) 
            self.emitir('CALL')
            return func_info.get('tipo', 'INTEGER')
        else:
            print(f"AVISO: Função '{nome}' não definida.")
            return 'INTEGER'

    def visit_array_access(self, node):
        nome_var = node[1]
        expr_index = node[2]
        
        if nome_var not in self.info_arrays:
            # É uma string - pode ser parâmetro, variável local, ou global
            
            # Verificar se é um parâmetro local
            if hasattr(self, 'params_locais') and nome_var in self.params_locais:
                offset = self.params_locais[nome_var]['offset']
                self.emitir('PUSHL', offset)
            # Verificar se é uma variável local
            elif hasattr(self, 'vars_locais') and nome_var in self.vars_locais:
                offset = self.vars_locais[nome_var]['offset']
                self.emitir('PUSHL', offset)
            # Variável global
            elif nome_var in self.tabela_simbolos:
                addr = self.tabela_simbolos[nome_var]['addr']
                self.emitir('PUSHG', addr)
            else:
                print(f"ERRO: Variável '{nome_var}' não declarada")
                return 'CHAR'
            
            self.visit(expr_index)
            self.emitir('PUSHI', 1)
            self.emitir('SUB')
            
            self.emitir('CHARAT')
            return 'CHAR'
        else:
            # É um array
            addr_base = self.tabela_simbolos[nome_var]['addr']
            min_idx = self.info_arrays[nome_var]['min']
            tipo_base = self.info_arrays[nome_var].get('tipo_base', 'INTEGER')
            
            # PUSHGP + offset do array
            self.emitir('PUSHGP')
            self.emitir('PUSHI', addr_base)
            self.emitir('PADD')
            
            # Índice - min
            self.visit(expr_index)
            self.emitir('PUSHI', min_idx)
            self.emitir('SUB')
            
            self.emitir('LOADN')
            return tipo_base

    # INSTRUÇÕES

    def visit_begin_end(self, node): 
        self.visit(node[1])
    
    def visit_assign(self, node):
        _, var_node, expr_node = node
        
        if var_node[0] == 'array_access':
            nome_array = var_node[1]
            expr_index = var_node[2]
            
            if nome_array not in self.tabela_simbolos:
                print(f"ERRO: Variável '{nome_array}' não declarada")
                return
                
            addr_base = self.tabela_simbolos[nome_array]['addr']
            
            if nome_array in self.info_arrays:
                min_idx = self.info_arrays[nome_array]['min']
                
                # STOREN: stores value in address[index]
                # Stack order: address, index, value (bottom to top)
                
                # Endereço base do array
                self.emitir('PUSHGP')
                self.emitir('PUSHI', addr_base)
                self.emitir('PADD')
                
                # Índice
                self.visit(expr_index)
                self.emitir('PUSHI', min_idx)
                self.emitir('SUB')
                
                # Valor
                self.visit(expr_node)
                
                self.emitir('STOREN')
            else:
                print(f"AVISO: Atribuição a caractere de string não suportada")
                
        elif var_node[0] == 'var':
            self.visit(expr_node)
            nome = var_node[1]
            
            # Verificar se é atribuição do valor de retorno da função (NomeFuncao := valor)
            if hasattr(self, 'funcao_atual') and self.funcao_atual and nome == self.funcao_atual:
                # Guardar o valor de retorno - fica na stack para RETURN
                # Usar STOREL -2 para guardar no espaço de retorno (abaixo dos parâmetros)
                num_params = len(self.params_locais) if hasattr(self, 'params_locais') else 0
                self.emitir('STOREL', -(num_params + 1))
                return
            
            # Verificar se é um parâmetro local
            if hasattr(self, 'params_locais') and nome in self.params_locais:
                offset = self.params_locais[nome]['offset']
                self.emitir('STOREL', offset)
                return
            
            # Verificar se é uma variável local
            if hasattr(self, 'vars_locais') and nome in self.vars_locais:
                offset = self.vars_locais[nome]['offset']
                self.emitir('STOREL', offset)
                return
            
            if nome not in self.tabela_simbolos:
                print(f"ERRO: Variável '{nome}' não declarada")
                return
            addr = self.tabela_simbolos[nome]['addr']
            self.emitir('STOREG', addr)

    def visit_writeln(self, node):
        exprs = node[1]
        for expr in exprs:
            tipo = self.inferir_tipo(expr)
            self.visit(expr)
            
            if tipo == 'STRING':
                self.emitir('WRITES')
            elif tipo == 'REAL':
                self.emitir('WRITEF')
            elif tipo == 'CHAR':
                self.emitir('WRITECHR')
            else:
                self.emitir('WRITEI')
        self.emitir('WRITELN')

    def visit_write(self, node):
        exprs = node[1]
        for expr in exprs:
            tipo = self.inferir_tipo(expr)
            self.visit(expr)
            
            if tipo == 'STRING':
                self.emitir('WRITES')
            elif tipo == 'REAL':
                self.emitir('WRITEF')
            elif tipo == 'CHAR':
                self.emitir('WRITECHR')
            else:
                self.emitir('WRITEI')

    def visit_readln(self, node):
        for var_node in node[1]:
            self.emitir('READ')
            
            if var_node[0] == 'var':
                nome = var_node[1]
                if nome not in self.tabela_simbolos:
                    print(f"ERRO: Variável '{nome}' não declarada")
                    continue
                    
                tipo = self.tabela_simbolos[nome].get('tipo', 'INTEGER')
                addr = self.tabela_simbolos[nome]['addr']
                
                if tipo == 'INTEGER':
                    self.emitir('ATOI')
                elif tipo == 'REAL':
                    self.emitir('ATOF')
                
                self.emitir('STOREG', addr)
                
            elif var_node[0] == 'array_access':
                nome_array = var_node[1]
                expr_index = var_node[2]
                
                if nome_array not in self.tabela_simbolos:
                    print(f"ERRO: Variável '{nome_array}' não declarada")
                    continue
                
                addr_base = self.tabela_simbolos[nome_array]['addr']
                
                if nome_array in self.info_arrays:
                    min_idx = self.info_arrays[nome_array]['min']
                    tipo_base = self.info_arrays[nome_array].get('tipo_base', 'INTEGER')
                    
                    if tipo_base == 'INTEGER':
                        self.emitir('ATOI')
                    elif tipo_base == 'REAL':
                        self.emitir('ATOF')
                    
                    # Guardar valor temporariamente
                    temp_addr = self.endereco_atual
                    self.endereco_atual += 1
                    self.emitir('STOREG', temp_addr)
                    
                    # Endereço do array
                    self.emitir('PUSHGP')
                    self.emitir('PUSHI', addr_base)
                    self.emitir('PADD')
                    
                    # Índice
                    self.visit(expr_index)
                    self.emitir('PUSHI', min_idx)
                    self.emitir('SUB')
                    
                    # Valor
                    self.emitir('PUSHG', temp_addr)
                    
                    self.emitir('STOREN')

    def visit_read(self, node):
        self.visit_readln(node)

    def visit_if(self, node):
        _, cond, stmt_then, stmt_else = node
        lbl_else = self.novo_label()
        lbl_fim = self.novo_label()
        
        self.visit(cond)
        self.emitir('JZ', lbl_else if stmt_else else lbl_fim)
        self.visit(stmt_then)
        
        if stmt_else:
            self.emitir('JUMP', lbl_fim)
            self.emitir('LABEL', f'{lbl_else}:')
            self.visit(stmt_else)
        
        self.emitir('LABEL', f'{lbl_fim}:')

    def visit_while(self, node):
        lbl_ini = self.novo_label()
        lbl_fim = self.novo_label()
        
        self.emitir('LABEL', f'{lbl_ini}:')
        self.visit(node[1])
        self.emitir('JZ', lbl_fim)
        self.visit(node[2])
        self.emitir('JUMP', lbl_ini)
        self.emitir('LABEL', f'{lbl_fim}:')

    def visit_for(self, node):
        _, var, ini, fim, dir, corpo = node
        lbl_ini = self.novo_label()
        lbl_fim = self.novo_label()
        
        # Verificar se é variável local, parâmetro ou global
        is_local = var in self.vars_locais
        is_param = var in self.params_locais
        is_global = var in self.tabela_simbolos
        
        if not is_local and not is_param and not is_global:
            print(f"ERRO: Variável de controlo '{var}' não declarada")
            return
        
        # Inicialização
        self.visit(ini)
        if is_local:
            self.emitir('STOREL', self.vars_locais[var]['offset'])
        elif is_param:
            self.emitir('STOREL', self.params_locais[var]['offset'])
        else:
            self.emitir('STOREG', self.tabela_simbolos[var]['addr'])
        
        # Loop
        self.emitir('LABEL', f'{lbl_ini}:')
        if is_local:
            self.emitir('PUSHL', self.vars_locais[var]['offset'])
        elif is_param:
            self.emitir('PUSHL', self.params_locais[var]['offset'])
        else:
            self.emitir('PUSHG', self.tabela_simbolos[var]['addr'])
        self.visit(fim)
        
        if dir == 'to':
            self.emitir('INFEQ')
        else:
            self.emitir('SUPEQ')
        
        self.emitir('JZ', lbl_fim)
        
        self.visit(corpo)
        
        # Incrementar/decrementar
        if is_local:
            self.emitir('PUSHL', self.vars_locais[var]['offset'])
        elif is_param:
            self.emitir('PUSHL', self.params_locais[var]['offset'])
        else:
            self.emitir('PUSHG', self.tabela_simbolos[var]['addr'])
        self.emitir('PUSHI', 1)
        if dir == 'to':
            self.emitir('ADD')
        else:
            self.emitir('SUB')
        if is_local:
            self.emitir('STOREL', self.vars_locais[var]['offset'])
        elif is_param:
            self.emitir('STOREL', self.params_locais[var]['offset'])
        else:
            self.emitir('STOREG', self.tabela_simbolos[var]['addr'])
        
        self.emitir('JUMP', lbl_ini)
        self.emitir('LABEL', f'{lbl_fim}:')

    def visit_binop(self, node):
        _, op, l, r = node
        self.visit(l)
        self.visit(r)
        
        ops = {
            '+': 'ADD', '-': 'SUB', '*': 'MUL', '/': 'DIV', 
            'div': 'DIV', 'mod': 'MOD',
            'and': 'AND', 'or': 'OR', 
            '=': 'EQUAL', '<': 'INF', '>': 'SUP', 
            '<=': 'INFEQ', '>=': 'SUPEQ'
        }
        
        if op in ops:
            self.emitir(ops[op])
        elif op in ['<>', '!=']:
            self.emitir('EQUAL')
            self.emitir('NOT')
        
        if op in ['=', '<>', '!=', '<', '<=', '>', '>=', 'and', 'or']:
            return 'BOOLEAN'
        return 'INTEGER'

    def visit_unop(self, node):
        _, op, e = node
        self.visit(e)
        if op == 'not':
            self.emitir('NOT')
            return 'BOOLEAN'
        elif op == '-':
            self.emitir('PUSHI', -1)
            self.emitir('MUL')
        return self.inferir_tipo(e)

    def visit_var(self, node):
        nome = node[1]
        
        # Verificar se é um parâmetro local da função atual
        if hasattr(self, 'params_locais') and nome in self.params_locais:
            offset = self.params_locais[nome]['offset']
            self.emitir('PUSHL', offset)
            return self.params_locais[nome].get('tipo', 'INTEGER')
        
        # Verificar se é uma variável local da função atual
        if hasattr(self, 'vars_locais') and nome in self.vars_locais:
            offset = self.vars_locais[nome]['offset']
            self.emitir('PUSHL', offset)
            return self.vars_locais[nome].get('tipo', 'INTEGER')
        
        if nome not in self.tabela_simbolos:
            print(f"ERRO: Variável '{nome}' não declarada")
            return 'INTEGER'
        addr = self.tabela_simbolos[nome]['addr']
        self.emitir('PUSHG', addr)
        return self.tabela_simbolos[nome].get('tipo', 'INTEGER')


# MAIN
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 maquina.py <ficheiro.pas>")
        sys.exit(1)
    
    filename = sys.argv[1]
    ast = parse_file(filename)
    
    if ast:
        # Análise semântica
        analisador = AnalisadorSemantico()
        analisador.visit(ast)
        
        if analisador.erros:
            for erro in analisador.erros:
                print(erro)
            sys.exit(1)
        
        # Geração de código EWVM se passar no semantica
        gerador = GeradorCodigo()
        gerador.visit(ast)
        
        nome_saida = filename.replace('.pas', '.vm')
        if nome_saida == filename: 
            nome_saida += ".vm"
        
        try:
            with open(nome_saida, "w") as f:
                for instr in gerador.codigo:
                    if instr.startswith('LABEL') or instr.endswith(':'):
                        clean_instr = instr.replace('LABEL ', '')
                        f.write(f"{clean_instr}\n")
                    else:
                        f.write(f"\t{instr}\n")
            print(f"Sucesso! {nome_saida}")
        except Exception as e: 
            print(f"Erro ao escrever ficheiro: {e}")
