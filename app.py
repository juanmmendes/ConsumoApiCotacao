from flask import Flask, render_template, jsonify, request
import requests
from datetime import datetime, timedelta
import json

app = Flask(__name__)

class CotacaoService:
    """Serviço para consumir APIs de cotação"""
    
    def __init__(self):
        self.base_url = "https://economia.awesomeapi.com.br/json"
        
    def get_moedas_principais(self):
        """Obter cotações das principais moedas"""
        try:
            # Cotações principais: USD, EUR, GBP, ARS, BTC
            moedas = ['USD-BRL', 'EUR-BRL', 'GBP-BRL', 'ARS-BRL', 'BTC-BRL']
            
            cotacoes = {}
            for moeda in moedas:
                response = requests.get(f"{self.base_url}/last/{moeda}", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    key = moeda.replace('-', '')
                    if key in data:
                        cotacoes[moeda] = data[key]
            
            return cotacoes
            
        except Exception as e:
            print(f"Erro ao buscar cotações: {e}")
            return {}
    
    def get_historico_moeda(self, moeda, dias=30):
        """Obter histórico de uma moeda específica"""
        try:
            response = requests.get(f"{self.base_url}/daily/{moeda}/{dias}", timeout=10)
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print(f"Erro ao buscar histórico: {e}")
            return []
    
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

# Instanciar o serviço
cotacao_service = CotacaoService()

@app.route('/')
def index():
    """Página principal"""
    cotacoes = cotacao_service.get_moedas_principais()
    return render_template('index.html', cotacoes=cotacoes)

@app.route('/api/cotacoes')
def api_cotacoes():
    """Endpoint API para cotações principais"""
    cotacoes = cotacao_service.get_moedas_principais()
    return jsonify(cotacoes)

@app.route('/api/historico/<moeda>')
def api_historico(moeda):
    """Endpoint API para histórico de uma moeda"""
    dias = request.args.get('dias', 30, type=int)
    historico = cotacao_service.get_historico_moeda(moeda, dias)
    return jsonify(historico)

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

@app.route('/historico/<moeda>')
def historico_moeda(moeda):
    """Página de histórico de uma moeda específica"""
    dias = request.args.get('dias', 30, type=int)
    historico = cotacao_service.get_historico_moeda(moeda, dias)
    return render_template('historico.html', moeda=moeda, historico=historico, dias=dias)

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)