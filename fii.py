import time
import pandas as pd
import streamlit as st

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

st.set_page_config(layout="wide")  # 👈 deixa o app ocupar 100% da largura

# ----------------------------------------------
# Função para buscar a tabela no Fundsexplorer
# ----------------------------------------------
@st.cache_data(show_spinner=True)
@st.cache_data(show_spinner=True)
@st.cache_data(show_spinner=True)
def get_fii_table():
    url = "https://www.fundsexplorer.com.br/ranking"

    options = Options()
    # options.add_argument("--headless=new")
    # options.add_argument("--no-sandbox")
    # options.add_argument("--disable-dev-shm-usage")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    wait = WebDriverWait(driver, 20)

    try:
        driver.get(url)
        time.sleep(2)  # espera inicial

        # --- 0) Tenta fechar/aceitar o cookie banner por vários caminhos ---
        cookie_selectors = [
            'button[data-test="accept"]',
            'button#hs-eu-confirmation-button',             # exemplos comuns
            'button[aria-label*="aceitar"]',
            'button:contains("Aceitar")',                   # fallback textual (pode não funcionar no CSS)
            'div#hs-en-cookie-confirmation-buttons-area button',
            'button:contains("Aceitar todos")'
        ]
        # tentar por texto também (mais confiável)
        texts_to_try = ["Aceitar todos", "Aceitar", "OK", "Fechar"]

        # 1) tentar clique por seletores diretos
        for sel in cookie_selectors:
            try:
                els = driver.find_elements(By.CSS_SELECTOR, sel)
                if els:
                    for e in els:
                        try:
                            driver.execute_script("arguments[0].scrollIntoView(true);", e)
                            driver.execute_script("arguments[0].click();", e)
                            time.sleep(0.4)
                        except Exception:
                            pass
                    # se algum botão foi clicado, pausa e tenta prosseguir
                    time.sleep(0.6)
            except Exception:
                pass

        # 2) tentar clicar por texto (procura por botões/links)
        for txt in texts_to_try:
            try:
                candidates = driver.find_elements(By.XPATH, f"//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{txt.lower()}') or //a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{txt.lower()}')]]")
                if candidates:
                    for c in candidates:
                        try:
                            driver.execute_script("arguments[0].scrollIntoView(true);", c)
                            driver.execute_script("arguments[0].click();", c)
                            time.sleep(0.4)
                        except Exception:
                            pass
                    time.sleep(0.6)
            except Exception:
                pass

        # 3) se ainda existir o elemento de cookie conhecido, remove via JS (forçado)
        try:
            driver.execute_script("""
                var el = document.getElementById('hs-en-cookie-confirmation-buttons-area');
                if (el) { el.remove(); }
                var el2 = document.querySelector('[id^=hs-en-cookie]'); if(el2) el2.remove();
                var overlays = document.querySelectorAll('.cookie, .cookies, .hs-cookie-banner'); 
                overlays.forEach(e => e.remove());
            """)
            time.sleep(0.4)
        except Exception:
            pass

        # --- 4) abrir o menu de colunas (scroll + click via JS para evitar intercept) ---
        botao_colunas = wait.until(EC.presence_of_element_located((By.ID, "colunas-ranking__select-button")))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", botao_colunas)
        try:
            # preferencial: click via JS para evitar intercept
            driver.execute_script("arguments[0].click();", botao_colunas)
        except Exception:
            # fallback: webdriver click
            botao_colunas.click()
        time.sleep(0.6)

        # --- 5) clicar em "todos" (label) ---
        label_todos = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'label[for="colunas-ranking__todos"]')))
        driver.execute_script("arguments[0].scrollIntoView(true);", label_todos)
        try:
            driver.execute_script("arguments[0].click();", label_todos)
        except Exception:
            label_todos.click()
        time.sleep(1.0)  # deixa o JS atualizar a tabela

        # --- 6) esperar a tabela estar populada ---
        def tabela_populada(driver):
            try:
                rows = driver.find_elements(By.CSS_SELECTOR, ".default-fiis-table__container__table tbody tr")
                # contar linhas não-vazias
                count = 0
                for r in rows:
                    tds = r.find_elements(By.TAG_NAME, "td")
                    if any(td.text.strip() for td in tds):
                        count += 1
                return count > 5  # ajuste se precisar
            except:
                return False

        wait.until(tabela_populada)

        # --- 7) pegar HTML da tabela ---
        tabela = driver.find_element(By.CSS_SELECTOR, ".default-fiis-table__container__table")
        html = tabela.get_attribute("outerHTML")
        df = pd.read_html(html)[0]
        return df

    finally:
        driver.quit()



# ----------------------------------------------
# Streamlit interface
# ----------------------------------------------
st.title("📊 Análise de FIIs — Fundsexplorer")

st.write("Buscando dados diretamente do site...")

df = get_fii_table()

st.subheader("Filtros")

# Tratando os dados

