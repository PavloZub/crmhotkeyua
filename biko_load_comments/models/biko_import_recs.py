from odoo import models, fields
import base64
import json
from datetime import datetime
import requests
import csv
import yaml
import os

B24_URI = ''
RESULT_FILE = ''
SOURCE_FILE = ''
CHARSET = ''

relpath = os.path.dirname(os.path.realpath(__file__))
# get settings from YAML file
with open(relpath+'/settings.yaml', 'r', encoding='UTF_8') as yaml_file:
    objects = yaml.load(yaml_file, yaml.Loader)
    B24_URI = objects['B24_WEBHOOK'] if objects['B24_WEBHOOK'][-1] != '/' else objects['B24_WEBHOOK'][0:-1]
    RESULT_FILE = objects['RESULT_FILE']
    SOURCE_FILE = objects['SOURCE_FILE']
    CHARSET = objects['CHARSET']



class ImportRecs(models.TransientModel):
    _name = 'biko.import.recs'

    file = fields.Binary(string='File name')
    file_name = fields.Char()
    charset = fields.Selection(selection=[('UTF-8', 'UTF-8'), ('windows-1251', 'windows-1251')], string='Charset')

    def hello(self):
        try:
            with open(SOURCE_FILE, 'r', encoding=CHARSET) as file:

                deals = dict()
                csv_reader = csv.reader(file, delimiter=';')

                firstline = True

                for line in csv_reader:

                    if firstline:
                        firstline = False
                        continue

                    deals.update({line[0]: {'id': line[0], 'external_id': line[1], 'comments': dict()}})

                return deals

        except csv.Error as err:
            print(f'Error reading CSV file: {err}')
            return dict()
        except UnicodeDecodeError as err:
            print(f'Error reading CSV file: {err}')
            return dict()
        except IOError as err:
            print('Error working with file ' + SOURCE_FILE)
            print(err)

    def get_deals(self):

        try:
            with open(SOURCE_FILE, 'r', encoding=CHARSET) as file:

                deals = dict()
                csv_reader = csv.reader(file, delimiter=';')

                firstline = True

                for line in csv_reader:

                    if firstline:
                        firstline = False
                        continue

                    deals.update({line[0]: {'id': line[0], 'external_id': line[1], 'comments': dict()}})

                return deals

        except csv.Error as err:
            print(f'Error reading CSV file: {err}')
            return dict()
        except UnicodeDecodeError as err:
            print(f'Error reading CSV file: {err}')
            return dict()
        except IOError as err:
            print('Error working with file ' + SOURCE_FILE)
            print(err)

    def get_comments(self, deals):

        deals_with_files = {}

        templ_start = '{"halt":0,"cmd": {'
        templ_end = '}}'

        i = 0
        packages = []
        req_str = ""

        for deal in deals.values():

            req_str += f'"{deal["id"]}":"crm.timeline.comment.list?filter[ENTITY_ID]={deal["id"]}&filter[ENTITY_TYPE]=deal",'
            if ((i + 1) % 50 == 0) or (i == len(deals) - 1):
                json_res = json.loads(templ_start + req_str[0:-1] + templ_end)
                packages.append(json_res)
                req_str = ""
            i += 1

        for batch in packages:
            req = requests.post(f'{B24_URI}/batch', json=batch)

            if req.status_code != 200:
                print('Error accessing to B24!')
                continue

            resp_json = req.json()
            res_errors = resp_json['result']['result_error']
            res_comments = resp_json['result']['result']

            if len(res_errors) > 0:
                for key, val in res_errors.items():
                    print(key, ':', val['error_description'])

            if len(res_comments) > 0:
                for deal_id, comments in res_comments.items():
                    deal = deals[deal_id]
                    for comment_line in comments:
                        deal['comments'].update({comment_line['ID']: comment_line})
                        if 'FILES' in comment_line.keys():
                            for file in comment_line['FILES'].keys():
                                deals_with_files.update({file: {'deal_id': deal_id, 'comment_id': comment_line['ID']}})

        return [deals, deals_with_files]

    def action_import_records(self):
        # deals = self.get_deals()
        deals = self.hello()
        if len(deals) == 0:
            print('Error while loading deals!')
            return

        deals_res, deals_with_files = self.get_comments(deals)

        # for i_id, i_comments in deals_res.items():
        #     if i_comments['comments']:
        #         for c_id, c_comments in i_comments['comments'].items():
        #              if c_comments['COMMENT']=="":
        #                 print('empty')

        # data = base64.b64decode(self.file)
        # data = data.decode(self.charset)
        # jsdata = json.loads(data)

        env_deals = self.env['crm.lead'].env

        for deal in deals_res.values():

            comments_list = deal['comments']
            # self.env.ref
            if not comments_list:
                continue

            external_id = deal['external_id']
            id = deal['id']
            # user_id = self.env['res.users'].search(['id', '=', 11])
            # record = env_deals.ref('__import__.' + external_id)
            record = env_deals.ref(external_id)
            #
            if record:
                for comment in comments_list.values():
                    date_time = datetime.fromisoformat(comment['CREATED']).replace(tzinfo=None)
                    msg = comment['COMMENT']
                    f_attachments = []
                    if ('FILES' in comment.keys()):
                        for c_file in comment['FILES'].values():
                            f_name = c_file['name']
                            req = requests.get(c_file['urlDownload'])
                            f_attachments.append((f_name, req.content))
                    message_rec = record.message_post(body=msg, message_type='comment', attachments=f_attachments)
                    message_rec['date'] = date_time

        # data = base64.b64decode(self.file)
        # data = data.decode(self.charset)
        # jsdata = json.loads(data)
        #
        # env_deals = self.env['crm.lead'].env
        #
        # for deal in jsdata.values():
        #
        #     comments_list = deal['comments']
        #     # self.env.ref
        #     if not comments_list:
        #         continue
        #
        #     external_id = deal['external_id']
        #     id = deal['id']
        #     user_id = self.env['res.users'].search(['id', '=', 11])
        #     # record = env_deals.ref('__import__.' + external_id)
        #     record = env_deals.ref(external_id)
        #
        #     if record:
        #         for comment in comments_list.values():
        #             date_time = datetime.fromisoformat(comment['CREATED']).replace(tzinfo=None)
        #             msg = comment['COMMENT']
        #             f_attachments = []
        #             if ('FILES' in comment.keys()):
        #                 for c_file in comment['FILES'].values():
        #                     f_name = c_file['name']
        #                     req = requests.get(c_file['urlDownload'])
        #                     f_attachments.append((f_name, req.content))
        #             message_rec = record.message_post(body=msg, message_type='comment', attachments=f_attachments)
        #             message_rec['date'] = date_time
