import pandas as pd
import numpy as np
import requests
import datetime
import json
from pandas.io.json import json_normalize
import xlrd
import plotly.express as px 
import plotly.graph_objects as go

import dash  
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import dash_table_experiments as dt
import dash_table


def decode_event_group(coded_value, event_group):
    '''
    Decode arm names, example - EG000 to 'Dupilumab 300 mg qw'
    '''
    decoded_value = event_group[event_group.EventGroupId==coded_value]['EventGroupTitle'].values[0]
    if not decoded_value:
        decoded_value = coded_value
    return decoded_value

def get_oae(nctid):
    # Get CT.gov data on the NCTID
    URL = f'https://clinicaltrials.gov/api/query/full_studies?expr={nctid}&max_rnk=1&fmt=JSON'
    r = requests.get(URL)
    j = json.loads(r.content)
    # Other AE data
    tt = j['FullStudiesResponse']['FullStudies'][0]['Study']['ResultsSection']['AdverseEventsModule']['OtherEventList']['OtherEvent']
    event_groups = pd.json_normalize(j['FullStudiesResponse']['FullStudies'][0]['Study']['ResultsSection']['AdverseEventsModule']['EventGroupList']['EventGroup'])
    # convert into tabular format
    tt2 = pd.json_normalize(tt,
              ['OtherEventStatsList','OtherEventStats'],
              ['OtherEventTerm', 'OtherEventOrganSystem'],
              errors='ignore')
    # convert into multi-indexed column
    #if tt[0]['OtherEventStatsList']['OtherEventStats'][0]['OtherEventStatsNumEvents']:
    try:
        tt3 = tt2.pivot(columns='OtherEventStatsGroupId',
        values=['OtherEventStatsNumAffected','OtherEventStatsNumEvents','OtherEventStatsNumAtRisk'],
        index='OtherEventTerm')
        tt3.rename(columns={'OtherEventStatsNumEvents':'Events'}, inplace=True, level=0)
    except KeyError:
        tt3 = tt2.pivot(columns='OtherEventStatsGroupId',
        values=['OtherEventStatsNumAffected','OtherEventStatsNumAtRisk'],
        index='OtherEventTerm')
    tt3.rename(columns=lambda x: decode_event_group(x,event_groups), inplace=True, level=1)
    tt3.rename(columns={'OtherEventStatsNumAffected':'Subjects','OtherEventStatsNumAtRisk':'Total_Subjects'}, inplace=True, level=0)
    return(tt3)

def get_sae(nctid):
    # Get CT.gov data on the NCTID
    URL = f'https://clinicaltrials.gov/api/query/full_studies?expr={nctid}&max_rnk=1&fmt=JSON'
    r = requests.get(URL)
    j = json.loads(r.content)
    # Other AE data
    tt = j['FullStudiesResponse']['FullStudies'][0]['Study']['ResultsSection']['AdverseEventsModule']['SeriousEventList']['SeriousEvent']
    event_groups = pd.json_normalize(j['FullStudiesResponse']['FullStudies'][0]['Study']['ResultsSection']['AdverseEventsModule']['EventGroupList']['EventGroup'])
    # convert into tabular format
    tt2 = pd.json_normalize(tt,
              ['SeriousEventStatsList','SeriousEventStats'],
              ['SeriousEventTerm', 'SeriousEventOrganSystem'],
              errors='ignore')
    # convert into multi-indexed column
    try:
        tt3 = tt2.pivot(columns='SeriousEventStatsGroupId',
                    values=['SeriousEventStatsNumAffected','SeriousEventStatsNumEvents','SeriousEventStatsNumAtRisk'],
                    index='SeriousEventTerm')
        tt3.rename(columns={'SeriousEventStatsNumEvents':'Events'}, inplace=True, level=0)
    except KeyError:
        tt3 = tt2.pivot(columns='SeriousEventStatsGroupId',
                    values=['SeriousEventStatsNumAffected','SeriousEventStatsNumAtRisk'],
                    index='SeriousEventTerm')
    tt3.rename(columns=lambda x: decode_event_group(x,event_groups), inplace=True, level=1)
    tt3.rename(columns={'SeriousEventStatsNumAffected':'Subjects','SeriousEventStatsNumAtRisk':'Total_Subjects'}, inplace=True, level=0)
    return(tt3)

