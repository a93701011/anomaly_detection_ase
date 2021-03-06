import pandas as pd
import pyodbc
import os
import psutil

txn_time_start = '2020-01-01'
txn_time_end = '2020-01-02'
to_csv ='data_0101_0102'

#input parameter
#txn_time_start = str(sys.argv[1])
#txn_time_end = str(sys.argv[1])
#to_csv = str(sys.argv[1])


server = 'fdcdwserver.database.windows.net' 
database = 'fdcdb' 
username = 'aseadmin' 
password = 'p@ssw0rd' 
                         
sql_conn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER='+server+';DATABASE='+database+';UID='+username+';PWD='+ password)
query = "SELECT [TXN_TIME],[LOTID],[YEARCODE],[RECIPE],[QTY],[PACKAGECODE],[DEVICE],[LC],[CUSTOMER],[MCID],[BONDHEAD],[KEY],[CPUTICK],[FORCE],[TEMP],[BHZ] FROM [dbo].[fdc_data_master] where TXN_TIME > '{}' and TXN_TIME<'{}' and LEFT(MCID_SHORT,1) = 'K' and [ScoredLabels] = 1".format(txn_time_start, txn_time_end)
print(query)

data = pd.read_sql(query, sql_conn)

print('data size {}'.format(data.shape))

process = psutil.Process(os.getpid())
print(process.memory_info().rss/1024/1024/1024) # in GB

data['datetime'] = pd.to_datetime(data.TXN_TIME,format = '%Y%m%d %H:%M:%S')
data['datetimekey'] = data.datetime.apply(lambda x : x.strftime('%Y%m%d%H%M%S'))
data['day'] = data.datetime.apply(lambda x : x.strftime('%Y%m%d'))
data['CPUTICK']=data['CPUTICK'].apply(lambda x:x.strip())
data['BHZ']=data['BHZ'].apply(lambda x:str(x).strip())
data['FORCE']=data['FORCE'].apply(lambda x:str(x).strip())
data['TEMP']=data['TEMP'].apply(lambda x:str(x).strip())
data['RECIPE']=data['RECIPE'].apply(lambda x : x.strip())
data['datetimekey']= data['datetimekey'].apply(lambda x : x.strip())
data['MCID'] = data['MCID'].apply(lambda x : x.strip())
data['BONDHEAD'] = data['BONDHEAD'].apply(lambda x : x.strip())
data['CPUTICK']=data['CPUTICK'].str[:-1]
data['BHZ']=data['BHZ'].str[:-1]
data['FORCE']=data['FORCE'].str[:-1]
data['TEMP']=data['TEMP'].str[:-1]
data['Key'] = data['datetimekey'] +data['MCID']+data['BONDHEAD']
data['CPUTICK'] = data['CPUTICK'].str.split('|')
data['BHZ'] = data['BHZ'].str.split('|')
data['FORCE'] = data['FORCE'].str.split('|')
data['TEMP'] = data['TEMP'].str.split('|')

data.dropna(inplace = True)
print('transfer to row...')
data.reset_index(drop=True, inplace=True)
#data_all = data
df_all = []
for i in range(data.shape[0]):
    CPUTICK = pd.DataFrame(data['CPUTICK'][i])
    BHZ = pd.DataFrame(data['BHZ'][i])
    FORCE = pd.DataFrame(data['FORCE'][i])
    TEMP = pd.DataFrame(data['TEMP'][i])
    df = pd.concat([CPUTICK,BHZ,FORCE,TEMP], axis = 1 )
    df['TXN_TIME'] = data['TXN_TIME'][i]
    df['BONDHEAD'] = data['BONDHEAD'][i]
    df['MCID'] = data['MCID'][i]
    df['RECIPE'] =  data['RECIPE']
    df['Key'] =data['Key'][i]
    df['row_num'] = list(range(1,len(data['CPUTICK'][i])+1))
    #df['Label'] = 0
    df['datetime'] = data['datetime'][i]
    #data.reset_index(inplace=True, drop = True)
    df_all.append(df)
df_row = pd.concat(df_all, axis = 0)

del df_all
del data

process = psutil.Process(os.getpid())
print(process.memory_info().rss/1024/1024/1024) # in GB

df_row.drop_duplicates(inplace= True)
df_row.columns = ['CPUTICK','BHZ','FORCE','TEMP','TXN_TIME','BONDHEAD','MCID','RECIPE','KEY','row_num','datetime']
df_row = df_row[df_row['CPUTICK'] != '']
df_row['CPUTICK'] = df_row['CPUTICK'].astype(int)
df_row['TEMP'] = df_row['TEMP'].astype(float)
df_row['FORCE'] = df_row['FORCE'].astype(float)
df_row['BHZ'] = df_row['BHZ'].astype(float)

