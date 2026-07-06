"""
Bot de Sinais para Telegram - Luxury Mines Signals

Este módulo implementa um bot de Telegram automatizado que envia sinais
para o jogo Mines com tabuleiros interativos, rankings e cronômetros.

Dependências:
    - telebot (python-telebot)
    - python-dotenv
"""

import telebot
import random
import time
import threading
import logging
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from urllib.parse import urlparse
from dotenv import load_dotenv
from telebot import types

# ============================================================================
# CONFIGURAÇÃO DE LOGGING
# ============================================================================

def configurar_logging() -> None:
    """Configura o sistema de logging para o bot."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('bot.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )


logger = logging.getLogger(__name__)
configurar_logging()

# ============================================================================
# CARREGAMENTO DE VARIÁVEIS DE AMBIENTE
# ============================================================================

logger.info("Iniciando carregamento de configurações...")
load_dotenv()
logger.info("Arquivo .env carregado com sucesso")

# ============================================================================
# CONSTANTES - CONFIGURAÇÃO
# ============================================================================

# Configurações obrigatórias do bot
CONFIG_OBRIGATORIA = {
    'API_TOKEN': None,
    'CHAT_ID': None,
}

# Configurações opcionais com valores padrão
CONFIG_OPCIONAL = {
    'CAMINHO_IMAGEM': 'caminho_da_imagem.png',
    'PLATAFORMA_1_URL': 'https://bingo.bet.br/',
    'PLATAFORMA_2_URL': 'https://bingo.bet.br/',
    'DELAY_SINAL_EM_BREVE': 1,
    'DELAY_SINAL_CAPTURADO': 10,
    'DELAY_ENVIO_TABULEIRO': 120,
    'DELAY_ENVIO_GREEN': 10,
    'DELAY_ENVIO_RANKING': 10,
    'MIN_BOMBAS': 2,
    'MAX_BOMBAS': 4,  # Variação: 2-4 minas (ótimo para previsões)
    'MIN_BOMBAS_ALEATORIO': 2,  # Valor mínimo absoluto para minas aleatórias
    'MAX_BOMBAS_ALEATORIO': 4,  # Valor máximo absoluto para minas aleatórias
    'MIN_ESTRELAS': 2,
    'MAX_ESTRELAS': 4,
    'MIN_VALOR': 1,
    'MAX_VALOR': 100,
    'MIN_PORCENTAGEM': 65,
    'MAX_PORCENTAGEM': 90,
}

# ============================================================================
# CONSTANTES - TIMING
# ============================================================================

# Tempo total do cronômetro em segundos
TEMPO_CRONOMETRO_TOTAL: int = 120

# Intervalo de atualização do cronômetro em segundos
INTERVALO_ATUALIZACAO_CRONOMETRO: int = 15

# Tempo de espera ao lidar com erros em segundos
TEMPO_ESPERA_ERRO: int = 10

# ============================================================================
# CONSTANTES - STRINGS E EMOJIS
# ============================================================================

# Emojis
EMOJI_SINAL_BREVE = "🔵"
EMOJI_SINAL_CAPTURADO = "📡"
EMOJI_CHECKBOX = "✅"
EMOJI_ERROR = "❌"
EMOJI_AVISO = "⚠️"
EMOJI_BLOQUEADO = "🔒"
EMOJI_ABERTO = "🟦"
EMOJI_ESTRELA = "⭐"
EMOJI_TROFEU = "🏆"
EMOJI_VERDE = "🟢"
EMOJI_RAIO = "⚡"
EMOJI_BOMBA = "💣"
EMOJI_RELOGIO = "⏰"
EMOJI_GLOBO = "🌐"
EMOJI_CONFETE = "🎉"
EMOJI_DINHEIRO = "💰"
EMOJI_TRIAGULO_PARA_CIMA = "🔺"
EMOJI_TRIANGULO_INVERTIDO = "🔹"

# Marcadores especiais
MARCADOR_PREPARACAO = "`SINAL EM PREPARAÇÃO!`"
MARCADOR_CAPTURADO = "`SINAL CAPTURADO!`"
MARCADOR_GREEN = "🟢 *GREEN DETECTADO!* 🟢"
MARCADOR_TEMPO_ESGOTADO = "⏳ *TEMPO ESGOTADO - ESPERE O PRÓXIMO SINAL!*"

# Textos de aviso
TEXTO_ESPERANDO_SINAL = "Aguarde... Um novo sinal está sendo capturado."
TEXTO_CONFIRA_TABULEIRO = "Confira! O tabuleiro será gerado abaixo."
TEXTO_PARABENIZACAO = "Parabéns! A aposta foi um sucesso."
TEXTO_LUCRO_EXCLUSIVO = "Continue acompanhando nossos sinais exclusivos e maximize seus lucros!"
TEXTO_PLATAFORMAS_AUTORIZADAS = "*LUCRE SOMENTE NAS PLATAFORMAS AUTORIZADAS!*"
TEXTO_RANKING = "*RANKING DE VITÓRIAS!*"
TEXTO_APOSTADORES = "dos apostadores tiveram sucesso!"

# ============================================================================
# CONSTANTES - NOMES DE PESSOAS (para ranking)
# ============================================================================

PREFIXOS_NOMES = [
    "Ana", "João", "Lucas", "Beatriz", "Maria", 
    "Pedro", "Isabela", "Rafael", "Carla", "Victor"
]

SUFIXOS_NOMES = [
    "Silva", "Souza", "Oliveira", "Pereira", "Costa",
    "Alves", "Gomes", "Martins", "Barros", "Ferreira"
]

# ============================================================================
# CONSTANTES - TAMANHO DO TABULEIRO
# ============================================================================

TAMANHO_TABULEIRO: int = 5

# ============================================================================
# EXTENSÕES DE ARQUIVO ACEITAS PARA IMAGENS
# ============================================================================

EXTENSOES_IMAGEM_VALIDAS: Tuple[str, ...] = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')

# ============================================================================
# VARIÁVEIS GLOBAIS DE CONFIGURAÇÃO
# ============================================================================

config: Dict[str, any] = {}
bot: Optional[telebot.TeleBot] = None

# ============================================================================
# FUNÇÕES DE VALIDAÇÃO E CONFIGURAÇÃO
# ============================================================================

def validar_url(url: str) -> bool:
    """
    Valida se uma string é uma URL válida.
    
    Args:
        url: String a ser validada como URL.
        
    Returns:
        True se a URL é válida, False caso contrário.
    """
    try:
        resultado = urlparse(url)
        return all([resultado.scheme in ('http', 'https'), resultado.netloc])
    except Exception as e:
        logger.warning(f"Erro ao validar URL '{url}': {e}")
        return False


def validar_imagem(caminho: str) -> Tuple[bool, str]:
    """
    Valida se o arquivo de imagem existe e possui extensão válida.
    
    Args:
        caminho: Caminho do arquivo de imagem.
        
    Returns:
        Tupla (válido: bool, mensagem: str).
    """
    try:
        arquivo = Path(caminho)
        
        # Verificar se o arquivo existe
        if not arquivo.exists():
            msg = f"Arquivo de imagem não encontrado: {caminho}"
            logger.error(msg)
            return False, msg
        
        # Verificar se é um arquivo
        if not arquivo.is_file():
            msg = f"Caminho não é um arquivo: {caminho}"
            logger.error(msg)
            return False, msg
        
        # Verificar se tem tamanho válido (não vazio)
        if arquivo.stat().st_size == 0:
            msg = f"Arquivo de imagem está vazio: {caminho}"
            logger.error(msg)
            return False, msg
        
        # Verificar extensão
        if arquivo.suffix.lower() not in EXTENSOES_IMAGEM_VALIDAS:
            msg = f"Extensão de arquivo inválida: {arquivo.suffix}. Válidas: {EXTENSOES_IMAGEM_VALIDAS}"
            logger.error(msg)
            return False, msg
        
        logger.info(f"Imagem validada com sucesso: {caminho}")
        return True, "OK"
        
    except Exception as e:
        msg = f"Erro ao validar imagem: {e}"
        logger.error(msg, exc_info=True)
        return False, msg


def validar_token(token: str) -> bool:
    """
    Validação básica de formato de token do Telegram.
    
    Args:
        token: Token da API do Telegram.
        
    Returns:
        True se o token tem formato válido, False caso contrário.
    """
    # Token do Telegram tem formato: 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
    if not token or ':' not in token:
        logger.error("Token inválido: formato incorreto")
        return False
    
    partes = token.split(':')
    if len(partes) != 2 or not partes[0].isdigit():
        logger.error("Token inválido: não segue o padrão de token do Telegram")
        return False
    
    logger.info("Token validado com sucesso")
    return True


def validar_chat_id(chat_id: str) -> bool:
    """
    Valida se o chat_id é um número válido.
    
    Args:
        chat_id: ID do chat do Telegram.
        
    Returns:
        True se é um número válido, False caso contrário.
    """
    try:
        int(chat_id)
        logger.info(f"Chat ID validado: {chat_id}")
        return True
    except (ValueError, TypeError):
        logger.error(f"Chat ID inválido: {chat_id}")
        return False


def carregar_configuracoes() -> Dict[str, any]:
    """
    Carrega e valida todas as configurações do arquivo .env.
    
    Returns:
        Dicionário com configurações validadas.
        
    Raises:
        SystemExit: Se houver configurações obrigatórias faltando.
    """
    global config
    
    logger.info("Iniciando validação de configurações...")
    config = {}
    erros = []
    
    # Validar configurações obrigatórias
    for chave in CONFIG_OBRIGATORIA:
        valor = os.getenv(chave)
        if not valor:
            msg = f"{EMOJI_ERROR} Configuração obrigatória faltando: {chave}"
            logger.error(msg)
            erros.append(msg)
        else:
            config[chave] = valor
    
    # Se houver erros em configurações obrigatórias, parar
    if erros:
        logger.critical("Configurações obrigatórias faltando:")
        for erro in erros:
            logger.critical(erro)
        print("\n" + "\n".join(erros))
        print(f"\n{EMOJI_AVISO} Configure as variáveis faltando no arquivo .env")
        raise SystemExit(1)
    
    # Validações específicas
    if not validar_token(config['API_TOKEN']):
        logger.critical("Token do Telegram inválido")
        raise SystemExit(1)
    
    if not validar_chat_id(config['CHAT_ID']):
        logger.critical("Chat ID inválido")
        raise SystemExit(1)
    
    # Carregar configurações opcionais
    for chave, valor_padrao in CONFIG_OPCIONAL.items():
        try:
            valor_env = os.getenv(chave)
            if valor_env is None:
                config[chave] = valor_padrao
                logger.info(f"Usando valor padrão para {chave}: {valor_padrao}")
            else:
                # Tentar converter para tipo apropriado
                if isinstance(valor_padrao, int):
                    config[chave] = int(valor_env)
                else:
                    config[chave] = valor_env
                logger.info(f"Configuração {chave} carregada: {config[chave]}")
        except (ValueError, TypeError) as e:
            logger.warning(f"Erro ao carregar {chave}, usando valor padrão: {e}")
            config[chave] = valor_padrao
    
    # Validar URLs
    for plataforma in ['PLATAFORMA_1_URL', 'PLATAFORMA_2_URL']:
        if not validar_url(config[plataforma]):
            msg = f"URL inválida para {plataforma}: {config[plataforma]}"
            logger.warning(msg)
    
    # Validar arquivo de imagem
    valido, msg = validar_imagem(config['CAMINHO_IMAGEM'])
    if not valido:
        logger.warning(f"Arquivo de imagem inválido: {msg}")
    
    logger.info(f"{EMOJI_CHECKBOX} Todas as configurações validadas com sucesso")
    return config


# ============================================================================
# FUNÇÕES UTILITÁRIAS
# ============================================================================

def gerar_nome() -> str:
    """
    Gera um nome aleatório para o ranking.
    
    Returns:
        Nome aleatório (prefixo + sobrenome).
    """
    prefixo = random.choice(PREFIXOS_NOMES)
    sufixo = random.choice(SUFIXOS_NOMES)
    return f"{prefixo} {sufixo}"


def gerar_valor() -> int:
    """
    Gera um valor aleatório para o ranking.
    
    Returns:
        Valor inteiro entre MIN_VALOR e MAX_VALOR.
    """
    return random.randint(config['MIN_VALOR'], config['MAX_VALOR'])


def gerar_porcentagem() -> int:
    """
    Gera uma porcentagem aleatória de sucesso.
    
    Returns:
        Porcentagem inteira entre MIN_PORCENTAGEM e MAX_PORCENTAGEM.
    """
    return random.randint(config['MIN_PORCENTAGEM'], config['MAX_PORCENTAGEM'])


def gerar_ranking() -> str:
    """
    Gera um ranking formatado com 7 entradas aleatórias.
    
    Returns:
        String formatada com o ranking.
    """
    ranking = [(gerar_nome(), gerar_valor()) for _ in range(7)]
    ranking_ordenado = sorted(ranking, key=lambda x: x[1], reverse=True)
    return "\n".join(
        [f"*{i+1}º:* {nome} - `R$ {valor}`" 
         for i, (nome, valor) in enumerate(ranking_ordenado)]
    )


# ============================================================================
# FUNÇÕES DE GERAÇÃO DE TABULEIRO
# ============================================================================

def criar_tabuleiro(
    tamanho: int = TAMANHO_TABULEIRO,
    num_casas_sorteadas: Optional[int] = None
) -> Tuple[List[List[str]], int]:
    """
    Cria um tabuleiro do jogo Mines com casas aleatoriamente marcadas com estrelas.
    
    Args:
        tamanho: Tamanho do tabuleiro (padrão: 5x5).
        num_casas_sorteadas: Número de casas a marcar com estrelas. 
                            Se None, usa valor aleatório.
    
    Returns:
        Tupla com (tabuleiro: List[List[str]], num_casas_sorteadas: int).
    """
    if num_casas_sorteadas is None:
        num_casas_sorteadas = random.randint(
            config['MIN_ESTRELAS'],
            config['MAX_ESTRELAS']
        )
    
    # Inicializar tabuleiro com bloqueios azuis
    tabuleiro = [[EMOJI_ABERTO for _ in range(tamanho)] for _ in range(tamanho)]
    
    # Selecionar coordenadas aleatórias
    coordenadas_sorteadas = random.sample(
        [(x, y) for x in range(tamanho) for y in range(tamanho)],
        num_casas_sorteadas
    )
    
    # Marcar com estrelas
    for x, y in coordenadas_sorteadas:
        tabuleiro[x][y] = EMOJI_ESTRELA
    
    logger.debug(f"Tabuleiro criado: {tamanho}x{tamanho} com {num_casas_sorteadas} estrelas")
    return tabuleiro, num_casas_sorteadas


def formatar_tabuleiro(tabuleiro: List[List[str]]) -> str:
    """
    Formata um tabuleiro 2D em uma string para exibição.
    
    Args:
        tabuleiro: Tabuleiro em formato de lista 2D.
    
    Returns:
        String formatada para exibição no Telegram.
    """
    return "\n".join("".join(linha) for linha in tabuleiro)


def calcular_parametros_sinal(
    num_casas_sorteadas: int
) -> Tuple[int, int]:
    """
    Calcula o número de tentativas e minas baseado no número de estrelas.
    
    Minas variam entre 2-4 com pequena aleatoridade para melhor acurácia nas previsões.
    Usa 3 métodos diferentes com probabilidades iguais:
    
    1. Aleatório puro: 2-4 minas
    2. Correlacionado com estrelas: 2-4 minas
    3. Distribuição com leve variação: 2-4 minas
    
    Args:
        num_casas_sorteadas: Número de casas sorteadas (estrelas).
    
    Returns:
        Tupla com (tentativas: int, minas: int).
    """
    # Escolher um dos 3 métodos de cálculo de forma aleatória
    metodo = random.randint(1, 3)
    
    if metodo == 1:
        # ===== MÉTODO 1: Aleatório Puro (2-4) =====
        # Gera minas aleatórias sem relação com estrelas
        minas = random.randint(
            config.get('MIN_BOMBAS_ALEATORIO', 2),
            config.get('MAX_BOMBAS_ALEATORIO', 4)
        )
        logger.debug(f"Método 1 (Aleatório Puro): Minas = {minas}")
        
    elif metodo == 2:
        # ===== MÉTODO 2: Correlacionado com Estrelas (2-4) =====
        # Mantém a lógica original mas restrita a 2-4 minas
        if num_casas_sorteadas == 2:
            minas = 2
        elif num_casas_sorteadas == 3:
            minas = random.randint(2, 3)
        else:  # 4 ou mais
            minas = random.randint(3, 4)
        logger.debug(f"Método 2 (Correlacionado): Estrelas={num_casas_sorteadas}, Minas={minas}")
        
    else:  # metodo == 3
        # ===== MÉTODO 3: Distribuição com Leve Variação (2-4) =====
        # Distribuição mais ponderada para 2-3 minas
        peso = random.randint(1, 100)
        
        if peso <= 40:  # 40% - 2 minas
            minas = 2
        elif peso <= 80:  # 40% - 3 minas
            minas = 3
        else:  # 20% - 4 minas
            minas = 4
        logger.debug(f"Método 3 (Distribuição): Peso={peso}%, Minas={minas}")
    
    # Garantir que as minas estejam dentro do intervalo configurado
    min_bombas = config.get('MIN_BOMBAS', 2)
    max_bombas = config.get('MAX_BOMBAS', 4)
    minas = max(min_bombas, min(minas, max_bombas))
    
    # Calcular tentativas baseado TAMBÉM de forma aleatória
    tentativas = random.randint(3, 12)
    
    logger.debug(f"Parâmetros finais - Tentativas: {tentativas}, Minas: {minas}")
    return tentativas, minas


# ============================================================================
# FUNÇÕES DE ENVIO DE MENSAGENS
# ============================================================================

def enviar_mensagem_texto(chat_id: str, texto: str) -> bool:
    """
    Envia uma mensagem de texto para o chat.
    
    Args:
        chat_id: ID do chat Telegram.
        texto: Texto a enviar.
    
    Returns:
        True se enviado com sucesso, False caso contrário.
    """
    try:
        bot.send_message(chat_id, texto, parse_mode="Markdown")
        logger.info(f"Mensagem enviada para {chat_id}")
        return True
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem: {e}", exc_info=True)
        return False


def enviar_mensagem_com_markup(
    chat_id: str,
    texto: str,
    markup: types.InlineKeyboardMarkup
) -> bool:
    """
    Envia uma mensagem de texto com botões inline.
    
    Args:
        chat_id: ID do chat Telegram.
        texto: Texto a enviar.
        markup: Markup com os botões.
    
    Returns:
        True se enviado com sucesso, False caso contrário.
    """
    try:
        bot.send_message(chat_id, texto, parse_mode="Markdown", reply_markup=markup)
        logger.info(f"Mensagem com markup enviada para {chat_id}")
        return True
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem com markup: {e}", exc_info=True)
        return False


def enviar_foto_tabuleiro(
    chat_id: str,
    caminho_imagem: str,
    caption: str,
    markup: types.InlineKeyboardMarkup
) -> Optional[telebot.types.Message]:
    """
    Envia uma foto com o tabuleiro e legenda.
    
    Args:
        chat_id: ID do chat Telegram.
        caminho_imagem: Caminho do arquivo de imagem.
        caption: Legenda da foto.
        markup: Markup com os botões.
    
    Returns:
        Objeto Message se enviado com sucesso, None caso contrário.
    """
    # Validar arquivo antes de enviar
    valido, msg = validar_imagem(caminho_imagem)
    if not valido:
        logger.error(f"Impossível enviar foto: {msg}")
        # Enviar mensagem de erro amigável
        enviar_mensagem_texto(
            chat_id,
            f"{EMOJI_ERROR} *Erro ao enviar tabuleiro*\n"
            f"Arquivo de imagem não está disponível.\n"
            f"Contate o administrador."
        )
        return None
    
    try:
        with open(caminho_imagem, 'rb') as img:
            mensagem = bot.send_photo(
                chat_id,
                img,
                caption=caption,
                parse_mode="Markdown",
                reply_markup=markup
            )
        logger.info(f"Foto enviada para {chat_id} (mensagem ID: {mensagem.message_id})")
        return mensagem
    except Exception as e:
        logger.error(f"Erro ao enviar foto: {e}", exc_info=True)
        return None


# ============================================================================
# FUNÇÕES DE CRONÔMETRO
# ============================================================================

def atualizar_cronometro(
    chat_id: str,
    message_id: int,
    tabuleiro_formatado: str,
    tempo_restante: int,
    markup: types.InlineKeyboardMarkup,
    tentativas: int,
    minas: int
) -> None:
    """
    Atualiza o cronômetro de uma mensagem de foto em tempo real.
    
    A função atualiza a legenda da foto a cada INTERVALO_ATUALIZACAO_CRONOMETRO
    segundos, mostrando o tempo restante formatado como MM:SS.
    
    Args:
        chat_id: ID do chat Telegram.
        message_id: ID da mensagem a atualizar.
        tabuleiro_formatado: Tabuleiro formatado em string.
        tempo_restante: Tempo em segundos para o cronômetro.
        markup: Markup com os botões.
        tentativas: Número de tentativas calculadas para o sinal.
        minas: Número de minas calculadas para o sinal.
    """
    mensagem_anterior = None
    
    logger.info(f"Iniciando cronômetro: {tempo_restante}s para mensagem {message_id}")
    
    while tempo_restante > 0:
        minutos, segundos = divmod(tempo_restante, 60)
        
        # Construir conteúdo da mensagem
        conteudo_base = (
            f"🟦 *Luxury* 🟦\n"
            f"-------------------------------------\n"
            f"{EMOJI_RAIO} - *Tentativas Restantes*: {tentativas}\n"
            f"{EMOJI_BOMBA} - *Minas Ativadas*: {minas}\n"
            f"{EMOJI_RELOGIO} - *Validade*: 2:00 minutos\n\n"
            f"{tabuleiro_formatado}\n\n"
            f"-------------------------------------\n"
            f"{EMOJI_SINAL_BREVE} *OS SINAIS FUNCIONAM APENAS NA PLATAFORMA ABAIXO!*\n"
        )
        
        cronometro_formatado = f"```\n{EMOJI_RELOGIO} {minutos:02d}:{segundos:02d} restantes\n```"
        novo_conteudo = f"{conteudo_base}\n\n{cronometro_formatado}"
        
        # Atualizar apenas se o conteúdo mudou
        if mensagem_anterior != novo_conteudo:
            try:
                bot.edit_message_caption(
                    chat_id=chat_id,
                    message_id=message_id,
                    caption=novo_conteudo,
                    reply_markup=markup,
                    parse_mode="Markdown"
                )
                mensagem_anterior = novo_conteudo
                logger.debug(f"Cronômetro atualizado: {minutos:02d}:{segundos:02d}")
                time.sleep(INTERVALO_ATUALIZACAO_CRONOMETRO)
                tempo_restante -= INTERVALO_ATUALIZACAO_CRONOMETRO
            except Exception as e:
                logger.error(f"Erro ao atualizar cronômetro: {e}", exc_info=True)
                break
    
    # Mensagem final quando tempo esgota
    try:
        bot.edit_message_caption(
            chat_id=chat_id,
            message_id=message_id,
            caption=MARCADOR_TEMPO_ESGOTADO,
            reply_markup=markup,
            parse_mode="Markdown"
        )
        logger.info("Cronômetro finalizado - tempo esgotado")
    except Exception as e:
        logger.error(f"Erro ao exibir mensagem de tempo esgotado: {e}", exc_info=True)

# ============================================================================
# FUNÇÃO PRINCIPAL - ENVIO DE SINAIS
# ============================================================================

def enviar_sinal() -> None:
    """
    Envia um ciclo completo de sinal com:
    1. Aviso de preparação
    2. Criação e envio do tabuleiro
    3. Cronômetro em tempo real
    4. Mensagem de sucesso (GREEN)
    5. Ranking de apostadores
    
    Esta função executa a sequência completa de eventos de um sinal,
    respeitando os delays configurados.
    """
    logger.info("Iniciando novo ciclo de sinal")
    
    try:
        # ========== ETAPA 1: Aviso de Preparação ==========
        logger.info("Etapa 1: Enviando aviso de preparação")
        aviso_preparacao = (
            f"{EMOJI_SINAL_BREVE} - {MARCADOR_PREPARACAO}\n\n"
            f"```{EMOJI_TRIAGULO_PARA_CIMA}Aguarde... Um novo sinal está sendo capturado.```\n"
        )
        enviar_mensagem_texto(config['CHAT_ID'], aviso_preparacao)
        time.sleep(config['DELAY_SINAL_EM_BREVE'])
        
        # ========== ETAPA 2: Geração do Tabuleiro ==========
        logger.info("Etapa 2: Gerando tabuleiro e parâmetros")
        tabuleiro, num_casas_sorteadas = criar_tabuleiro()
        tabuleiro_formatado = formatar_tabuleiro(tabuleiro)
        tentativas, minas = calcular_parametros_sinal(num_casas_sorteadas)
        
        # ========== ETAPA 3: Aviso de Sinal Capturado ==========
        logger.info("Etapa 3: Enviando aviso de sinal capturado")
        aviso_capturado = (
            f"{EMOJI_SINAL_CAPTURADO} - {MARCADOR_CAPTURADO}\n\n"
            f"```{EMOJI_TRIANGULO_INVERTIDO}Confira! O tabuleiro será gerado abaixo.```\n"
        )
        enviar_mensagem_texto(config['CHAT_ID'], aviso_capturado)
        time.sleep(config['DELAY_SINAL_CAPTURADO'])
        
        # ========== ETAPA 4: Envio do Tabuleiro com Foto ==========
        logger.info("Etapa 4: Enviando tabuleiro com foto")
        
        # Criar markup com botão
        markup_tabuleiro = types.InlineKeyboardMarkup()
        markup_tabuleiro.add(types.InlineKeyboardButton(
            f"{EMOJI_GLOBO} Acessar Plataforma",
            url=config['PLATAFORMA_1_URL']
        ))
        
        # Construir legenda do tabuleiro
        legenda_tabuleiro = (
            f"🔒 *Luxury* 🔒\n"
            f"-------------------------------------\n"
            f"{EMOJI_RAIO} - *Tentativas*: {tentativas}\n"
            f"{EMOJI_BOMBA} - *Minas Ativadas*: {minas}\n"
            f"{EMOJI_RELOGIO} - *Validade*: 2:00 minutos\n\n"
            f"{tabuleiro_formatado}\n\n"
            f"-------------------------------------\n"
            f"{EMOJI_SINAL_BREVE} {TEXTO_PLATAFORMAS_AUTORIZADAS}\n"
        )
        
        # Enviar foto
        mensagem = enviar_foto_tabuleiro(
            config['CHAT_ID'],
            config['CAMINHO_IMAGEM'],
            legenda_tabuleiro,
            markup_tabuleiro
        )
        
        if mensagem is None:
            logger.warning("Falha ao enviar foto, continuando ciclo...")
            time.sleep(config['DELAY_ENVIO_TABULEIRO'])
        else:
            # ========== ETAPA 5: Cronômetro ==========
            logger.info("Etapa 5: Iniciando cronômetro")
            thread_cronometro = threading.Thread(
                target=atualizar_cronometro,
                args=(
                    config['CHAT_ID'],
                    mensagem.message_id,
                    tabuleiro_formatado,
                    TEMPO_CRONOMETRO_TOTAL,
                    markup_tabuleiro,
                    tentativas,
                    minas
                ),
                daemon=True,
                name="CronometroThread"
            )
            thread_cronometro.start()
            
            time.sleep(config['DELAY_ENVIO_TABULEIRO'])
        
        # ========== ETAPA 6: Mensagem de Sucesso (GREEN) ==========
        logger.info("Etapa 6: Enviando mensagem de sucesso")
        msg_sucesso = (
            f"{MARCADOR_GREEN}\n"
            f"-------------------------------------\n"
            f"{EMOJI_CONFETE} *{TEXTO_PARABENIZACAO}*\n"
            f"{TEXTO_LUCRO_EXCLUSIVO} {EMOJI_DINHEIRO}\n"
            f"-------------------------------------\n"
        )
        enviar_mensagem_texto(config['CHAT_ID'], msg_sucesso)
        time.sleep(config['DELAY_ENVIO_GREEN'])
        
        # ========== ETAPA 7: Ranking ==========
        logger.info("Etapa 7: Enviando ranking")
        porcentagem_vitoria = gerar_porcentagem()
        ranking = gerar_ranking()
        
        markup_ranking = types.InlineKeyboardMarkup()
        markup_ranking.add(types.InlineKeyboardButton(
            f"{EMOJI_GLOBO} Lucre Agora!",
            url=config['PLATAFORMA_2_URL']
        ))
        
        msg_ranking = (
            f"{EMOJI_TROFEU} *{TEXTO_RANKING}!* {EMOJI_TROFEU}\n"
            f"-------------------------------------\n"
            f"📊 *{porcentagem_vitoria}% {TEXTO_APOSTADORES}*\n\n"
            f"{ranking}\n"
            f"-------------------------------------\n"
        )
        enviar_mensagem_com_markup(
            config['CHAT_ID'],
            msg_ranking,
            markup_ranking
        )
        time.sleep(config['DELAY_ENVIO_RANKING'])
        
        logger.info("Ciclo de sinal concluído com sucesso")
        
    except Exception as e:
        logger.error(f"Erro no envio de sinais: {e}", exc_info=True)


# ============================================================================
# FUNÇÃO DE CICLO AUTOMÁTICO
# ============================================================================

def ciclo_sinais() -> None:
    """
    Executa um loop infinito que envia sinais repetidamente.
    
    Caso ocorra algum erro durante o envio de um sinal, a função registra
    o erro e aguarda TEMPO_ESPERA_ERRO segundos antes de tentar novamente.
    """
    logger.info("Iniciando ciclo automático de sinais...")
    
    while True:
        try:
            enviar_sinal()
        except KeyboardInterrupt:
            logger.warning("Ciclo interrompido pelo usuário (Ctrl+C)")
            break
        except Exception as e:
            logger.error(f"Erro no ciclo de sinais: {e}", exc_info=True)
            logger.info(f"Aguardando {TEMPO_ESPERA_ERRO}s antes de tentar novamente...")
            time.sleep(TEMPO_ESPERA_ERRO)


# ============================================================================
# FUNÇÃO PRINCIPAL - INICIALIZAÇÃO DO BOT
# ============================================================================

def inicializar_bot() -> bool:
    """
    Inicializa o bot do Telegram com as configurações validadas.
    
    Returns:
        True se inicializado com sucesso, False caso contrário.
    """
    global bot
    
    try:
        logger.info("Inicializando bot do Telegram...")
        bot = telebot.TeleBot(config['API_TOKEN'])
        
        # Teste de conexão
        try:
            bot_info = bot.get_me()
            logger.info(f"Bot conectado com sucesso: @{bot_info.username}")
            return True
        except Exception as e:
            logger.error(f"Erro ao conectar com a API do Telegram: {e}", exc_info=True)
            return False
            
    except Exception as e:
        logger.error(f"Erro ao inicializar o bot: {e}", exc_info=True)
        return False


# ============================================================================
# ENTRY POINT - FUNÇÃO PRINCIPAL
# ============================================================================

def main() -> None:
    """
    Função principal que configura e executa o bot.
    
    Realiza as seguintes etapas:
    1. Carrega e valida configurações
    2. Inicializa o bot
    3. Inicia o ciclo de envio de sinais em thread separada
    4. Inicia o polling do bot (aguarda mensagens)
    """
    logger.info("=" * 70)
    logger.info("BOT DE SINAIS LUXURY - INICIANDO")
    logger.info("=" * 70)
    
    try:
        # Carregar configurações
        logger.info("Carregando configurações...")
        carregar_configuracoes()
        
        # Inicializar bot
        logger.info("Inicializando bot...")
        if not inicializar_bot():
            logger.critical("Falha ao inicializar o bot. Abortando.")
            raise SystemExit(1)
        
        logger.info(f"{EMOJI_CHECKBOX} Bot iniciado com sucesso")
        logger.info(f"{EMOJI_CHECKBOX} Chat ID configurado: {config['CHAT_ID']}")
        logger.info(f"{EMOJI_CHECKBOX} Delay entre sinais: {config['DELAY_ENVIO_TABULEIRO']}s")
        
        # Iniciar thread de ciclo de sinais
        logger.info("Iniciando thread de ciclo de sinais...")
        thread_sinais = threading.Thread(
            target=ciclo_sinais,
            daemon=True,
            name="SinaisThread"
        )
        thread_sinais.start()
        logger.info("Thread de sinais iniciada")
        
        # Iniciar polling
        logger.info(f"{EMOJI_CHECKBOX} Bot aguardando mensagens... (Ctrl+C para parar)")
        logger.info("=" * 70)
        bot.polling(none_stop=True, interval=0)
        
    except KeyboardInterrupt:
        logger.warning("Bot interrompido pelo usuário (Ctrl+C)")
    except SystemExit:
        raise
    except Exception as e:
        logger.critical(f"Erro crítico: {e}", exc_info=True)
        raise
    finally:
        logger.info("=" * 70)
        logger.info("BOT FINALIZADO")
        logger.info("=" * 70)


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    main()
