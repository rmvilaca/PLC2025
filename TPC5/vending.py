import json
from datetime import datetime
from collections import Counter

FICHEIRO_STOCK = "stock.json"

# Moedas disponíveis em cêntimos
MOEDAS_VALIDAS = [200, 100, 50, 20, 10, 5, 2, 1]

def carregar_stock():
    """Carrega o stock do ficheiro JSON"""
    try:
        with open(FICHEIRO_STOCK, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # Stock inicial se o ficheiro não existir
        return [
            {"cod": "A23", "nome": "água 0.5L", "quant": 8, "preco": 0.7},
            {"cod": "B12", "nome": "coca-cola 0.33L", "quant": 5, "preco": 1.2},
            {"cod": "C45", "nome": "snickers", "quant": 10, "preco": 0.9},
            {"cod": "D78", "nome": "kit-kat", "quant": 7, "preco": 0.85},
            {"cod": "E56", "nome": "sumo laranja", "quant": 6, "preco": 1.0},
        ]

def guardar_stock(stock):
    """Guarda o stock no ficheiro JSON"""
    with open(FICHEIRO_STOCK, 'w', encoding='utf-8') as f:
        json.dump(stock, f, indent=2, ensure_ascii=False)

def converter_moeda(texto):
    """Converte texto de moeda para cêntimos (ex: '1e' -> 100, '20c' -> 20)"""
    texto = texto.strip().lower()
    if texto.endswith('e'):
        return int(float(texto[:-1]) * 100)
    elif texto.endswith('c'):
        return int(texto[:-1])
    return 0

def formatar_preco(centimos):
    """Formata cêntimos para string legível"""
    euros = centimos // 100
    cents = centimos % 100
    if euros > 0 and cents > 0:
        return f"{euros}e{cents:02d}c"
    elif euros > 0:
        return f"{euros}e"
    else:
        return f"{cents}c"

def calcular_troco(centimos):
    """Calcula o troco em moedas"""
    troco = {}
    restante = centimos
    
    for moeda in MOEDAS_VALIDAS:
        if restante >= moeda:
            quantidade = restante // moeda
            troco[moeda] = quantidade
            restante -= quantidade * moeda
    
    return troco

def formatar_troco(troco_dict):
    """Formata o dicionário de troco para string legível"""
    partes = []
    for moeda, quant in troco_dict.items():
        if moeda >= 100:
            valor = f"{moeda//100}e"
        else:
            valor = f"{moeda}c"
        partes.append(f"{quant}x {valor}")
    
    return ", ".join(partes)

def listar_produtos(stock):
    """Lista todos os produtos disponíveis"""
    print("\nmaq:")
    print(f"{'cod':<6}| {'nome':<20} | {'quantidade':<10} | {'preço':<10}")
    print("-" * 55)
    for produto in stock:
        preco_str = f"{produto['preco']:.2f}€"
        print(f"{produto['cod']:<6}| {produto['nome']:<20} | {produto['quant']:<10} | {preco_str:<10}")
    print()

def encontrar_produto(stock, codigo):
    """Encontra um produto pelo código"""
    for produto in stock:
        if produto['cod'].upper() == codigo.upper():
            return produto
    return None

def adicionar_produto(stock):
    """Adiciona ou atualiza produtos no stock"""
    print("\nmaq: === Adicionar Produto ao Stock ===")
    codigo = input(">> Código do produto: ").strip().upper()
    
    produto_existente = encontrar_produto(stock, codigo)
    
    if produto_existente:
        print(f"maq: Produto '{produto_existente['nome']}' já existe.")
        quantidade = input(">> Quantidade a adicionar: ").strip()
        try:
            quant = int(quantidade)
            produto_existente['quant'] += quant
            print(f"maq: Adicionadas {quant} unidades. Stock atual: {produto_existente['quant']}")
        except ValueError:
            print("maq: Quantidade inválida.")
    else:
        nome = input(">> Nome do produto: ").strip()
        quantidade = input(">> Quantidade: ").strip()
        preco = input(">> Preço (em euros): ").strip()
        
        try:
            novo_produto = {
                "cod": codigo,
                "nome": nome,
                "quant": int(quantidade),
                "preco": float(preco)
            }
            stock.append(novo_produto)
            print(f"maq: Produto '{nome}' adicionado com sucesso!")
        except ValueError:
            print("maq: Dados inválidos. Produto não adicionado.")

def main():
    # Carregar stock
    stock = carregar_stock()
    data_atual = datetime.now().strftime("%Y-%m-%d")
    print(f"maq: {data_atual}, Stock carregado, Estado atualizado.")
    
    # Determinar saudação
    hora = datetime.now().hour
    if hora < 12:
        saudacao = "Bom dia"
    elif hora < 20:
        saudacao = "Boa tarde"
    else:
        saudacao = "Boa noite"
    
    print(f"maq: {saudacao}. Estou disponível para atender o seu pedido.")
    
    saldo = 0  # saldo em cêntimos
    
    while True:
        comando = input(">> ").strip()
        
        if not comando:
            continue
            
        partes = comando.split(None, 1)
        cmd = partes[0].upper()
        
        if cmd == "LISTAR":
            listar_produtos(stock)
            
        elif cmd == "MOEDA":
            if len(partes) < 2:
                print("maq: Por favor indique as moedas (ex: MOEDA 1e, 20c, 5c)")
                continue
                
            moedas_texto = partes[1].replace('.', '').split(',')
            for moeda_txt in moedas_texto:
                moeda_txt = moeda_txt.strip()
                if moeda_txt:
                    valor = converter_moeda(moeda_txt)
                    saldo += valor
            
            print(f"maq: Saldo = {formatar_preco(saldo)}")
            
        elif cmd == "SELECIONAR":
            if len(partes) < 2:
                print("maq: Por favor indique o código do produto.")
                continue
                
            codigo = partes[1].strip()
            produto = encontrar_produto(stock, codigo)
            
            if not produto:
                print(f"maq: Produto '{codigo}' não encontrado.")
                continue
                
            if produto['quant'] <= 0:
                print(f"maq: Produto '{produto['nome']}' esgotado.")
                continue
                
            preco_centimos = int(produto['preco'] * 100)
            
            if saldo < preco_centimos:
                print("maq: Saldo insuficiente para satisfazer o seu pedido")
                print(f"maq: Saldo = {formatar_preco(saldo)}; Pedido = {formatar_preco(preco_centimos)}")
            else:
                produto['quant'] -= 1
                saldo -= preco_centimos
                print(f'maq: Pode retirar o produto dispensado "{produto["nome"]}"')
                print(f"maq: Saldo = {formatar_preco(saldo)}")
                
        elif cmd == "SAIR":
            if saldo > 0:
                troco = calcular_troco(saldo)
                print(f"maq: Pode retirar o troco: {formatar_troco(troco)}.")
            print("maq: Até à próxima")
            break
            
        elif cmd == "ADICIONAR":
            adicionar_produto(stock)
            
        elif cmd == "AJUDA":
            print("\nmaq: Comandos disponíveis:")
            print("  LISTAR - mostra todos os produtos")
            print("  MOEDA <moedas> - insere moedas (ex: MOEDA 1e, 50c, 20c)")
            print("  SELECIONAR <código> - seleciona um produto")
            print("  ADICIONAR - adiciona produtos ao stock")
            print("  SAIR - termina e devolve o troco")
            print("  AJUDA - mostra esta mensagem\n")
            
        else:
            print(f"maq: Comando '{cmd}' não reconhecido. Digite AJUDA para ver os comandos disponíveis.")
    
    # Guardar stock ao terminar
    guardar_stock(stock)
    print("maq: Stock atualizado e guardado.")

if __name__ == "__main__":
    main()