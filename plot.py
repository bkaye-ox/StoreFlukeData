import plotly.express as px
import pandas as pd
import plotly.graph_objects as go

fname=  '17-2_test0air'
rdf = pd.read_csv(f'data/{fname}_raw.csv')
adf = pd.read_csv(f'data/{fname}.csv')
fig = px.line(rdf,x='Time',y='Flow rate (lpm)')
fig.add_trace(go.Scatter(x=adf['Time'],y=adf['60s flow rate (lpm)'], name='MA'))
fig.show() 