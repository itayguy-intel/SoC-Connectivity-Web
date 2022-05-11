import base64
import datetime
import io
import dash
from dash.dependencies import Input, Output, State
from dash_extensions import Download
import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_html_components as html
import dash_table
import pandas as pd
from smtplib import SMTP
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from typing import Optional
from collections import OrderedDict
BACKEND_PATH = "/nfs/iil/disks/chdk74_regression/performance/sp3ot_backend/soc-connectivity-analyzer"
import argparse
import sys
import os
sys.path.append(BACKEND_PATH)
from src.utils import args_parser, build_soc, build_imsoc
sys.path.pop()


def compute_and_download(n_clicks: int, 
                          df: pd.DataFrame, 
                          root_ip: str, 
                          filename: str) -> [dict, dash.no_update]:
  if df is not None and isinstance(df, pd.DataFrame):
    args = argparse.Namespace(
        config=f"{BACKEND_PATH}/configs/configs.json", 
        input_=df, 
        root_ip=root_ip
    )
    args = args_parser(args)
    soc = build_soc(args)
    if soc.valid_root_ip(root_ip=root_ip):
      imsoc = build_imsoc(soc, args)
      content_stream, _ = imsoc.render_html()
      filename, _ = os.path.splitext(os.path.basename(filename))
      return dict(content=content_stream.decode("utf-8"), 
                  filename=f"{root_ip}-{filename}.svg")
  return dash.no_update


def user_feedback(wwid: str, 
                  reason: str, 
                  comment: str) -> None:
  template = (MAIL_TEMPLATE)
  msg = MIMEMultipart()
  msg['From'] = OWNER_MAIL
  msg['To'] = DEV_MAIN
  msg['Date'] = formatdate(localtime=True)
  msg['Subject'] = MAIL_SUBJECT
  msg.attach(MIMEText(template.format(wwid=wwid, reason=reason, comment=comment), 'html'))
  server = SMTP(SMTP_DOMAIN, SMTP_PORT)
  server.sendmail(OWNER_MAIL, DEV_MAIN, msg.as_string())
  server.close()


def parse_contents(contents: str, 
                    filename: str, 
                    date: int) -> html.Div:
  content_type, content_string = contents.split(',')
  decoded = base64.b64decode(content_string)
  try:
    if 'csv' in filename:
      # a CSV file
      df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
    elif 'xlsx' in filename:
      # an EXCEL file
      df = pd.read_excel(io.BytesIO(decoded))
  except Exception as e:
    print(e)
    return html.Div([f"There was an error processing this file - {filename}."])

  return html.Div([
    html.Span([
      html.H5(filename, style={'padding-left': '2%'}), 
      dash_table.DataTable(data=df.to_dict('records'), 
                            columns=[{'name': i, 'id': i} for i in df.columns])
    ]), 
  ])


OWNER_MAIL = 'alon.cohen@intel.com'
DEV_MAIN = 'alon.cohen@intel.com'
MAIL_TEMPLATE = """
  <hr>
  <strong>WWID: {wwid}</strong>
  <br>
  <strong>Issue: {reason}</strong>
  <br>
  <Strong>Comment:</strong> {comment}
  <hr>
"""
MAIL_SUBJECT = 'SCA Feedback System'
SMTP_DOMAIN = 'smtp.intel.com'
SMTP_PORT = 25
WWID_LEN = 8
WWID_PTRN = '^\d{8}$'


meta_tags = [{'name': 'viewport', 
              'content': 'width=device-width, initial-scale=1.0, shrink-to-fit=no'}]
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css'] + \
                        [dbc.themes.BOOTSTRAP] + \
                        ["basics-style.css", "components-style.css", "sca-style.css"]
app = dash.Dash(__name__, external_stylesheets=external_stylesheets, 
                          meta_tags=meta_tags)