def get_ae_summary(nctid):
    # Get CT.gov data on the NCTID
    URL = f'https://clinicaltrials.gov/api/query/full_studies?expr={nctid}&max_rnk=1&fmt=JSON'
    r = requests.get(URL)
    j = json.loads(r.content)
    tt = pd.json_normalize(j['FullStudiesResponse']['FullStudies'][0]['Study']['ResultsSection']['AdverseEventsModule']['EventGroupList']['EventGroup'])
    for cols in ['EventGroupSeriousNumAffected', 'EventGroupSeriousNumAtRisk', 'EventGroupOtherNumAffected']:
        tt[cols] = tt[cols].apply(pd.to_numeric, errors='coerce')
    return tt.sum(axis = 0, skipna = True, numeric_only = True) 




app = dash.Dash(__name__)

# App layout
app.layout = html.Div([

    html.H1("Get Adverse Event Data", style={'text-align': 'center'}),

    html.Div([
        html.Br(),
        dcc.Input(id="trial1", type="text", placeholder="Enter the trial id", debounce =True),
        html.Br(),
    ]),
    html.Br(),
    #html.Div(id='blank1', style={'width': '6%', 'display': 'inline-block'}),    
    html.Div(id='output-ae-summary-total', style={'width': '70%', 'display': 'inline-block'}),
    html.Div(id='blank2', style={'width': '3%', 'display': 'inline-block'}),    
    html.Div(id='output-ae-summary', style={'width': '27%', 'display': 'inline-block'} ),
    #html.Div(id='blank3', style={'width': '5%', 'display': 'inline-block'}),    
    html.Br(), html.Br(),
    
    dcc.Tabs([
        dcc.Tab(label='Serious Adverse Event (Subject Count)', children=[
            html.Div(id='blank4', style={'width': '7%', 'display': 'inline-block'}),    
            html.Div(id='output-sae-subs', style={'width': '85%', 'display': 'inline-block'}),
        ]),
     
        dcc.Tab(label='Other Adverse Event (Subject Count)', children=[
            html.Div(id='blank5', style={'width': '7%', 'display': 'inline-block'}),    
            html.Div(id='output-oae-subs', style={'width': '85%', 'display': 'inline-block'}),
        ]),
        dcc.Tab(label='Serious Adverse Event (Event Count)', children=[
            
        ]),
        dcc.Tab(label='Other Adverse Event (Event Count)', children=[
            
        ])
     ]),
    
    html.Br(),
])


# ------------------------------------------------------------------------------
# Connect the data with Dash Components
@app.callback(
    [dash.dependencies.Output('output-sae-subs', 'children'),
     dash.dependencies.Output('output-oae-subs', 'children'),
     dash.dependencies.Output('output-ae-summary', 'children'),
     dash.dependencies.Output('output-ae-summary-total', 'children')],
    Input(component_id='trial1', component_property='value')
)


# update logic
def update_graph(trial):
    print(trial)  
    
    trials1 = trial.split(',')
    trials2 = trial.split(' ')
    
    #######################
    # multi- trial input
    #######################
    if ((len(trials1) > 1) | (len(trials2) > 1)):
        if len(trials1)==1:
            trials1 = trials2
        res_list = []
        
        # Get summary for every trial
        for trial in trials1:
            try:
                ae_sum = get_ae_summary(trial)
            except (KeyError, RuntimeError, TypeError, NameError):
                # if results are not present just get the subject count
                try:
                    URL = f'https://clinicaltrials.gov/api/query/full_studies?expr={trial}&max_rnk=1&fmt=JSON'
                    r = requests.get(URL)
                    j = json.loads(r.content)
                    sub_count = int(j['FullStudiesResponse']['FullStudies'][0]['Study']['ProtocolSection']['DesignModule']['EnrollmentInfo']['EnrollmentCount'])
                # if NCTID is invalid
                except (KeyError, RuntimeError, TypeError, NameError):
                    sub_count = 'NA'
                    
                res_list.append([trial,
                            'NA', 
                            'NA',
                            sub_count,
                            'NA',
                            'NA', 
                            'NA'
                            ])
                continue
                
            sae_subs_uni = ae_sum['EventGroupSeriousNumAffected']
            sae_risk = ae_sum['EventGroupSeriousNumAtRisk']
            oae_subs_uni = ae_sum['EventGroupOtherNumAffected']
            oae_risk = ae_sum['EventGroupSeriousNumAtRisk'] 
            flag = 0
            if sae_subs_uni != 0:
                sae = get_sae(trial)
                sae_subs = sae['Subjects']  
                study_arm_count = int(sae_subs.shape[1])
                flag = 1
                sae_term_count = int(sae_subs.shape[0])
            else:
                study_arm_count = 0
                sae_term_count = 0
            if oae_subs_uni != 0:
                oae = get_oae(trial)
                oae_subs = oae['Subjects']  
                study_arm_count = int(oae_subs.shape[1])
                oae_term_count = int(oae_subs.shape[0])
            else:
                oae_term_count = 0
                if flag == 0:
                    study_arm_count = 0
            
            res_list.append([trial,
                            (sae_term_count+oae_term_count), 
                            (sae_subs_uni+oae_subs_uni),
                            oae_risk,
                            round(100*((sae_subs_uni+oae_subs_uni)/oae_risk),3),
                            round((oae_risk/(sae_term_count+oae_term_count)),4), 
                            study_arm_count
                            ])
             
        ae_summary_total = pd.DataFrame(res_list, columns=['NCTID',
                         'AE Count', 
                         'Subjects with AE',
                         'Subjects in study',
                         '% subjects w AE',
                         'Subject per AE', 
                         'Study Arm Count'])
        
        return(html.H4('Multiple inputs detected, SAE table available only for single trial id input', style={'text-align': 'center'}),
               html.H4('Multiple inputs detected, OAE table available only for single trial id input', style={'text-align': 'center'}),
               " ",
               html.Div([
                    html.H2(' ', style={'text-align': 'center'}),
                    dash_table.DataTable(
                        id='table4',
                        columns=[{"name": i, "id": i} for i in ae_summary_total.columns],
                        data=ae_summary_total.to_dict("rows"),
                        export_format="csv",
                        export_headers="display",
                        style_cell={
                        'minWidth': '100px', 'width': '100px', 'maxWidth': '100px',
                        'height': '40px',
                        'textAlign': 'left'}),
                   html.H2(' ', style={'text-align': 'center'}),
                    ])
                )
