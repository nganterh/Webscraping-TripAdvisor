from selenium import webdriver
from bs4 import BeautifulSoup
import requests

import gc
import os
import pandas as pd
import pickle
import re
import time
from tqdm import tqdm


def run_selenium(url, geckodriver_path):
    browser = webdriver.Firefox(executable_path=geckodriver_path)
    browser.get(url + '/Restaurants-g294305-Santiago_Santiago_Metropolitan_Region.html')

    html = browser.page_source
    soup = BeautifulSoup(html, 'lxml')
    
    return {'browser':browser, 'soup':soup}


def info_restaurants(url, geckodriver_path):
    selenium = run_selenium(url, geckodriver_path)
    browser, soup = selenium['browser'], selenium['soup']
    browser.close()
    
    pages = int(soup.find_all('a', class_ = 'pageNum taLnk')[-1].text)
    max_restaurants = int(soup.find('span', class_ = '_1D_QUaKi').text)
    
    return {'pages':pages, 'max_restaurants':max_restaurants}


def check_files(dir_files, keyword):
    dict_files = {}

    for file in os.listdir(dir_files):
        key = re.search('^([0-9]+)', file)
        
        if keyword in file and key is not None:
                dict_files[key.group(1)] = file
            
    return dict_files


def last_pickle(dict_pickles):
    last_date = max([date for date in dict_pickles])
    date_months = {'01':'enero', '02':'febrero', '03':'marzo', '04':'abril', '05':'mayo',
                   '06':'junio', '07':'julio', '08':'agosto', '09':'septiembre',
                   '10':'octubre', '11':'noviembre', '12':'diciembre'}

    last_pickle = dict_pickles[last_date]
    n_urls = int(re.search('_([0-9]+)_', last_pickle).group(1))

    print(f'Información cargada del pickle {last_pickle}' +
          f' extraído el {last_date[-2:]} de {date_months[last_date[4:-2]]} del {last_date[:4]}.')

    return last_pickle
    

def gen_pickle(seeds_url, geckodriver_path, pages, basic_url, time_id):
    browser = run_selenium(seeds_url, geckodriver_path)['browser']
    gc.disable()
    urls = []

    for page in tqdm(range(pages)):
        time.sleep(3)
        
        try:
            html = browser.page_source
            soup = BeautifulSoup(html, 'lxml')
            
            browser.find_element_by_css_selector('a.nav:nth-child(2)').click()
            
            page_restaurants = soup.find_all('div', class_='_1llCuDZj')
            page_urls = [basic_url + restaurant.find_all('a')[0].get('href')
                         for restaurant in page_restaurants]
            
            urls.extend(page_urls)

        except Exception as e:
            browser.close()
            #print(e)
            break
            
    gc.enable()
    gc.collect()
    n_urls = len(set(urls))
    
    with open(f'{time_id}_{n_urls}_urls.pickle', 'wb') as file:
        pickle.dump(list(set(urls)), file)
    
    print(f'Se guardó "{time_id}_{n_urls}_urls.pickle" en "{os.getcwd()}".')
    
    return list(set(urls))


def get_restaurant(url_restaurant):
    html_restaurant = requests.get(url_restaurant)
    soup_restaurant = BeautifulSoup(html_restaurant.text, 'lxml')

    try:
        name = soup_restaurant.find_all('h1')[-1].text
        address_soups = soup_restaurant.find_all('div', class_ = '_1ud-0ITN')

        for address_soup in address_soups:
            try:
                address = address_soup.find('a', class_ = '_15QfMZ2L').text
            except:
                pass

        try:
            grade = float(soup_restaurant.find('span', class_ = 'r2Cf69qf').text.replace(',', '.'))
            n_opinions = int(re.search('([0-9\.]+).*', soup_restaurant.find('a', class_ = '_10Iv7dOs').text).group(1).replace('.', ''))


            dict_qualifications = {}

            qualifications = soup_restaurant.find(
                'div', class_ = 'ui_columns filters').select(
                'div[class*="prw_rup prw_filters_detail_checkbox ui_column separated"]')

            for category in qualifications:
                key = category.find('div', class_ = 'name ui_header h2').text
                values = [(elem.find('label', class_ = 'row_label label').text,
                           int(elem.find('span', class_ = 'row_num is-shown-at-tablet').text.replace('.', '')))
                          if elem.find('span', class_ = 'row_num is-shown-at-tablet') != None
                          else (elem.find('label', class_ = 'row_label label').text, None)
                          for elem in category.find_all('div', class_ = 'ui_checkbox item') if elem != None]

                dict_qualifications[key] = values

        except:
            grade, n_opinions, dict_qualifications = soup_restaurant.find('div', class_ = '_1AhFUMxC').text.replace('\n', ' '), 0 , None

        covid = (True if soup_restaurant.find('div', class_ = '_2oPcIw1r _16XWDY6r') != None else False)
        positions = [''.join(re.search('([0-9]+)(.*)', elem.text).groups()).replace('.', '')
                     for elem in soup_restaurant.find_all('div', class_ = '_3-W4EexF')]

        if len(positions) == 0:
            positions = soup_restaurant.find('div', class_ = '_1AhFUMxC').text.replace('\n', ' ')

        # characteristics = ...

        dict_elem = {i: soup_restaurant.find_all('div', class_ = class_name)
                     for i, class_name in enumerate(['_14zKtJkz', '_1XLfiSsv'])}

        dict_details = {dict_elem[0][i].text: dict_elem[1][i].text for i in range(len(dict_elem[0]))}

        dict_test = {'id':hash(url_restaurant), 'Nombre restaurante':[name], 'Promedio de calificaciones':[grade],
                     'N° de opiniones':[n_opinions], 'Dirección':[address],
                     'Calificación de viajeros por categoría':[dict_qualifications], 'Toman medidas de seguridad':[covid],
                     'Rankings':[positions], 'Tipo de comida y servicios':[dict_details], 'url':url_restaurant}

        return dict_test

    except Exception as e:
        return None
    