app.title = 'SCA'
app.scripts.config.serve_locally = True
dash_server = app.server
app.layout = html.Div([
  dbc.Col(
    children=[
      html.Div(
        children=[
          dbc.Navbar(
            sticky=True, dark=True, fixed='top', 
            className='NavBar-Header',  
            children=[
              html.Img(className='Image', 
                        id='intel-logo-white', 
                        src=app.get_asset_url('intel-logo-white.png')), 
              html.Div(
                id='app-header-title',
                className='Div-Title', 
                children=[html.H2('SoC Connectivity Analyzer')]
              ),
              html.Span(
                className='Span-Modal',
                children=[
                  html.Div(
                    id='Div-Modal', 
                    children=[
                      dbc.Button(
                        id='Feedback-Modal-Open', n_clicks=0, 
                        children=[dbc.Label('Send Feedback', className='Feedback-Modal-Open-Label')], 
                      ), 
                      dbc.Modal(
                        className='Modal', 
                        children=[
                          dbc.ModalHeader( 
                            className='Modal-Header', 
                            children=[
                              dbc.Label('Feedback', className='Modal-Header-Label'),
                              html.Img(className='Modal-Header-Image', 
                                        id='feedback', 
                                        src=app.get_asset_url('feedback.png')),   
                            ], 
                          ),
                          dbc.ModalBody(
                            children=[
                              html.Span(
                                className='Modal-Body-Span', 
                                children=[
                                  dbc.Form([
                                    dbc.Form(
                                      className='mr-3',
                                      children=[dbc.Input(id='WWID', 
                                                          type='text', 
                                                          autoFocus=False, 
                                                          pattern=WWID_PTRN, 
                                                          placeholder='WWID')],
                                    ),
                                    dbc.Form(
                                      children=[
                                          dcc.RadioItems(
                                            id='Reason',
                                            options=[
                                              {'label': 'Bug', 'value': 'bug'}, 
                                              {'label': 'Enahancement', 'value': 'enhancement'}
                                            ],
                                            value='bug', 
                                            labelStyle={'display': 'block', 'color': 'black'}
                                          ),
                                    ]), 
                                    dbc.Form(
                                      id='Feedback-Comments', 
                                      children=[
                                        dbc.Textarea(
                                          id='Comments', 
                                          spellCheck=True, draggable=False, 
                                          autoFocus=False, required=True, 
                                          placeholder='Comments', style={'width': '100%', 'background': 'rgb(235 243 249)', 'color': 'black', 'font-size': 'inherit'}
                                        ),
                                      ],
                                      className='mr-3',
                                    ),
                                  ]), 
                                ], 
                              ), 
                            ], 
                          ),
                          dbc.ModalFooter(
                            id='Modal-Footer', 
                            children=[
                              dbc.Spinner(
                                type='grow', color='primary',
                                spinner_style={'width': '3rem', 'height': '3rem', 'justify-content': 'left'}, 
                                children=html.Div(id='Spinner-Submit'), 
                              ), 
                              dbc.Button('Send', 
                                id='Feedback-Modal-Close', n_clicks=0, 
                                className='ml-auto'
                              ), 
                            ], 
                          ), 
                        ], 
                        is_open=False
                      ),
                    ], 
                  ), 
                  html.Img(className='Image', 
                            id='sp3ot-logo', 
                            src=app.get_asset_url('sp3ot-logo-2021.png')), 
                ], 
              ), 
            ], 
          ), 
          html.Div(id='output_data_upload', 
            children=[
              html.Span(
                id="press-compute-span", 
                children=[
                  html.Span(
                    id="root-ip-span", 
                    children=[
                      html.Div(
                        children=[
                          html.Button(
                            className=f"Button", 
                            children=html.Img(className='Image-Exe', 
                                              id='exe-icon', 
                                              src=app.get_asset_url('exe-icon.png')), 
                            id=f"button-Compute-and-Download", 
                            style={'background-color': 'aliceblue'}, 
                            n_clicks=0
                          ), 
                        ], 
                        id='button-Compute-and-Download-div'
                      ), 
                      dbc.Input(id='root-ip', 
                                type='text', 
                                autoFocus=False, 
                                placeholder='Root IP', 
                                style={'margin': '0px 4px 4px 4px', 'background': 'aliceblue'}), 
                  ], style={'display': 'inline-flex'}), 
                ], style={'display': 'none', 'margin': '2% 0px 0px 0px'}, 
              ),  
            ], 
          ), 
          Download(id='Download-Loc'), 
          dbc.Navbar(
            sticky=False, dark=True, 
            fixed='bottom', className='NavBar-Header',  
            children=[
              dcc.Upload(
                id='upload_data',
                children=html.Span(
                  id='upload_data_children', 
                  children=['Drag and Drop / ', html.A('Select locally', style={'text-decoration': 'underline'}), ' - SoC Skeleton Architecture File'], 
                ), multiple=False
              ),
            ],
          ),
        ], 
      ), 
    ], 
  ), 
])


