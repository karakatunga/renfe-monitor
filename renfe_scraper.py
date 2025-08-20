# -*- coding: utf-8 -*-
"""
Script de web scraping para monitorizar billetes en Renfe.com.

Versión 11.0 - La Final. Esta versión contiene la lógica de análisis de
la página de resultados completamente reescrita para coincidir con la
estructura HTML real, garantizando una detección de disponibilidad precisa.

Autor: Alberto Ines
Fecha: [Fecha Actual]
"""

import os
import smtplib
import ssl
import time
from datetime import datetime

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- LIBRERÍAS DE SELENIUM ---
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# --- GESTOR AUTOMÁTICO DE DRIVER ---
from webdriver_manager.chrome import ChromeDriverManager

# ==============================================================================
# --- CONFIGURACIÓN DE USUARIO ---
# ==============================================================================

# -- Datos del Viaje --
ORIGEN = "Linares-Baeza"
DESTINO = "Madrid"
# Formato: "DD/MM/AAAA"
FECHA_IDA = "21/08/2025"
# Formato: "HH:MM"
HORA_SALIDA_TREN = "09:13"

# -- Datos del Email de Notificación --
EMAIL_REMITENTE = os.environ.get("EMAIL_REMITENTE")
EMAIL_CONTRASENA_APP = os.environ.get("EMAIL_CONTRASENA_APP")
EMAIL_DESTINATARIO = os.environ.get("EMAIL_DESTINATARIO")
EMAIL_SMTP_SERVER = "smtp.gmail.com"
EMAIL_SMTP_PORT = 465

# -- Configuración del Script --
INTERVALO_SEGUNDOS = 300
HEADLESS_MODE = False  # Cambiar a False para ver el navegador en acción

# ==============================================================================
# --- FIN DE LA CONFIGURACIÓN ---
# ==============================================================================

def configurar_driver():
    """Configura e inicializa el WebDriver de Selenium."""
    print("Configurando el driver de Chrome...")
    options = webdriver.ChromeOptions()
    if HEADLESS_MODE:
        options.add_argument("--headless")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def enviar_correo():
    """Construye y envía el correo electrónico de notificación."""
    print("¡Tren disponible! Preparando notificación por correo electrónico...")
    message = MIMEMultipart("alternative")
    message["Subject"] = f"✅ ¡Plazas Disponibles en tu Tren Renfe!"
    message["From"] = EMAIL_REMITENTE
    message["To"] = EMAIL_DESTINATARIO
    html = f"""
    <html><body>
        <h2>¡Alerta de Disponibilidad de Billetes Renfe!</h2>
        <p>Se han encontrado plazas disponibles para el tren que estabas monitorizando.</p>
        <h3>Detalles del Viaje:</h3>
        <ul>
            <li><b>Origen:</b> {ORIGEN}</li>
            <li><b>Destino:</b> {DESTINO}</li>
            <li><b>Fecha:</b> {FECHA_IDA}</li>
            <li><b>Hora de Salida:</b> {HORA_SALIDA_TREN}</li>
        </ul>
        <p>¡Date prisa y compra tu billete! <a href="https://www.renfe.com" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Ir a Renfe.com</a></p>
    </body></html>
    """
    message.attach(MIMEText(html, "html"))
    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL(EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT, context=context) as server:
            server.login(EMAIL_REMITENTE, EMAIL_CONTRASENA_APP)
            server.sendmail(EMAIL_REMITENTE, EMAIL_DESTINATARIO, message.as_string())
        print(f"Correo de notificación enviado con éxito a {EMAIL_DESTINATARIO}.")
    except Exception as e:
        print(f"Error crítico al enviar el correo: {e}")


def rellenar_origen_destino_robusto(wait, input_id, list_css_selector, texto_a_buscar):
    """Función para rellenar Origen/Destino."""
    print(f"Rellenando campo '{input_id}' con '{texto_a_buscar}'...")
    campo_input = wait.until(EC.element_to_be_clickable((By.ID, input_id)))
    campo_input.click()
    campo_input.clear()
    campo_input.send_keys(texto_a_buscar)
    time.sleep(1) 
    opcion = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, list_css_selector)))
    opcion.click()
    print(f"Campo '{input_id}' seleccionado con éxito: '{texto_a_buscar}'.")


