import json
import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service

from scipy.spatial.distance import cdist

from typing import Dict

# Получаем всю информацию о банкоматах с первоначальной страницы (Минск). Ключ - по названию (по координатам не работает, т.к. могут быть одинаковые адреса). 
def atms_info_generator() -> Dict:
    s = Service(executable_path=None, port=0)
    driver = webdriver.Chrome(service = s)
    driver.get('https://www.prior.by/maps')
    time.sleep(1) # задержка для запуска дравера, чтобы странница полностью прогрузилась, иначе "кнопки" могут не сработать
    # переключаемся с вида "карта" на вид "список"
    driver.find_element(by = 'id', value = 'lbllist').click()
    time.sleep(0.5)
    # переходим на последнюю страницу и определяем общее кол-во страниц
    last_page_button = driver.find_element(By.CSS_SELECTOR, 'a[aria-label="К последней странице"]')
    last_page_button.click()
    pages = int(last_page_button.get_attribute('data-page')) # число страниц
    # возвращаемся на первую страницу
    driver.find_element(By.CSS_SELECTOR, 'a[aria-label="Вернуться на первую страницу"]').click()
    atm_name = []
    atms_adr_list = []
    atm_coords = []
    atm_worktime = []
    for _ in (range(pages)): 
        html = driver.page_source
        soup = BeautifulSoup(markup = html, features = 'lxml')
        tbody = soup.find_all("td", role="gridcell")
        i = 1
        # Записываем данные
        while i < len(tbody):
            atm_name.append(tbody[i].text) # Name
            atms_adr_list.append(tbody[i+1].find('div').text) #address
            atm_coords.append(str(tbody[i+1].find('div', class_='link')['onclick']).split('showOnMap(')[1].split(');')[0].split(',')) #coords
            atm_worktime.append(tbody[i+2].text.replace(';','')) #worktime
            i += 6
        # переходим на следующую страницу
        driver.find_element(By.CSS_SELECTOR, 'a[aria-label="Перейдите на следующую страницу"]').click()
#    driver.quit() - не нужно, т.к. закрывается сам, когда не может нажать на кнопку "на следующую страницу" на последней страннице
    atms_full_info = dict()
    for i in range(len(atm_name)):
        atms_full_info[atm_name[i]] = [[float(atm_coords[i][0]), float(atm_coords[i][1])], atms_adr_list[i], atm_worktime[i]]

    # Записываем данные в файл
    with open("atms_full_info.json", "w") as file:
        # Convert dictionary to a string using json.dumps()
        dict_str = json.dumps(atms_full_info)
        file.write(dict_str)

    return atms_full_info