@app.callback(
  Output('output_data_upload', 'children'), 
  [
    Input('upload_data', 'contents'), 
  ],
  [
    State('upload_data', 'filename'), 
    State('upload_data', 'last_modified'), 
    State('output_data_upload', 'children'), 
  ], 
)
def upload_data_callback(list_of_contents: str, 
                          list_of_names: str, 
                          list_of_dates: int,  
                          output_data: list) -> list:
  if list_of_contents is not None:
    children = [html.Div(children=[parse_contents(list_of_contents, list_of_names, list_of_dates)])]
    output_data[0]["props"]["style"]["display"] = "block"
    if len(output_data[0]["props"]["children"]) < 2:
      output_data[0]["props"]["children"].extend(children)
    else:
      output_data[0]["props"]["children"][-1] = children[0]
    return output_data
  return dash.no_update


@app.callback(
  [  
    Output('Download-Loc', 'data'), 
    Output('press-compute-span', 'children'), 
  ], 
  [
    Input('button-Compute-and-Download', 'n_clicks'), 
  ], 
  [
    State('button-Compute-and-Download-div', 'children'), 
    State('root-ip', 'value'), 
    State('output_data_upload', 'children'),
    State('press-compute-span', 'children'), 
  ], 
)
def compute_and_download_callback(n_clicks: int, 
                                  button_child: list, 
                                  root_ip: str, 
                                  output_data: list, 
                                  press_span: list) -> list:
  if n_clicks > 0:
    button_child[0]['props']['n_clicks'] = 0
    # from pprint import pprint
    press_span[0]["props"]["children"][1]["props"]["value"] = ""
    filename = output_data[0]["props"]["children"][-1]["props"]["children"][0]["props"]["children"][0]["props"]["children"][0]["props"]["children"]
    data = output_data[0]["props"]["children"][-1]["props"]["children"][0]["props"]["children"][0]["props"]["children"][1]["props"]["data"]
    columns = output_data[0]["props"]["children"][-1]["props"]["children"][0]["props"]["children"][0]["props"]["children"][1]["props"]["columns"]
    datatable = pd.DataFrame(data=data, columns=[c["name"] for c in columns])
    res_download = compute_and_download(n_clicks, datatable, root_ip, filename)
    return res_download, press_span
  return [dash.no_update] * 2


@app.callback(
  [
    Output('Spinner-Submit', 'children'), 
    Output('WWID', 'value'), 
    Output('Reason', 'value'), 
    Output('Comments', 'value'), 
    Output('Div-Modal', 'children'), 
    Output('Modal-Footer', 'children')
  ], 
  [ 
    Input('Feedback-Modal-Open', 'n_clicks'), 
    Input('Feedback-Modal-Close', 'n_clicks'),
  ], 
  [
    State('WWID', 'value'), 
    State('Reason', 'value'), 
    State('Comments', 'value'), 
    State('Div-Modal', 'children'), 
    State('Modal-Footer', 'children')
  ], 
)
def user_feedback_callback(to_open: int, 
                            to_close: int, 
                            wwid: str, 
                            reason: int, 
                            comment: str, 
                            header_modal_oclicks: int, 
                            footer_modal_cclicks: int) -> [dash.no_update, list]:
  if to_open > 0:
    header_modal_oclicks[1]['props']['is_open'] = True
    header_modal_oclicks[0]['props']['n_clicks'] = 0
    return [list(), None, None, None, header_modal_oclicks, footer_modal_cclicks]
  elif to_close > 0:
    if None not in [wwid, reason, comment] and len(wwid) == WWID_LEN and len(comment) > 0:
      user_feedback(wwid, reason, comment)
      header_modal_oclicks[1]['props']['is_open'] = False
      footer_modal_cclicks[1]['props']['n_clicks'] = 0
      return [list(), None, None, None, header_modal_oclicks, footer_modal_cclicks]
  return [dash.no_update] * 6



if __name__ == '__main__':
    # app.run_server(debug=True)
    app.run_server(debug=False)
