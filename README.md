# Installation

1.Python connection to sql server

```bash
pip install pyodbc 
```

2.ODBC Driver 17 for SQL Server 
https://www.microsoft.com/zh-tw/download/details.aspx?id=56567 


3.joblib
```bash
pip install joblib 
```


# How to use the script

Run this script by order

1.feature.py   
create feature for training model.

```bash
$python feature.py start_date end_date to_csv
```

2.model.py  
training nodel.

```bash
$python model.py input_file_name
```

3.azurews.py  
azure machine learning ws connection configuration.

```bash
$python azurews.py
```


4.registermodel.py  
register model to azure machine learning serivce A3CIM.

```bash
$python registermodel.py RegisterModel WhatModel
```
