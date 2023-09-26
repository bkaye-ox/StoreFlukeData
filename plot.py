import plotly.express as px
import pandas as pd
import plotly.graph_objects as go

fname = 'o2sweep/o2sweep_11-15'

chunk_lookup = {k:f'{(k+1)*20:d}%' if k<=4 else f'100%' for k in range(8)}
rdf = pd.read_csv(f'data/{fname}_raw.csv')
adf = pd.read_csv(f'data/{fname}.csv')




def post(df, t_max):
    df.drop(index=df.index[(df['Time'] > t_max)|(df['Time']<0)], inplace=True)



def split(first_change: int, duration: int, freq: int):
    t0 = first_change - duration

    # k0 = rdf[rdf['Time'] > t0].iloc[0].name

    num_chunks = int((len(rdf)/freq - t0)//duration) + 1
    for h in range(num_chunks):
        rdf.loc[(rdf['Time'] >= t0 + h*duration) &
                (rdf['Time'] < t0+(h+1)*duration), 'Output'] = chunk_lookup[h]

    for k, c in rdf.groupby('Output'):
        pass
        if k != 'unassigned':
            k0 = c.iloc[0].name
            rdf.loc[k0:k0+len(c), 'kTime'] = c['Time'] - c['Time'].iloc[0]



    rdf.drop(index=rdf.index[rdf['Output'] == 'unassigned'], inplace=True)

    rdf[tuple(rdf['Flow rate (lpm)'] == 'OL'), 'Flow rate (lpm)'] = 0.83
    rdf['Flow rate (lpm)'] = pd.to_numeric(
        rdf['Flow rate (lpm)'], errors='coerce')
    rdf.dropna(how='all', inplace=True)

    tmp = rdf.groupby('Output')['Flow rate (lpm)'].rolling(60*freq,min_periods=1).mean()
    rdf.loc[list(zip(*tmp.index))[1], 'Avg'] = tmp.values

    px.line(rdf, x='kTime', y='Avg', color='Output').show()
    px.line(rdf, x='kTime', y='Flow rate (lpm)', color='Output').show()

rdf['Flow rate (lpm)'] = pd.to_numeric(rdf['Flow rate (lpm)'], errors='coerce')

post(rdf, 2000, )

rdf['Avg'] = rdf['Flow rate (lpm)'].dropna().rolling(60*60).mean(numeric_only=True)

px.line(rdf,x='Time', y=['Flow rate (lpm)', 'Avg'], ).show()


# fig = px.line(rdf, x='Time', y='Flow rate (lpm)')
# fig.add_trace(go.Scatter(
#     x=adf['Time'], y=adf['60s flow rate (lpm)'], name='MA'))
# fig.show()


split(306.9,300,60)