# Tirar as linhas que tiverem NAs nas colunas importantes
df = df.dropna(subset=['P/VP', 'Dividend Yield', 'DY (3M) Acumulado','DY (6M) Acumulado', 'DY (12M) Acumulado',
       'Patrimônio Líquido', 'Quant. Ativos','Volatilidade', 'Num. Cotistas'])

df['P/VP'] = df['P/VP'].apply(lambda x : x/100)
df['Dividend Yield'] = df['Dividend Yield'].apply(lambda x : float(str(x).replace('%','').replace('.','').replace(',','.')))
df['DY (3M) Acumulado'] = df['DY (3M) Acumulado'].apply(lambda x : float(str(x).replace('%','').replace('.','').replace(',','.')))
df['DY (6M) Acumulado'] = df['DY (6M) Acumulado'].apply(lambda x : float(str(x).replace('%','').replace('.','').replace(',','.')))
df['DY (12M) Acumulado'] = df['DY (12M) Acumulado'].apply(lambda x : float(str(x).replace('%','').replace('.','').replace(',','.')))
df['Volatilidade'] = df['Volatilidade'].apply(lambda x : float(str(x).replace('.','').replace(',','.'))/100)
df['Liquidez Diária (R$)'] = df['Liquidez Diária (R$)'].apply(lambda x : float(str(x).replace('.','').replace(',','.'))/1_000_000)
df['Patrimônio Líquido'] = df['Patrimônio Líquido'].apply(lambda x : float(str(x).replace('.','').replace(',','.'))/1_000_000)
df['Num. Cotistas'] = df['Num. Cotistas'].apply(lambda x : float(str(x).replace('.','').replace(',','.'))/1000)
df['Quant. Ativos'] = df['Quant. Ativos'].apply(lambda x : int(x))

df.rename(columns={
    'Liquidez Diária (R$)': 'Liquidez Diária (milhões R$)',
    'Patrimônio Líquido': 'Patrimônio Líquido (milhões R$)',
    'Num. Cotistas': 'Num. Cotistas (milhares)'
}, inplace=True)

# Replace in colunas importantes the new names
colunas_importantes = ['Fundos', 'Setor', 'Liquidez Diária (milhões R$)', 'P/VP', 'Dividend Yield', 'DY (3M) Acumulado','DY (6M) Acumulado', 'DY (12M) Acumulado',
       'Patrimônio Líquido (milhões R$)', 'Quant. Ativos','Volatilidade', 'Num. Cotistas (milhares)']

# Limpeza inicial automática
parametros_limpeza = {
    "P/VP": [0.5, 1],
    "Dividend Yield": [1, 15],
    'DY (3M) Acumulado' : [3, 50],
    'DY (6M) Acumulado' : [6, 50],
    'DY (12M) Acumulado' : [12, 50],
    'Quant. Ativos' : [1, 150],
    'Num. Cotistas' : [10, 1_000_000_000],
    }

for col, lim in parametros_limpeza.items():
    if col in df.columns:
        df = df[(df[col] >= lim[0]) & (df[col] <= lim[1])]

# Cria filtros automáticos coluna por coluna
filtered_df = df.copy()

for col in colunas_importantes:
    # Limita a filtros úteis — ignora colunas 100% vazias
    # st.write(f"Analisando coluna: {col}, tipo {df[col].dtype}")
    if df[col].dtype == "object":
        unique_vals = df[col].dropna().unique()
        if len(unique_vals) <= 50:  # evitar caixas enormes
            selected = st.multiselect(f"Filtro: {col}", unique_vals)
            if selected:
                filtered_df = filtered_df[filtered_df[col].isin(selected)]
            st.write('_________________')
    else:
        # filtro por faixa (para colunas numéricas)
        min_val = float(df[col].min())
        max_val = float(df[col].max())
        # st.write(f"Valores em {col}: {min_val} a {max_val}")    
        # Markdown slider
        st.markdown(f"### Filtro: {col}")
        selected_range = st.slider('Selecione o intervalo:',
            min_val, max_val, (min_val, max_val),key=col
        )
        st.write('_________________')
        filtered_df = filtered_df[
            (filtered_df[col] >= selected_range[0]) &
            (filtered_df[col] <= selected_range[1])
        ]

st.subheader("Selecionar colunas para exibir")
cols = st.multiselect("Colunas:", df.columns, default=colunas_importantes)
filtered_df = filtered_df[cols]


st.subheader("📄 Resultado filtrado")
#LEn of the filtered dataframe
st.write(f"Número de FIIs encontrados: {len(filtered_df)}")
# Display the filtered dataframe and reset the index for better readability
st.dataframe(filtered_df.reset_index(drop=True))

st.success("Pronto! Sistema funcionando com scraping + filtros dinâmicos 🤝")

# A markdown that say how important is to see the begin of the stock
st.warning("### > Se lembre de verificar o início do FII, para ver se já é uma tese consolidada.")
st.warning("### > Vale verificar se historicamente está pegando bons dividendos, e não só recentemente. Pode ter RMG no meio")
st.warning("### > Verifique as notícias para ver se tem algum problema no FII e tente ler o relatório dele")