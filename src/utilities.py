# -*- coding: utf-8 -*-
"""
Created on Wed Apr 20 13:51:07 2022

@author: pmayaduque
"""
from classes import Solar, Eolic, Diesel, Battery
import pandas as pd
import requests
import json 
import numpy as np
import math


def read_data(demand_filepath, 
              forecast_filepath,
              units_filepath):
    
    forecast_df = pd.read_csv(forecast_filepath)
    demand_df = pd.read_csv(demand_filepath)
    try:
        generators_data =  requests.get(units_filepath)
        generators_data = json.loads(generators_data.text)
    except:
        f = open(units_filepath)
        generators_data = json.load(f)
    
    generators = generators_data['generators']
    batteries = generators_data['batteries']
    
    return demand_df, forecast_df, generators, batteries

def create_objects(generators, batteries):
    # Create generators and batteries
    generators_dict = {}
    for k in generators:
      if k['tec'] == 'S':
        obj_aux = Solar(*k.values())
      elif k['tec'] == 'W':
        obj_aux = Eolic(*k.values())
      elif k['tec'] == 'D':
        obj_aux = Diesel(*k.values())      
      generators_dict[k['id_gen']] = obj_aux
      
    batteries_dict = {}
    for l in batteries:
        obj_aux = Battery(*l.values())
        batteries_dict[l['id_bat']] = obj_aux
        
    # Create technologies list
    technologies_dict = dict()
    for bat in batteries_dict.values(): 
      if not (bat.tec in technologies_dict.keys()):
        technologies_dict[bat.tec] = set()
        technologies_dict[bat.tec].add(bat.alt)
      else:
        technologies_dict[bat.tec].add(bat.alt)
    for gen in generators_dict.values(): 
      if not (gen.tec in technologies_dict.keys()):
        technologies_dict[gen.tec] = set()
        technologies_dict[gen.tec].add(gen.alt)
      else:
        technologies_dict[gen.tec].add(gen.alt)

    # Creates renewables dict
    renewables_dict = dict()
    for gen in generators_dict.values(): 
        if gen.tec == 'S' or gen.tec == 'W': #or gen.tec = 'H'
          if not (gen.tec in renewables_dict.keys()):
              renewables_dict[gen.tec] = set()
              renewables_dict[gen.tec].add(gen.alt)
          else:
              renewables_dict[gen.tec].add(gen.alt)
              
    return generators_dict, batteries_dict, technologies_dict, renewables_dict

# TODO: it might not be needed
def calculate_size(demand_df, 
                   forecast_df,
                   generators_dict):
    
    max_demand =  max(demand_df.max())
    max_rad = max(forecast_df['Rt'])
    max_wind = max(forecast_df['Wt'])
    l_min, l_max = 2, 2
    g_max = 1.1 * max_demand
    g_min = 0.3 * max_demand
    nn = len(forecast_df)
    demand_d = np.zeros(nn)
    rad_p = np.zeros(nn)
    wind_p = 0
    wind_p = pd.DataFrame.mean(forecast_df['Wt'])
    demand_d = np.zeros(nn)
    rad_p = np.ones(nn)
    for val in range(len(forecast_df)):
         demand_d[val] = demand_df['demand'].values[val]
         rad_p[val] = forecast_df['Rt'].values[val]
    rad_s = sum(i for i in rad_p)
    h_p = rad_s/1000 
    l_min, l_max = 2, 2
    g_max = 0.8*max_demand
    Size = {}
    for gen in generators_dict.values():
          if gen.tec == 'S':
             Size[gen.id_gen] = math.ceil((0.1*sum(i for i in demand_d))/(gen.G_test * h_p))
          elif gen.tec == 'W':
              f_plan = wind_p/gen.w_a
              Size[gen.id_gen] = math.ceil((0.1*sum(i for i in demand_d))/(nn*f_plan*20))
          elif gen.tec == 'D':
              Size[gen.id_gen] =  g_max  #para no calcular max_demand siempre          
    return Size

def generation(gen, t, forecast_df, Size):

      if gen.tec == 'S':
         g_rule = Size * gen.ef * gen.G_test * (forecast_df['Rt'][t]/gen.R_test) 
         #falta considerar área del panel
      elif gen.tec == 'W':
          if forecast_df['Wt'][t] < gen.w_min:
              g_rule = 0
          elif forecast_df['Wt'][t] < gen.w_a:
              g_rule =  (Size * (1/2) * gen.p * gen.s * (forecast_df['Wt'][t]**3) * gen.ef * gen.n )/1000
              #p en otros papers es densidad del aíre, preguntar a Mateo, por qué divide por 1000?
          elif forecast_df['Wt'][t] <= gen.w_max:
              g_rule = (Size * (1/2) * gen.p * gen.s * (gen.w_a**3) * gen.ef * gen.n )/1000
          else:
              g_rule = 0
      elif gen.tec == 'D':
         g_rule =  Size
      return g_rule