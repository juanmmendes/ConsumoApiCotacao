# 💱 Cotações App - Sistema de Cotações em Tempo Real

Uma aplicação Flask moderna para acompanhar cotações de moedas e criptomoedas em tempo real, com conversor integrado e interface responsiva.
## 💵 Cotação Atual do Dólar (USD/BRL)

> 📅 Última atualização: 2025-08-08  
> 💰 1 USD ≈ **R$ 5.4268**

📝 *Cotação em tempo real disponível no app acessando `/api/cotacoes`*








































































## 🚀 Funcionalidades

- **📊 Dashboard em Tempo Real**: Visualize cotações das principais moedas (USD, EUR, GBP, ARS, BTC)
- **💱 Conversor de Moedas**: Converta valores entre diferentes moedas instantaneamente
- **📈 Dados Atualizados**: Informações atualizadas automaticamente a cada 30 segundos
- **📱 Design Responsivo**: Interface adaptável para desktop e mobile
- **🎨 Interface Moderna**: Design com gradientes, animações e efeitos visuais
- **⚡ Performance**: Carregamento rápido e otimizado

## 🛠️ Tecnologias Utilizadas

- **Backend**: Flask (Python)
- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **API**: AwesomeAPI (economia.awesomeapi.com.br)
- **Estilo**: CSS Grid, Flexbox, Animações CSS
- **Ícones**: Font Awesome

## 📋 Pré-requisitos

- Python 3.7+
- pip (gerenciador de pacotes Python)
- Conexão com internet (para consumir APIs)

## 🔧 Instalação e Configuração

### 1. Clone ou baixe o projeto
```bash
# Se você baixou os arquivos, navegue até a pasta
cd cotacoes-app
```

### 2. Crie um ambiente virtual (recomendado)
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Instale as dependências
```bash
pip install -r requirements.txt
```

### 4. Execute a aplicação
```bash
python app.py
```

### 5. Acesse no navegador
Abra seu navegador e vá para: `http://localhost:5000`

## 📱 Como Usar

### Dashboard Principal
- Visualize cotações em tempo real das principais moedas
- Acompanhe variações percentuais (positivas em verde, negativas em vermelho)
- Veja valores de compra, venda, máxima e mínima do dia

### Conversor de Moedas
1. Inserir o valor que deseja converter
2. Selecionar a moeda de origem
3. Selecionar a moeda de destino
4. Clicar em "Converter" ou pressionar Enter
5. Ver o resultado detalhado com taxa de câmbio atual

## 🌐 API Endpoints

A aplicação oferece endpoints para integração:

### GET `/api/cotacoes`
Retorna cotações das principais moedas em formato JSON.

**Exemplo de resposta:**
```json
{
  "USD-BRL": {
    "bid": "5.1234",
    "ask": "5.1289",
    "high": "5.2000",
    "low": "5.1000",
    "pctChange": "0.85"
  }
}
```

### GET `/api/converter`
Converte valores entre moedas.

**Parâmetros:**
- `de`: Moeda de origem (ex: USD)
- `para`: Moeda de destino (ex: BRL)
- `valor`: Valor a converter (ex: 100)

**Exemplo:**
```
GET /api/converter?de=USD&para=BRL&valor=100
```

### GET `/api/historico/<moeda>`
Retorna histórico de uma moeda específica.

**Parâmetros:**
- `dias`: Número de dias do histórico (padrão: 30)

## 💡 Impacto Real para o Usuário

### Para Investidores
- Acompanhe variações do mercado em tempo real
- Tome decisões informadas sobre investimentos
- Compare performance entre diferentes moedas

### Para Viajantes
- Converta moedas antes de viagens internacionais
- Acompanhe flutuações cambiais
- Planeje gastos em moeda estrangeira

### Para Empresários
- Monitore câmbio para importação/exportação
- Calcule custos em diferentes moedas
- Acompanhe tendências do mercado

### Para Estudantes
- Aprenda sobre mercado financeiro
- Entenda variações cambiais
- Pratique conversões matemáticas

## 🔄 Atualizações Automáticas

- **Frontend**: Atualização automática a cada 30 segundos
- **Dados**: Consumo em tempo real da AwesomeAPI
- **Cache**: Sistema otimizado para performance

## 🛡️ Tratamento de Erros

- Mensagens amigáveis para usuários
- Fallbacks para problemas de conectividade
- Validação de dados de entrada
- Logs detalhados para debugging

## 📊 Moedas Suportadas

- **USD** - Dólar Americano 🇺🇸
- **EUR** - Euro 🇪🇺
- **GBP** - Libra Esterlina 🇬🇧
- **ARS** - Peso Argentino 🇦🇷
- **BTC** - Bitcoin ₿

## 🚀 Melhorias Futuras

- [ ] Histórico gráfico de cotações
- [ ] Alertas de preço por email/SMS
- [ ] Mais moedas e criptomoedas
- [ ] Dashboard personalizado
- [ ] Exportar dados para Excel/PDF
- [ ] Modo escuro/claro
- [ ] PWA (Progressive Web App)

## 🤝 Contribuições

Contribuições são bem-vindas! Sinta-se à vontade para:

1. Fazer fork do projeto
2. Criar uma branch para sua feature
3. Fazer commit das mudanças
4. Abrir um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo LICENSE para mais detalhes.

## 📞 Suporte

Para dúvidas ou sugestões:
- Abra uma issue no GitHub
- Entre em contato através do email do projeto

---

### 🎯 Feito com ❤️ para facilitar o acompanhamento do mercado financeiro!