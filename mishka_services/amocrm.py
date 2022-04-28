import requests
from functools import wraps
from pydash import py_
import os


class AmoCRM:
    """Отрефакторить, сделать методы нестатическими."""
    base_url = 'https://{}.amocrm.ru'.format(os.environ['AMOCRM_ACCOUNT_NAME'])
    api_token = os.environ.get('AMOCRM_API_TOKEN')

    attrs_dict = {'PRODUCTS': 165525,
                  'promo_subscribe': 690597,
                  'promo_subscribe_others': 690775,
                  'PRODUCT': 682895,
                  'delivery_status': 690781}

    def __init__(self, email=None, api_token=None, connect=False):
        if email:
            self.email = email
        if api_token:
            self.api_token = api_token

        self.session = requests.Session()
        self.session.headers = {'User-Agent': "Mozilla/5.0 (X11; Linux x86_64)"}
        # AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36 - на всякий случай
        if connect:
            self.update_session()

    def update_session(self):
        self.session.post('https://andreymishkacloud.amocrm.ru/private/api/auth.php?type=json',
                          data={'USER_LOGIN': self.email,
                                'USER_HASH': self.api_token})
        print('session refreshed')
        return self.session

    def get_lead_by_id(self, lead_id):
        """Получает данные заявки по id"""
        return self.get(AmoCRM.base_url + f'/api/v4/leads/{lead_id}').json()

    def get_leads(self, per_page=100, **filter_):
        """Получает сделки постранично."""
        page = 1
        while True:
            r = self.get(self.base_url + '/api/v4/leads',
                         params={'limit': per_page, 'page': page, **{f'filter[{k}][0]': v
                                                                     for k, v in
                                                                     filter_.items()}})

            # Остановка, когда нет контента
            if r.status_code != 200:
                break

            yield r.json()
            page += 1

    def set_custom_fields(self, lead_id, **fields):
        # print(fields)
        body = {'custom_fields_values': [{'field_id': AmoCRM.attrs_dict[k],
                                          'values': [{'value': v}]}
                                         for k, v in fields.items() if v is not None]}
        # print('body is', body)
        return self.patch(AmoCRM.base_url + f'/api/v4/leads/{lead_id}',
                          json=body).json()

    @staticmethod
    def get_custom_value(order, value):
        return py_.get(
            py_.filter(order['custom_fields_values'], {'field_name': value}),
            [0, 'values', 0, 'value'], None)

    @wraps(requests.Session.get)
    def get(self, url, **kwargs):
        r = self.session.get(url, **kwargs)
        if r.status_code == 401:
            self.update_session()
            return self.get(url, **kwargs)
        return self.session.get(url, **kwargs)

    @wraps(requests.Session.post)
    def post(self, url, **kwargs):
        r = self.session.post(url, **kwargs)
        if r.status_code == 401:
            self.update_session()
            return self.post(url, **kwargs)
        return self.session.post(url, **kwargs)

    @wraps(requests.Session.patch)
    def patch(self, url, **kwargs):
        r = self.session.patch(url, **kwargs)
        if r.status_code == 401:
            self.update_session()
            return self.patch(url, **kwargs)
        return self.session.patch(url, **kwargs)

    def extract_lead_pages(self, per_page=50):
        """Получает лиды постранично."""
        page = 0
        while True:
            try:
                page += 1
                yield self.get(self.base_url + '/api/v4/leads',
                               params={'limit': per_page,
                                       'page': page,
                                       'filter[statuses][0][pipeline_id]': 1969807,
                                       'filter[statuses][0][status_id]': 37709317,
                                       'order[created_at]': 'asc'}
                               ).json()['_embedded']['leads']
            except:
                break
