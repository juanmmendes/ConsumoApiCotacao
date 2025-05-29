from flask import Flask, render_template, jsonify, request, session
import requests
from datetime import datetime, timedelta
import json
import sqlite3
import threading
import time
from collections import defaultdict
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'

class DatabaseManager:
    """Gerenciador do banco de dados SQLite"""
    
    def __init__(self, db_path='cotacoes.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Inicializar tabelas do banco"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tabela de histórico de cotações
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS historico_cotacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                moeda VARCHAR(10) NOT NULL,
                valor REAL NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                bid REAL,
                ask REAL,
                high REAL,
                low REAL,
                pct_change REAL
            )
        ''')
        
        # Tabela de alertas de preço
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alertas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email VARCHAR(255) NOT NULL,
                moeda VARCHAR(10) NOT NULL,
                tipo VARCHAR(10) NOT NULL,  -- 'acima' ou 'abaixo'
                valor_alerta REAL NOT NULL,
                ativo BOOLEAN DEFAULT 1,
                criado_em DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de portfólio do usuário
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS portfolio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id VARCHAR(255) NOT NULL,
                moeda VARCHAR(10) NOT NULL,
                quantidade REAL NOT NULL,
                preco_compra REAL NOT NULL,
                data_compra DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def salvar_cotacao_historico(self, moeda, dados):
        """Salvar cotação no histórico"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO historico_cotacoes 
            (moeda, valor, bid, ask, high, low, pct_change)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            moeda, 
            float(dados.get('bid', 0)),
            float(dados.get('bid', 0)),
            float(dados.get('ask', 0)),
            float(dados.get('high', 0)),
            float(dados.get('low', 0)),
            float(dados.get('pctChange', 0))
        ))
        
        conn.commit()
        conn.close()
    
    def get_historico_grafico(self, moeda, dias=7):
        """Obter dados para gráfico de histórico"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT DATE(timestamp) as data, 
                   AVG(valor) as media,
                   MAX(high) as maxima,
                   MIN(low) as minima
            FROM historico_cotacoes 
            WHERE moeda = ? AND timestamp >= datetime('now', '-{} days')
            GROUP BY DATE(timestamp)
            ORDER BY data
        '''.format(dias), (moeda,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [{'data': row[0], 'media': row[1], 'maxima': row[2], 'minima': row[3]} 
                for row in results]
    
    def criar_alerta(self, email, moeda, tipo, valor):
        """Criar alerta de preço"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO alertas (email, moeda, tipo, valor_alerta)
            VALUES (?, ?, ?, ?)
        ''', (email, moeda, tipo, valor))
        
        conn.commit()
        conn.close()
    
    def get_alertas_ativos(self):
        """Obter todos os alertas ativos"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM alertas WHERE ativo = 1')
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    def desativar_alerta(self, alerta_id):
        """Desativar um alerta após ser disparado"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('UPDATE alertas SET ativo = 0 WHERE id = ?', (alerta_id,))
        conn.commit()
        conn.close()

class CotacaoService:
    """Serviço para consumir APIs de cotação"""
    
    def __init__(self, db_manager):
        self.base_url = "https://economia.awesomeapi.com.br/json"
        self.db_manager = db_manager
        self.cache = {}
        self.cache_time = {}
        
    def get_moedas_principais(self):
        """Obter cotações das principais moedas com cache"""
        # Verificar cache (5 minutos)
        if 'principais' in self.cache:
            if time.time() - self.cache_time.get('principais', 0) < 300:
                return self.cache['principais']
        
        try:
            moedas = ['USD-BRL', 'EUR-BRL', 'GBP-BRL', 'ARS-BRL', 'BTC-BRL']
            cotacoes = {}
            
            for moeda in moedas:
                response = requests.get(f"{self.base_url}/last/{moeda}", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    key = moeda.replace('-', '')
                    if key in data:
                        cotacoes[moeda] = data[key]
                        # Salvar no histórico
                        self.db_manager.salvar_cotacao_historico(moeda, data[key])
            
            # Atualizar cache
            self.cache['principais'] = cotacoes
            self.cache_time['principais'] = time.time()
            
            return cotacoes
            
        except Exception as e:
            print(f"Erro ao buscar cotações: {e}")
            return self.cache.get('principais', {})
    
    def get_conversao(self, de_moeda, para_moeda, valor):
        """Converter valor entre moedas"""
        try:
            par = f"{de_moeda}-{para_moeda}"
            response = requests.get(f"{self.base_url}/last/{par}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                key = par.replace('-', '')
                if key in data:
                    taxa = float(data[key]['bid'])
                    return {
                        'valor_original': valor,
                        'valor_convertido': round(valor * taxa, 2),
                        'moeda_origem': de_moeda,
                        'moeda_destino': para_moeda,
                        'taxa': taxa,
                        'timestamp': data[key]['create_date']
                    }
            return None
        except Exception as e:
            print(f"Erro na conversão: {e}")
            return None
    
    def get_multiplas_moedas(self, moedas_lista):
        """Obter cotações de múltiplas moedas de uma vez"""
        try:
            moedas_str = ','.join(moedas_lista)
            response = requests.get(f"{self.base_url}/last/{moedas_str}", timeout=15)
            
            if response.status_code == 200:
                return response.json()
            return {}
        except Exception as e:
            print(f"Erro ao buscar múltiplas moedas: {e}")
            return {}

class AlertaService:
    """Serviço para gerenciar alertas de preço"""
    
    def __init__(self, db_manager, cotacao_service):
        self.db_manager = db_manager
        self.cotacao_service = cotacao_service
        
    def verificar_alertas(self):
        """Verificar e disparar alertas"""
        alertas = self.db_manager.get_alertas_ativos()
        cotacoes = self.cotacao_service.get_moedas_principais()
        
        for alerta in alertas:
            alerta_id, email, moeda, tipo, valor_alerta, ativo, criado_em = alerta
            
            if moeda in cotacoes:
                valor_atual = float(cotacoes[moeda]['bid'])
                
                disparar = False
                if tipo == 'acima' and valor_atual >= valor_alerta:
                    disparar = True
                elif tipo == 'abaixo' and valor_atual <= valor_alerta:
                    disparar = True
                
                if disparar:
                    self.enviar_alerta_email(email, moeda, valor_atual, valor_alerta, tipo)
                    self.db_manager.desativar_alerta(alerta_id)
    
    def enviar_alerta_email(self, email, moeda, valor_atual, valor_alerta, tipo):
        """Enviar email de alerta (simulado - você precisa configurar SMTP real)"""
        print(f"ALERTA: {moeda} {tipo} {valor_alerta} - Valor atual: {valor_atual} - Email: {email}")
        # Aqui você implementaria o envio real de email

# Instanciar serviços
db_manager = DatabaseManager()
cotacao_service = CotacaoService(db_manager)
alerta_service = AlertaService(db_manager, cotacao_service)

# Thread para verificar alertas periodicamente
def verificar_alertas_worker():
    while True:
        try:
            alerta_service.verificar_alertas()
            time.sleep(300)  # Verificar a cada 5 minutos
        except Exception as e:
            print(f"Erro ao verificar alertas: {e}")
            time.sleep(60)

# Iniciar thread em background
alert_thread = threading.Thread(target=verificar_alertas_worker, daemon=True)
alert_thread.start()

@app.route('/')
def index():
    """Página principal"""
    if 'session_id' not in session:
        session['session_id'] = str(int(time.time()))
    
    cotacoes = cotacao_service.get_moedas_principais()
    return render_template('index.html', cotacoes=cotacoes)

@app.route('/api/cotacoes')
def api_cotacoes():
    """Endpoint API para cotações principais"""
    cotacoes = cotacao_service.get_moedas_principais()
    return jsonify(cotacoes)

@app.route('/api/converter')
def api_converter():
    """Endpoint API para conversão de moedas"""
    de_moeda = request.args.get('de', 'USD')
    para_moeda = request.args.get('para', 'BRL')
    valor = request.args.get('valor', 1, type=float)
    
    resultado = cotacao_service.get_conversao(de_moeda, para_moeda, valor)
    if resultado:
        return jsonify(resultado)
    else:
        return jsonify({'erro': 'Não foi possível realizar a conversão'}), 400

@app.route('/api/historico/<moeda>')
def api_historico_grafico(moeda):
    """Endpoint para dados do gráfico de histórico"""
    dias = request.args.get('dias', 7, type=int)
    dados = db_manager.get_historico_grafico(moeda, dias)
    return jsonify(dados)

@app.route('/api/multiplas')
def api_multiplas_moedas():
    """Endpoint para cotações de múltiplas moedas customizadas"""
    moedas = request.args.get('moedas', '').split(',')
    if not moedas or moedas == ['']:
        return jsonify({'erro': 'Especifique as moedas'}), 400
    
    cotacoes = cotacao_service.get_multiplas_moedas(moedas)
    return jsonify(cotacoes)

@app.route('/api/alerta', methods=['POST'])
def criar_alerta():
    """Criar alerta de preço"""
    data = request.get_json()
    
    email = data.get('email')
    moeda = data.get('moeda')
    tipo = data.get('tipo')  # 'acima' ou 'abaixo'
    valor = data.get('valor')
    
    if not all([email, moeda, tipo, valor]):
        return jsonify({'erro': 'Dados incompletos'}), 400
    
    try:
        db_manager.criar_alerta(email, moeda, tipo, float(valor))
        return jsonify({'sucesso': 'Alerta criado com sucesso'})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/api/portfolio', methods=['GET', 'POST'])
def portfolio():
    """Gerenciar portfólio do usuário"""
    if 'session_id' not in session:
        session['session_id'] = str(int(time.time()))
    
    if request.method == 'POST':
        # Adicionar investimento ao portfólio
        data = request.get_json()
        moeda = data.get('moeda')
        quantidade = data.get('quantidade')
        preco_compra = data.get('preco_compra')
        
        if not all([moeda, quantidade, preco_compra]):
            return jsonify({'erro': 'Dados incompletos'}), 400
        
        conn = sqlite3.connect(db_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO portfolio (session_id, moeda, quantidade, preco_compra)
            VALUES (?, ?, ?, ?)
        ''', (session['session_id'], moeda, float(quantidade), float(preco_compra)))
        
        conn.commit()
        conn.close()
        
        return jsonify({'sucesso': 'Investimento adicionado'})
    
    else:
        # Obter portfólio atual
        conn = sqlite3.connect(db_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT moeda, quantidade, preco_compra, data_compra
            FROM portfolio 
            WHERE session_id = ?
            ORDER BY data_compra DESC
        ''', (session['session_id'],))
        
        portfolio_data = cursor.fetchall()
        conn.close()
        
        # Calcular lucro/prejuízo
        cotacoes_atuais = cotacao_service.get_moedas_principais()
        portfolio_com_calc = []
        
        for item in portfolio_data:
            moeda, quantidade, preco_compra, data_compra = item
            moeda_par = f"{moeda}-BRL"
            
            if moeda_par in cotacoes_atuais:
                preco_atual = float(cotacoes_atuais[moeda_par]['bid'])
                valor_investido = quantidade * preco_compra
                valor_atual = quantidade * preco_atual
                lucro_prejuizo = valor_atual - valor_investido
                percentual = ((valor_atual - valor_investido) / valor_investido) * 100
                
                portfolio_com_calc.append({
                    'moeda': moeda,
                    'quantidade': quantidade,
                    'preco_compra': preco_compra,
                    'preco_atual': preco_atual,
                    'valor_investido': valor_investido,
                    'valor_atual': valor_atual,
                    'lucro_prejuizo': lucro_prejuizo,
                    'percentual': percentual,
                    'data_compra': data_compra
                })
        
        return jsonify(portfolio_com_calc)

@app.route('/calculadora')
def calculadora_investimentos():
    """Página da calculadora de investimentos"""
    return render_template('calculadora.html')

@app.route('/portfolio')
def portfolio_page():
    """Página do portfólio"""
    return render_template('portfolio.html')

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)