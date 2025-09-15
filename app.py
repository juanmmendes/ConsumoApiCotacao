# app.py
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

from flask_cors import CORS

# -----------------------------------------------------------------------------
# App & Config
# -----------------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "sua_chave_secreta_aqui")

# CORS apenas para rotas da API
CORS(app, resources={r"/api/*": {"origins": [
    "https://juanmmendes.github.io",  # GitHub Pages
    "http://localhost:3000",          # CRA
    "http://localhost:5173"           # Vite
]}})

# -----------------------------------------------------------------------------
# Camada de Dados
# -----------------------------------------------------------------------------
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
        cursor.execute('SELECT id, email, moeda, tipo, valor_alerta, ativo, criado_em FROM alertas WHERE ativo = 1')
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

# -----------------------------------------------------------------------------
# Serviços de Negócio
# -----------------------------------------------------------------------------
class CotacaoService:
    """Serviço para consumir APIs de cotação"""

    def __init__(self, db_manager):
        self.base_url = "https://economia.awesomeapi.com.br/json"
        self.db_manager = db_manager
        self.cache = {}
        self.cache_time = {}

    def get_moedas_principais(self):
        """Obter cotações das principais moedas com cache (5 min)"""
        if 'principais' in self.cache and time.time() - self.cache_time.get('principais', 0) < 300:
            return self.cache['principais']

        try:
            moedas = ['USD-BRL', 'EUR-BRL', 'GBP-BRL', 'ARS-BRL', 'BTC-BRL']
            cotacoes = {}
            for moeda in moedas:
                resp = requests.get(f"{self.base_url}/last/{moeda}", timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    key = moeda.replace('-', '')
                    if key in data:
                        cotacoes[moeda] = data[key]
                        self.db_manager.salvar_cotacao_historico(moeda, data[key])
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
            resp = requests.get(f"{self.base_url}/last/{par}", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                key = par.replace('-', '')
                if key in data:
                    taxa = float(data[key]['bid'])
                    return {
                        'valor_original': valor,
                        'valor_convertido': round(valor * taxa, 2),
                        'moeda_origem': de_moeda,
                        'moeda_destino': para_moeda,
                        'taxa': taxa,
                        'timestamp': data[key].get('create_date')
                    }
            return None
        except Exception as e:
            print(f"Erro na conversão: {e}")
            return None

    def get_multiplas_moedas(self, moedas_lista):
        """Obter cotações de múltiplas moedas de uma vez"""
        try:
            moedas_str = ','.join(moedas_lista)
            resp = requests.get(f"{self.base_url}/last/{moedas_str}", timeout=15)
            if resp.status_code == 200:
                return resp.json()
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
                disparar = (tipo == 'acima' and valor_atual >= valor_alerta) or \
                           (tipo == 'abaixo' and valor_atual <= valor_alerta)
                if disparar:
                    self.enviar_alerta_email(email, moeda, valor_atual, valor_alerta, tipo)
                    self.db_manager.desativar_alerta(alerta_id)

    def enviar_alerta_email(self, email, moeda, valor_atual, valor_alerta, tipo):
        """Simulação de envio de email de alerta (implemente SMTP real se desejar)"""
        print(f"ALERTA: {moeda} {tipo} {valor_alerta} - Atual: {valor_atual} - Email: {email}")

# -----------------------------------------------------------------------------
# Instâncias de serviço e thread de alertas
# -----------------------------------------------------------------------------
db_manager = DatabaseManager()
cotacao_service = CotacaoService(db_manager)
alerta_service = AlertaService(db_manager, cotacao_service)

def verificar_alertas_worker():
    while True:
        try:
            alerta_service.verificar_alertas()
            time.sleep(300)  # a cada 5 min
        except Exception as e:
            print(f"Erro ao verificar alertas: {e}")
            time.sleep(60)

# Inicia a thread em background (daemon)
alert_thread = threading.Thread(target=verificar_alertas_worker, daemon=True)
alert_thread.start()

# -----------------------------------------------------------------------------
# Rotas
# -----------------------------------------------------------------------------
@app.get("/")
def index():
    """Página principal (HTML) + inicialização de sessão"""
    if 'session_id' not in session:
        session['session_id'] = str(int(time.time()))
    cotacoes = cotacao_service.get_moedas_principais()
    return render_template('index.html', cotacoes=cotacoes)

@app.get("/health")
def health():
    return jsonify({"status": "ok"}), 200

@app.get("/api/cotacoes")
def api_cotacoes():
    """Endpoint API para cotações principais"""
    return jsonify(cotacao_service.get_moedas_principais())

@app.get("/api/converter")
def api_converter():
    """Endpoint API para conversão de moedas"""
    de_moeda = request.args.get('de', 'USD')
    para_moeda = request.args.get('para', 'BRL')
    valor = request.args.get('valor', 1, type=float)
    resultado = cotacao_service.get_conversao(de_moeda, para_moeda, valor)
    if resultado:
        return jsonify(resultado)
    return jsonify({'erro': 'Não foi possível realizar a conversão'}), 400

@app.get("/api/historico/<moeda>")
def api_historico_grafico(moeda):
    """Endpoint para dados do gráfico de histórico"""
    dias = request.args.get('dias', 7, type=int)
    dados = db_manager.get_historico_grafico(moeda, dias)
    return jsonify(dados)

@app.get("/api/multiplas")
def api_multiplas_moedas():
    """Endpoint para cotações de múltiplas moedas customizadas"""
    moedas = request.args.get('moedas', '').split(',')
    if not moedas or moedas == ['']:
        return jsonify({'erro': 'Especifique as moedas'}), 400
    return jsonify(cotacao_service.get_multiplas_moedas(moedas))

@app.post("/api/alerta")
def criar_alerta():
    """Criar alerta de preço"""
    data = request.get_json() or {}
    email = data.get('email')
    moeda = data.get('moeda')
    tipo = data.get('tipo')        # 'acima' ou 'abaixo'
    valor = data.get('valor')
    if not all([email, moeda, tipo, valor]):
        return jsonify({'erro': 'Dados incompletos'}), 400
    try:
        db_manager.criar_alerta(email, moeda, tipo, float(valor))
        return jsonify({'sucesso': 'Alerta criado com sucesso'})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@app.get("/calculadora")
def calculadora_investimentos():
    """Página da calculadora de investimentos"""
    return render_template('calculadora.html')

@app.get("/portfolio")
def portfolio_page():
    """Página do portfólio"""
    return render_template('portfolio.html')

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

# Execução local (em produção o Render usa o Gunicorn)
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