def build_dataframe(dict_structure, results, time_id):
    df_main = pd.DataFrame(dict_structure)
    
    for result in results:
        if result != None:
            df_local = pd.DataFrame.from_dict(result)
            df_main = df_main.append(df_local)

    df_main = df_main.set_index(keys='id', drop=True)
    
    return df_main


def review_urls(url):
    html = requests.get(url)
    soup = BeautifulSoup(html.text, 'lxml')
    dict_reviews = {}

    try:
        raw_reviews = soup.find('span', class_ = 'reviews_header_count').text
        n_reviews = re.search('([0-9]+)', raw_reviews).group(1)

        value = [url] + [re.sub('Reviews', f'Reviews-or{num}', url)
                         for num in range(10, int(n_reviews), 10)]
        
    except Exception as e:
        value = e

    return(hash(url), value)


def prepare_urls(dict_reviews):
    tuple_reviews, url_reviews = [], []

    for key in dict_reviews:

        if len(dict_reviews[key]) == 1:
            tuple_reviews = {'identifier':dict_reviews[key][0],
                             'scraping':dict_reviews[key][0]}

            url_reviews.append(tuple_reviews)

        elif len(dict_reviews[key]) > 1:
            tuple_reviews = [{'identifier':dict_reviews[key][0],
                              'scraping':url} for url
                             in dict_reviews[key][1:]]

            url_reviews.extend(tuple_reviews)
            
    return url_reviews


def get_reviews(url):
    try:
        html = requests.get(url['scraping'], timeout=600)
    
    except Exception as e:
        dict_reviews = {'id':hash(url['identifier']), 'restaurant':'timeout', 'grade':'timeout',
                        'date_review':'timeout', 'comments':'timeout', 'date_stayed':'timeout',
                        'response_body':'timeout', 'user_name':'timeout', 'user_reviews':'timeout',
                        'useful_votes':'timeout', 'url':url}
        
        return dict_reviews
        
    soup = BeautifulSoup(html.text, 'lxml')
    restaurant = soup.find('h1', class_ = '_3a1XQ88S').text
    soup_reviews = soup.find_all('div', class_ = 'reviewSelector')
    dict_months = {'enero':1, 'febrero':2, 'marzo':3, 'abril':4,
                  'mayo':5, 'junio':6, 'julio':7, 'agosto':8,
                  'septiembre':9, 'octubre':10, 'noviembre':11, 'diciembre':12}

    dict_reviews = {'id':[], 'restaurant':[], 'grade':[], 'date_review':[], 'comments':[],
                    'date_stayed':[], 'response_body':[], 'user_name':[], 'user_reviews':[],
                    'useful_votes':[], 'url':[]}

    for review in soup_reviews:
        dict_reviews['id'].append(hash(url['identifier']))
        dict_reviews['restaurant'].append(restaurant)
        grade = str(review.find('div', class_ = 'ui_column is-9').span)
        re_grade = int(re.search('_([0-9]+)">', grade).group(1))
        dict_reviews['grade'].append(re_grade)

        try:
            raw_date = re.search('([0-9]+) de ([a-z]+) de ([0-9]+)',
                                 review.find('span', class_ = 'ratingDate').text)

            day, month, year = raw_date.group(1), dict_months[raw_date.group(2)], raw_date.group(3)
            dict_reviews['date_review'].append('{}/{:02d}/{}'.format(day, month, year))

        except:
            dict_reviews['date_review'].append(review.find('span', class_ = 'ratingDate').text)

        dict_reviews['comments'].append(review.find('p', class_ = 'partial_entry').text)

        raw_date = re.search(': ([a-z]+) de ([0-9]+)',
                             review.find('div', class_ = 'prw_rup prw_reviews_stay_date_hsx').text)
        try:
            month, year = dict_months[raw_date.group(1)], raw_date.group(2)
            dict_reviews['date_stayed'].append('{:02d}/{}'.format(month, year))
            
        except Exception as e:
            month, year = review.find('div', class_ = 'prw_rup prw_reviews_stay_date_hsx'), e
            dict_reviews['date_stayed'].append(f'{month} with error: {year}')
            

        #try:
        #    full_response = review.find('div', class_ = 'mgrRspnInline')
        #    local_body = []

        #    for match in ['(.*)\n', '(.*)\.\.\.Más']:
        #        re_body = re.search(match, full_response.find('p', class_ = 'partial_entry').text)

        #        if re_body != None:
        #            local_body.append(re_body.group(1)) # Acá agregar marcador para extracción completa
                    
        #    dict_reviews['response_body'].append(' '.join(local_body))

        #except:
        #    full_response = None
        #    dict_reviews['response_body'].append(None)

        full_response = review.find('div', class_ = 'entry')
        
        try:
            dict_reviews['user_name'].append(review.find('div', class_ = 'info_text pointer_cursor').text)
            
        except Exception as e:
            dict_reviews['user_name'].append('La url {} presenta un error de tipo {}'.format(url['scraping'], e))            
        try:
            dict_reviews['user_reviews'].append(int(re.match('([0-9]+)',
                                                             review.find('span',
                                                                         class_ = 'badgeText').text).group(1)))
        except Exception as e:
            dict_reviews['user_reviews'].append('La url {} presenta un error de tipo {}'.format(url['scraping'], e)) 

        get_votes = lambda useful_votes: n.text if useful_votes != None else 0
        dict_reviews['useful_votes'].append(get_votes(review.find('span', class_ = 'numHlpIn')))
        
        dict_reviews['url'].append(url)

    return dict_reviews