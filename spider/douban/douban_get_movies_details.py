# coding: utf8
""" 
@File: douban_get_movies_details.py
@Author: Alice(From Chengdu.China)
@HomePage: https://github.com/AliceEngineerPro
@CreatedTime: 2022/11/8 11:50
"""

from spider.douban.douban_get_movies_url import SpiderDoubanMoviesInit
from spider.public.init_mysqlserver import ConnectMySQL
from spider.public.tb_create import CreateTables
import requests
from bs4 import BeautifulSoup
import re, json, time, random
from spider.public.tb_inster import InsterTables


class SpiderDoubanMoviesDetails(SpiderDoubanMoviesInit):

    def __init__(self):
        super().__init__()
        self.headers.update(
            Host='movie.douban.com',
            Referer='https://movie.douban.com/',
        )
        self.cookies = {
            "ll": "118318",
            "bid": "DcI5Fbd5RAQ",
            "_pk_id.100001.4cf6": "959ba2efabc0eeb9.1666526866.1.1666526866.1666526866.",
            "__yadk_uid": "SUX3h03B1t94hEHCClSpkHgmk1VKG8fV",
            "dbcl2": "264064658:Eb5fqV+OILA",
            "push_noty_num": "0",
            "push_doumail_num": "0",
            "ap_v": "0,6.0",
            "ck": "F6Lh"
        }
        self.proxies = {
            "http": "http://{}".format(requests.get("http://127.0.0.1:5010/get/").json().get("proxy")),
            # "https": "http://{}".format(requests.get("http://127.0.0.1:5010/get/").json().get("proxy")),
        }

    def batch_save_movies_details(self):
        connect = ConnectMySQL().mysql()
        cursor = connect.cursor()
        try:
            sql_msg = "select tb_douban_movies.tb_movies_simple_info.id, tb_douban_movies.tb_movies_simple_info.url " \
                      "from tb_douban_movies.tb_movies_simple_info " \
                      "where tb_douban_movies.tb_movies_simple_info.is_delete = false " \
                      "and tb_douban_movies.tb_movies_simple_info.id > 453 ;"
            cursor.execute(query=sql_msg)
            movies_datas = cursor.fetchall()
            CreateTables().c_tb_movies_used_info()
            for id, url in movies_datas:
                movie_response = requests.request(
                    method='GET',
                    url=url,
                    headers=self.headers,
                    cookies=self.cookies,
                    proxies=self.proxies
                )
                movie_soup = BeautifulSoup(movie_response.content.decode(), 'html.parser')
                # 片名
                name = movie_soup.find('span', {'property': 'v:itemreviewed'}).text.split(' ')[0]
                # 上映年份
                year = movie_soup.find('span', {'class': 'year'}).text.replace('(', '').replace(')', '')
                # 评分
                score = movie_soup.find('strong', {'property': 'v:average'}).text
                # 评价人数
                # votes = movie_soup.find('span', {'property': 'v:votes'}).text
                # 海报url
                try:
                    playbill_link = movie_soup.find('img', {'rel': 'v:image'}).get('src')
                except Exception as error:
                    print(error)
                    playbill_link = ''
                ## 电影信息
                infos = movie_soup.find('div', {'id': 'info'}).text.split('\n')[1:11]
                # 导演
                director = ','.join(infos[0].split(': ')[1].replace(' ', '').split('/'))
                directors = []
                for data in [data for data in director.split(',')]:
                    if '\'' in data:
                        data = ''.join(data.split('\''))
                    directors.append(data)
                directors = ','.join(directors)
                # 编剧
                # scriptwriter = ','.join(infos[1].split(': ')[1].replace(' ', '').split('/'))
                # 主演
                actor = ','.join(infos[2].split(': ')[1].replace(' ', '').split('/'))
                actors = []
                for data in [data for data in actor.split(',')]:
                    if '\'' in data:
                        data = ''.join(data.split('\''))
                    actors.append(data)
                actors = ','.join(actors)
                # 类型
                movies_type = ','.join(infos[3].split(': ')[1].replace(' ', '').split('/'))
                # 国家/地区
                area = ','.join(infos[4].split(': ')[1].replace(' ', '').split('/'))
                # 语言
                lang = ','.join(infos[5].split(': ')[1].replace(' ', '').split('/'))
                # 上映日期
                release_time = ','.join(infos[6].split(': ')[1].replace(' ', '').split('/'))
                # 电影时长
                movie_long = infos[7].split(': ')[1].replace(' ', '')
                # 短评数量
                short_review_num = re.findall(r'\d+', movie_soup.find('div', {'class': 'mod-hd'}).text.split('\n')[9].replace(' ', ''))[0]
                # 星级占比
                star_compare = ','.join(re.findall(r'\d+.\d+%', ''.join(
                    data for data in movie_soup.find('div', {'class': 'ratings-on-weight'}).text.replace(' ', '').split('\n')
                )))
                # 电影简介
                movie_summary = re.findall(f'[^\u3000]+', ''.join(
                    data for data in movie_soup.find('span', {'property': 'v:summary'}).text.replace(' ', '').split('\n')
                ))[0]
                if '\'' in movie_summary or '\"' in movie_summary:
                    movie_summary = ''.join(movie_summary.split('\''))
                # 电影短评
                movie_review_data = []
                movie_review = [data.text.replace(' ', '').split('\n') for data in movie_soup.findAll('div', {'class': 'comment'})]
                movie_review_user = []
                movie_review_star = re.findall(r'\d+', ''.join([data.get('class')[0] for data in (movie_soup.findAll('span', {'class': 'rating'}))]))
                movie_review_time = []
                movie_review_comment = []
                for data in movie_review:
                    for data_data in data:
                        if data_data == '':
                            data.remove(data_data)
                for data in movie_review:
                    user_msg = ''.join(re.findall(f'[\u4E00-\u9FA5A-Za-z0-9_]+', data[2]))
                    if user_msg is None:
                        user_msg = 'Anonymous'
                    movie_review_user.append(user_msg)
                    movie_review_time.append(data[4])
                    movie_review_comment.append(''.join(re.findall(f'[^\'\"]+', data[8])))
                for user, stat, p_time, comment in zip(movie_review_user, movie_review_star, movie_review_time, movie_review_comment):
                    # movie_review_data.append(json.dumps({'user': f'{user}', 'star': f'{stat}', 'time': f'{time}', 'comment': f'{comment}'}, ensure_ascii=False))
                    movie_review_data.append({'user': f'{user}', 'star': f'{stat}', 'time': f'{p_time}', 'comment': f'{comment}'})
                # 相关图片链接
                try:
                    about_img = ','.join(
                        [data.get('src') for data in [data.findAll('img') for data in movie_soup.findAll('ul', {'class': 'related-pic-bd'})][0]]
                    )
                except Exception as error:
                    print(error)
                    about_img = ''
                # 相关视频链接
                try:
                    about_avi = movie_soup.find('a', {'class': 'related-pic-video'}).get('href')
                except Exception as error:
                    print(error)
                    about_avi = ''
                InsterTables().insert_tb_movies_used_info(
                    directors=directors,
                    score=score,
                    title=name,
                    actors=actors,
                    playbill_link=playbill_link,
                    detail_link=url,
                    release_year=year,
                    movie_type=movies_type,
                    movie_country=area,
                    movie_lang=lang,
                    release_time=release_time,
                    movie_long=movie_long,
                    short_review_num=short_review_num,
                    star_compare=star_compare,
                    summary=movie_summary,
                    movie_review=movie_review_data,
                    about_img_url=about_img,
                    movie_url=about_avi
                )
                delay_time = random.randint(1, 5)
                print(delay_time)
                time.sleep(delay_time)
        except Exception as error:
            print(error)
            exit(1)