def feature_engineering(dftemp):
    #FOREC 70~90之間用TEMP往回推5點作為開始,先平移圖形
    dfreset_temp = dftemp[dftemp['TEMP'] >196 ]
    dfreset_temp_groupby = dfreset_temp.groupby('KEY').agg({'row_num':min}).rename(columns={'row_num':'TEMP_start'})
    dfreset_temp_groupby.reset_index(inplace= True)
    dfreset = dftemp.merge(dfreset_temp_groupby, on = ['KEY'])
    dfreset['row_num'] = dfreset['row_num'] -dfreset['TEMP_start']+5
    dfreset = dfreset[dfreset['row_num']>=0]
    #第一區下壓區要到70-90,至少要有70N
    dfreset_force_features1 = dfreset[dfreset['row_num'] < 6 ]
    dfreset_force_features1 = dfreset_force_features1.groupby('KEY').agg({'FORCE':["max","min",'std']})
    dfreset_force_features1.reset_index(col_level=1, col_fill ='', inplace = True)
    dfreset_force_features1.columns = ['key','force_1_max','force_1_min','force_1_std']
    dfreset_force_features1.set_index('key', inplace =True)
    dfreset_force_features1.head()
    #第二區回饋上升, 不能超過90N
    dfreset_force_features2 = dfreset[dfreset['row_num'] > 6 ]
    dfreset_force_features2 = dfreset_force_features2[dfreset_force_features2['row_num'] < 15 ]
    dfreset_force_features2 = dfreset_force_features2.groupby('KEY').agg({'FORCE':["max","min",'std']})
    dfreset_force_features2.reset_index(col_level=1, col_fill ='', inplace = True)
    dfreset_force_features2.columns = ['key','force_2_max','force_2_min','force_2_std']
    dfreset_force_features2.set_index('key', inplace =True)
    dfreset_force_features2.head()
    #第三區無FORCE狀態, +/-10N之內
    dfreset_force_features3 = dfreset[dfreset['row_num'] > 30 ]
    dfreset_force_features3 = dfreset_force_features3[dfreset_force_features3['row_num'] < 150  ]
    dfreset_force_features3 = dfreset_force_features3.groupby('KEY').agg({'FORCE':["max","min",'std']})
    dfreset_force_features3.reset_index(col_level=1, col_fill ='', inplace = True)
    dfreset_force_features3.columns = ['key','force_3_max','force_3_min','force_3_std']
    dfreset_force_features3.set_index('key', inplace =True)
    dfreset_force_features3.head()
    #第一區需要10-20um下壓
    dfreset_bhz_features1 = dfreset[dfreset['row_num'] <=4 ]
    dfreset_bhz_features1 = dfreset_bhz_features1.groupby('KEY').agg({'BHZ':["max","min",'std']})
    dfreset_bhz_features1.reset_index(col_level=1, col_fill ='', inplace = True)
    dfreset_bhz_features1.columns = ['key','bhz_1_max','bhz_1_min','bhz_1_std']
    dfreset_bhz_features1['max-min1'] = dfreset_bhz_features1['bhz_1_max'] - dfreset_bhz_features1['bhz_1_min']
    dfreset_bhz_features1.set_index('key', inplace =True)
    dfreset_bhz_features1.head()
    #第二區需要35um下壓
    dfreset_bhz_features2 = dfreset[dfreset['row_num'] >=5 ]
    dfreset_bhz_features2 = dfreset_bhz_features2[dfreset_bhz_features2['row_num'] <=30 ]
    dfreset_bhz_features2 = dfreset_bhz_features2.groupby('KEY').agg({'BHZ':["max","min",'std']})
    dfreset_bhz_features2.reset_index(col_level=1, col_fill ='', inplace = True)
    dfreset_bhz_features2.columns = ['key','bhz_2_max','bhz_2_min','bhz_2_std']
    dfreset_bhz_features2['max-min2'] = dfreset_bhz_features2['bhz_2_max'] - dfreset_bhz_features2['bhz_2_min']
    dfreset_bhz_features2.set_index('key', inplace =True)
    dfreset_bhz_features2.head()
    #第四區需要35um下壓
    dfreset_bhz_features3 = dfreset[dfreset['row_num'] >=80 ]
    dfreset_bhz_features3 = dfreset_bhz_features3[dfreset_bhz_features3['row_num'] <100 ]
    dfreset_bhz_features3 = dfreset_bhz_features3.groupby('KEY').agg({'BHZ':["max","min",'std']})
    dfreset_bhz_features3.reset_index(col_level=1, col_fill ='', inplace = True)
    dfreset_bhz_features3.columns = ['key','bhz_3_max','bhz_3_min','bhz_3_std']
    dfreset_bhz_features3['max-min3'] = dfreset_bhz_features3['bhz_3_max'] - dfreset_bhz_features3['bhz_3_min']
    dfreset_bhz_features3.set_index('key', inplace =True)
    dfreset_bhz_features3.head()

    #get第一個點195度
    dfreset_temp_features1 = dftemp[dftemp['row_num'] == 1][['KEY','TEMP']]
    dfreset_temp_features1.columns = ['key','temp1']
    dfreset_temp_features1.set_index('key', inplace =True)
    dfreset_temp_features1.head()
    #用196為開始去平移圖形
    dfreset_temp = dftemp[dftemp['TEMP'] >196 ]
    dfreset_temp_groupby = dfreset_temp.groupby('KEY').agg({'row_num':min}).rename(columns={'row_num':'TEMP_start'})
    dfreset_temp_groupby.reset_index(inplace= True)
    dfreset = dftemp.merge(dfreset_temp_groupby, on = ['KEY'])
    dfreset['row_num'] = dfreset['row_num'] -dfreset['TEMP_start']+1
    dfreset = dfreset[dfreset['row_num']>=0]
    dfreset = dfreset[dfreset['TEMP']>=125]
    #195~315區間升溫率, 時間1.5秒內要達到315
    dfreset_temp_features2 = dfreset[dfreset['row_num'] <30 ]
    dfreset_temp_features2 = dfreset_temp_features2.groupby('KEY').agg({'TEMP':["max","min",'std']})
    dfreset_temp_features2.reset_index(col_level=1, col_fill ='', inplace = True)
    dfreset_temp_features2.columns = ['key','temp_2_max','temp_2_min','temp_2_std']
    dfreset_temp_features2.set_index('key', inplace =True)
    dfreset_temp_features2.head()
    #第八區最低溫度140
    dfreset_temp_features3 = dfreset[dfreset['row_num'] > 135 ]
    dfreset_temp_features3 = dfreset_temp_features3[dfreset_temp_features3['row_num'] < 175 ]
    dfreset_temp_features3 = dfreset_temp_features3.groupby('KEY').agg({'TEMP':["max","min",'std']})
    dfreset_temp_features3.reset_index(col_level=1, col_fill ='', inplace = True)
    dfreset_temp_features3.columns = ['key','temp_3_max','temp_3_min','temp_3_std']
    dfreset_temp_features3.set_index('key', inplace =True)
    dfreset_temp_features3.head()
    #第7區溫度變化std
    dfreset_temp_features4 = dfreset[dfreset['row_num'] > 100 ]
    dfreset_temp_features4 = dfreset_temp_features4[dfreset_temp_features4['row_num'] < 135 ]
    dfreset_temp_features4 = dfreset_temp_features4.groupby('KEY').agg({'TEMP':['std']})
    dfreset_temp_features4.reset_index(col_level=1, col_fill ='', inplace = True)
    dfreset_temp_features4.columns = ['key','temp_4_std']
    dfreset_temp_features4.set_index('key', inplace =True)
    dfreset_temp_features4.head()
    #
    df_info = dftemp[dftemp['CPUTICK'] == 0]
    df_info = df_info[['KEY','MCID','BONDHEAD','datetime','RECIPE']].rename({'KEY':'key'},axis='columns')
    df_info.set_index('key', inplace =True)
    df_info.head()
    df_features_a = pd.merge(df_info, right = dfreset_temp_features1, on ='key', how = 'inner', sort = True)
    df_features_b = pd.concat([dfreset_force_features1,dfreset_force_features2,dfreset_force_features3
                  ,dfreset_temp_features2,dfreset_temp_features3,dfreset_temp_features4,dfreset_bhz_features1,dfreset_bhz_features2,dfreset_bhz_features3],axis = 1, sort = True)
    #df_features_b.set_index('key', inplace =True)
    df_features = pd.merge(df_features_a, right = df_features_b, on ='key',how = 'inner', sort = True)
    df_features.dropna(inplace = True)
    df_features.reset_index(inplace =True)
    df_features.columns = ['index','MCID','BONDHEAD','datetime','RECIPE','temp1', 'force_1_max', 'force_1_min', 'force_1_std', 'force_2_max',
       'force_2_min', 'force_2_std', 'force_3_max', 'force_3_min',
       'force_3_std',  'temp_2_max', 'temp_2_min', 'temp_2_std',
       'temp_3_max', 'temp_3_min', 'temp_3_std', 'temp_4_std', 'bhz_1_max',
       'bhz_1_min', 'bhz_1_std', 'max-min1', 'bhz_2_max', 'bhz_2_min',
       'bhz_2_std', 'max-min2', 'bhz_3_max', 'bhz_3_min', 'bhz_3_std',
       'max-min3']
    return df_features
print('start to create feature...')
df_features = feature_engineering(df_row)
df_features.to_csv('./{}.csv'.format(to_csv), index = False)