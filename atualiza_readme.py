import requests
import re

url = 'https://economia.awesomeapi.com.br/json/last/USD-BRL'
response = requests.get(url)
data = response.json()

cotacao = data['USDBRL']['bid']
data_atual = data['USDBRL']['create_date'].split()[0]

with open('README.md', 'r', encoding='utf-8') as f:
    conteudo = f.read()

novo_bloco = f"""\
## 💵 Cotação Atual do Dólar (USD/BRL)

> 📅 Última atualização: {data_atual}  
> 💰 1 USD ≈ **R$ {cotacao}**

📝 *Cotação em tempo real disponível no app acessando `/api/cotacoes`*
"""

conteudo_atualizado = re.sub(
    r'## 💵 Cotação Atual do Dólar \(USD/BRL\)[\s\S]*?📝 \*Cotação.*?\n',
    novo_bloco + '\n',
    conteudo
)

with open('README.md', 'w', encoding='utf-8') as f:
    f.write(conteudo_atualizado)