#         print("Multiple Trials detected")
#         return(html.H4('Multiple Trials detected', style={'text-align': 'center'}),"none","none","none")
    
    #######################
    # Single Trial input
    #######################
    else:
    
        # Part 0 - Check if the results data exists
        try:
            ae_sum = get_ae_summary(trial)
        except (KeyError, RuntimeError, TypeError, NameError):
            return(html.H3('NA', style={'text-align': 'center'}),
               html.H3('NA', style={'text-align': 'center'}),
               " ",
               html.H4('Results data not available', style={'text-align': 'center'}),
                )
        
        # Part 1 - Get the summary
        sae_subs_uni = ae_sum['EventGroupSeriousNumAffected']
        sae_risk = ae_sum['EventGroupSeriousNumAtRisk']
        oae_subs_uni = ae_sum['EventGroupOtherNumAffected']
        oae_risk = ae_sum['EventGroupSeriousNumAtRisk']   

        # Part 2 - Get and format the Serious Adverse Events data
        if sae_subs_uni != 0:
            sae = get_sae(trial)
            sae_subs = sae['Subjects']  
            study_arm_count = int(sae_subs.shape[1])
            for cols in sae_subs.columns:
                sae_subs[cols] = sae_subs[cols].apply(pd.to_numeric, errors='coerce')            
            # Add a row for total number of subjects with SAE or OAE in each arm (column)
            sae_subs = sae_subs.append(sae_subs.sum().rename('Total'))
            sae_subs.reset_index(inplace=True)        
            # Get total number of subjects with SAE or OAE
            total_sae = sae_subs[sae_subs.SeriousEventTerm=="Total"].sum(axis = 1, skipna = True)
            sae_subs.loc[:,'Total'] = sae_subs.sum(axis=1, numeric_only = True)         
            # Move "total" row at the first position
            sae_subs = pd.concat([sae_subs[sae_subs.SeriousEventTerm=="Total"],sae_subs[sae_subs.SeriousEventTerm!="Total"]])        
            sae_subs.loc[:,'Percent'] = round(100*(sae_subs.Total/sae_risk),3)
            sae_term_count = int(sae_subs.shape[0])-1
            sae_sub_percent = str(round(100*(sae_subs_uni/sae_risk), 2))
            # Return object
            sae_tab = dash_table.DataTable(
                            id='table',
                            columns=[{"name": i, "id": i} for i in sae_subs.columns],
                            data=sae_subs.to_dict("rows"),
                            filter_action="native",
                            export_format="csv",
                            export_headers="display",
                            style_cell={'width': '300px',
                            'height': '60px',
                            'textAlign': 'left'},
                            style_data_conditional=[{
                                'if': {'row_index': 'odd'},
                                'backgroundColor': 'rgb(248, 248, 248)'
                            }],
                            style_header={
                                'backgroundColor': 'rgb(230, 230, 230)',
                                'fontWeight': 'bold'
                            })
        else:
            print("There are 0 SAEs")
            sae_term_count = 0
            sae_sub_percent = 0
            sae_tab = html.H2("There are 0 subjects with Serious Adverse Events", style={'text-align': 'center'})

        # Part 3 - Get and format the Other Adverse Events data
        if oae_subs_uni != 0:    
            oae = get_oae(trial)
            oae_subs = oae['Subjects']    
            study_arm_count = int(oae_subs.shape[1])
            for cols in oae_subs.columns:
                oae_subs[cols] = oae_subs[cols].apply(pd.to_numeric, errors='coerce')
            oae_subs = oae_subs.append(oae_subs.sum().rename('Total'))
            oae_subs.reset_index(inplace=True)
            total_oae = oae_subs[oae_subs.OtherEventTerm=="Total"].sum(axis = 1, skipna = True)
            oae_subs.loc[:,'Total'] = oae_subs.sum(axis=1, numeric_only = True)
            oae_subs = pd.concat([oae_subs[oae_subs.OtherEventTerm=="Total"],oae_subs[oae_subs.OtherEventTerm!="Total"]])
            oae_subs.loc[:,'Percent'] = round(100*(oae_subs.Total/oae_risk),3)
            oae_term_count = int(oae_subs.shape[0])-1
            oae_sub_percent = str(round(100*(oae_subs_uni/oae_risk), 2))
            # Return object
            oae_tab=dash_table.DataTable(
                        id='table2',
                        columns=[{"name": i, "id": i} for i in oae_subs.columns],
                        data=oae_subs.to_dict("rows"),
                        filter_action="native",
                        export_format="csv",
                        export_headers="display",
                        style_cell={'width': '300px',
                        'height': '60px',
                        'textAlign': 'left'},
                        style_data_conditional=[{
                            'if': {'row_index': 'odd'},
                            'backgroundColor': 'rgb(248, 248, 248)'
                        }],
                        style_header={
                            'backgroundColor': 'rgb(230, 230, 230)',
                            'fontWeight': 'bold'
                        })
        else:
            print("There are 0 OAEs")   
            oae_term_count = 0
            oae_sub_percent = 0
            oae_tab = html.H1("There are 0 subjects with Serious Adverse Events", style={'text-align': 'center'})
            study_arm_count = 0

        d = {'Group': ['SAE', 'OAE'], 
             'Subjects': [sae_subs_uni, oae_subs_uni],
             'Percentage': [sae_sub_percent, oae_sub_percent],
             #'Subjects At Risk': [sae_risk, oae_risk], 
             'AE Count': [sae_term_count, oae_term_count],
             }

        ae_summary_individual = pd.DataFrame(data=d)

        d2 = {'AE Count': [(sae_term_count+oae_term_count)] , 
             'Subjects with AE': [(sae_subs_uni+oae_subs_uni)],
             'Subjects in study': [oae_risk],
             '% subjects w AE': [ round(100*((sae_subs_uni+oae_subs_uni)/oae_risk),3)],
             'Subject per AE': [round((oae_risk/(sae_term_count+oae_term_count)),4)], 
             'Study Arm Count': [study_arm_count],
             }

        ae_summary_total = pd.DataFrame(data=d2)

        return html.Div([
            html.H4(' ', style={'text-align': 'center'}),
            sae_tab
        ]), html.Div([
            html.H4(' ', style={'text-align': 'center'}),
            oae_tab
        ]), html.Div([
            dash_table.DataTable(
                id='table3',
                columns=[{"name": i, "id": i} for i in ae_summary_individual.columns],
                data=ae_summary_individual.to_dict("rows"),
                style_cell={
                'minWidth': '100px', 'width': '100px', 'maxWidth': '100px',
                'height': '40px',
                'textAlign': 'left'})
        ]), html.Div([
            #html.H5('Study Summary', style={'text-align': 'center'}),
            dash_table.DataTable(
                id='table4',
                columns=[{"name": i, "id": i} for i in ae_summary_total.columns],
                data=ae_summary_total.to_dict("rows"),
                style_cell={
                'minWidth': '100px', 'width': '100px', 'maxWidth': '100px',
                'height': '40px',
                'textAlign': 'left'})
        ])


# ------------------------------------------------------------------------------
if __name__ == '__main__':
    app.run_server(debug=False)