def buscar_y_seleccionar_tren(driver):
    """Realiza la búsqueda completa en la web de Renfe."""
    wait = WebDriverWait(driver, 20)
    print("Abriendo Renfe.com...")
    driver.get("https://www.renfe.com/es/es")
    try:
        wait.until(EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))).click()
        print("Política de cookies aceptada.")
    except TimeoutException:
        print("No se encontró el banner de cookies o ya estaba aceptado.")
    rellenar_origen_destino_robusto(wait, "origin", "#awesomplete_list_1 > li", ORIGEN)
    rellenar_origen_destino_robusto(wait, "destination", "#awesomplete_list_2 > li", DESTINO)
    print("Iniciando selección de fecha...")
    wait.until(EC.element_to_be_clickable((By.ID, "first-input"))).click()
    one_way_label_selector = "//label[contains(normalize-space(), 'Viaje solo ida')]"
    wait.until(EC.element_to_be_clickable((By.XPATH, one_way_label_selector))).click()
    time.sleep(1)
    print(f"Buscando la fecha {FECHA_IDA} usando su timestamp...")
    fecha_obj = datetime.strptime(FECHA_IDA, "%d/%m/%Y").replace(hour=0, minute=0, second=0, microsecond=0)
    target_timestamp_ms = int(fecha_obj.timestamp() * 1000)
    day_selector = f"div.lightpick__day[data-time='{str(target_timestamp_ms)}']"
    date_selected = False
    for _ in range(24):
        try:
            day_element = driver.find_element(By.CSS_SELECTOR, day_selector)
            if day_element.is_displayed():
                print("Fecha encontrada. Seleccionando día...")
                day_element.click()
                date_selected = True
                break
        except NoSuchElementException:
            next_button_selector = "div.lightpick__nav-action-next"
            wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, next_button_selector))).click()
            time.sleep(0.5)
    if not date_selected:
        raise Exception(f"No se pudo encontrar la fecha {FECHA_IDA} en el calendario.")
    print("Confirmando con el botón 'Aceptar' (modo JS)...")
    accept_button_selector = "button.lightpick__apply-action-sub"
    accept_button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, accept_button_selector)))
    driver.execute_script("arguments[0].click();", accept_button)
    print("Fecha confirmada.")
    print("Haciendo clic en 'Buscar billete'...")
    search_button_selector = "//button[contains(., 'Buscar billete')]"
    wait.until(EC.element_to_be_clickable((By.XPATH, search_button_selector))).click()
    print("Búsqueda iniciada. Esperando resultados...")


def comprobar_disponibilidad(driver):
    """
    Analiza la página de resultados utilizando la estructura HTML real para
    identificar la hora y la disponibilidad (presencia de precio).
    """
    wait = WebDriverWait(driver, 40)
    
    print("Esperando la carga de la lista de trenes...")
    try:
        # PASO 1: Esperar a que el contenedor principal de la lista de trenes sea visible.
        wait.until(EC.visibility_of_element_located((By.ID, "listaTrenesTBodyIda")))
        print("Lista de trenes cargada.")
    except TimeoutException:
        if "No hay trenes para la fecha seleccionada" in driver.page_source:
             print("Mensaje oficial de Renfe: No hay trenes para esta ruta y fecha.")
             return "no_trenes"
        print("Error: La página de resultados no cargó a tiempo.")
        raise # Relanzamos la excepción para que el main() la capture y guarde screenshot.

    # PASO 2: Obtener todos los elementos de tren.
    trenes = driver.find_elements(By.CSS_SELECTOR, "div.selectedTren")
    print(f"Se encontraron {len(trenes)} trenes. Analizando...")

    tren_encontrado = False
    for tren in trenes:
        try:
            # PASO 3: Extraer la hora de salida de CADA tren.
            # La hora está en el primer `h5` dentro del div con clase `trenes`.
            hora_salida_element = tren.find_element(By.CSS_SELECTOR, "div.trenes > h5")
            # El texto es "HH:MM h", lo limpiamos para la comparación.
            hora_salida_texto = hora_salida_element.text.strip().replace(' h', '')
            
            # PASO 4: Comprobar si es el tren que buscamos.
            if hora_salida_texto == HORA_SALIDA_TREN:
                tren_encontrado = True
                print(f"Tren de las {HORA_SALIDA_TREN} encontrado.")
                
                # PASO 5: Comprobar disponibilidad por la presencia del precio.
                try:
                    # Buscamos el elemento del precio DENTRO del `div` del tren actual.
                    tren.find_element(By.CSS_SELECTOR, "span.precio-final")
                    # Si la línea anterior no lanza un error, el elemento existe.
                    print("¡Precio encontrado! El tren está DISPONIBLE.")
                    return True  # ¡ÉXITO!
                except NoSuchElementException:
                    # Si no encontramos el `span.precio-final`, el tren no tiene billetes a la venta.
                    print("No se encontró precio. El tren NO está disponible (Completo o sin tarifas).")
                    return False

        except NoSuchElementException:
            # Ignorar si un elemento de la lista no tiene la estructura de un tren.
            continue
    
    if not tren_encontrado:
        print(f"AVISO: El tren con hora {HORA_SALIDA_TREN} no se ha encontrado en la lista de resultados.")
    
    return False # Devuelve False si el tren no se encontró o si no estaba disponible.


def main():
    """
    Función principal que realiza UNA ÚNICA comprobación de disponibilidad.
    Está diseñada para ser llamada por un orquestador externo como GitHub Actions.
    """
    print("\n" + "="*50)
    print(f"INICIANDO COMPROBACIÓN - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)
    
    driver = None
    try:
        driver = configurar_driver()
        buscar_y_seleccionar_tren(driver)
        disponible = comprobar_disponibilidad(driver)

        if disponible is True:
            enviar_correo()
            print("\n¡ÉXITO! SCRIPT FINALIZADO.")
        elif disponible == "no_trenes":
            print("No hay trenes programados. Finalizando comprobación.")
        else:
            print("El tren no está disponible. Finalizando comprobación.")

    except Exception as e:
        print(f"\n--- ERROR INESPERADO DURANTE LA EJECUCIÓN ---")
        print(f"Error: {e.__class__.__name__} - {str(e).splitlines()[0]}")
        if driver:
            screenshot_path = "error_renfe.png" # Nombre simple, ya que cada ejecución es independiente
            try:
                driver.save_screenshot(screenshot_path)
                print(f"Captura de pantalla guardada en: {screenshot_path}")
            except Exception as e_ss:
                print(f"No se pudo guardar la captura de pantalla: {e_ss}")
        # Es importante que el script termine con un código de error si falla
        # para que GitHub Actions marque la ejecución como fallida.
        raise e 
    
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    main()




