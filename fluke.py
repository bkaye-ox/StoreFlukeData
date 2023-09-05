import argparse
import math
import serial
import time
import asyncio


language = {
    'CR': 0x0D,
    'LF': 0x0A,
    'SP': 0x20,
    'BS': 0x08,
    'ESC': 0x1B,
}
response = {
    'RMAIN': 0,
    'LOCAL': 0,
    '*': 0,
    '!': 1,
    '!01 UNKNOWN COMMAND': 2,
    '!02 ILLEGAL COMMAND': 3,
    '!03 ILLEGAL PARAMETER': 4,
    '!04 BUFFER OVERFLOW': 5,
}

cmd_res_store = []




def cmd_response(ser, cmd: bytes):
    ser.flush()
    ser.write(cmd + b'\r\n')
    while not ser.in_waiting:
        pass
    data = ser.readline()
    return data


def read_data(ser: serial.Serial, dest: list, length: int):

    start_time = time.time()

    while time.time() - start_time < length + 5:
        count = ser.in_waiting
        if count:
            data = ser.read(count)
            dest.append(data)
            # counter += 1
        else:
            time.sleep(1)  # sleep for one second


def setup_fluke(ser, mode, freq):

    if mode == 'airway':
        setup = [b'REMOTE', b'MEAS=AW',
            b'MFLAW=TRUE', b'MFREQ='+bytes(str(freq), 'UTF-8'), b'STREAMIDX']
    else:
        setup = [b'REMOTE', b'MEAS=FLULO',
            b'MFLULO=TRUE', b'MFREQ='+bytes(str(freq), 'UTF-8'), b'STREAMIDX']


    ser.flush()
    for cmd in setup:
        time.sleep(1e-6)
        res = cmd_response(ser, cmd)

        try:
            if response[decode(res).upper()] > 0:
                print('ERR, restart!!')
                return 0
        except:
            cmd_response(b'\x1b')


        cmd_res_store.append(res)
        # print(res)

    return 1


def finish_stream(ser):
    final = [b'\x1b']
    for cmd in final:
        res = cmd_response(ser, cmd)

        if res == b'!\r\n':
            pass

        cmd_res_store.append(res)

        time.sleep(1e-6)


def decode(b):
    return b.decode('UTF-8').replace('\r', '').replace('\n', '')


def extract_data(data, freq):
    data = b''.join(data)

    import pickle as pkl
    pkl.dump(data, open('tmp.pkl', 'wb'))

    end_dex = len(data)-1
    while data[end_dex-1:end_dex+1] != b'\r\n':
        end_dex -= 1
    start_dex = 0
    while data[start_dex:start_dex + 2] != b'\r\n':
        start_dex += 1

    split_data = data[start_dex+2:end_dex-1].split(b'\r\n')

    # data = .split(b'\r\n')

    def extract_line(line):
        data = decode(line)
        try:
            x = data.split(',')
            if len(x) == 2:
                num, index = x
            else:
                return math.nan, math.nan

            if 'OL' in num:
                # num = 'OL' # out of range
                num = 0.75
            else:
                num = float(num)

            index = int(index)
        except:
            num = math.nan
            index = math.nan
        return num, index

    if len(data):
        _, i0 = extract_line(split_data[0])
        return [(n, (k - i0)/freq) for (n, k) in map(extract_line, split_data)] # scaled by 2 idk why
    else:
        return []


class StreamFluke():
    def __init__(self, COM, mode, freq=40):

        self.ser = serial.Serial(COM,
                                 timeout=4/freq,
                                 baudrate=115200,
                                 parity='N',
                                 stopbits=1,
                                 xonxoff=False,
                                 )
        self.ser.close()

        assert freq >= 20 and freq <= 100
        self.freq = freq

        self.mode = 'airway' if mode =='airway' else 'ulflow'

    def measure(self, *, seconds: int = None, minutes: int = None):
        if not ((seconds is None) ^ (minutes is None)):
            raise Exception(
                'Must specify time in seconds OR minutes (NOT BOTH)')
        N = 0
        if seconds is not None:
            N = seconds
        if minutes is not None:
            N = 60*minutes

        dstore = []

        self.ser.open()

        if self.ser.in_waiting:
            self.ser.read(self.ser.in_waiting)

        if setup_fluke(self.ser, self.mode, self.freq):
            read_data(self.ser, dstore, N)
            finish_stream(self.ser)
            self.ser.close()
            return extract_data(dstore, self.freq)
        else:
            return [(), ]


def store(data, time_str, ename, freq, T_ma, plot=True):
    
    import pandas as pd
    import os
    flowr, time = zip(*data)

    if not os.path.exists(f'data/{ename}'):
        os.mkdir(f'data/{ename}')
    fname = f'data/{ename}_{time_str}'

    pd.DataFrame({k: v for k, v in zip(['Time', 'Flow rate (lpm)'], [
                 time, flowr])}).to_csv(f'{fname}_raw.csv', index=False)

    print(f'{1000*sum(flowr)/len(flowr):.2f} mLpm')

    ma = pd.Series(flowr).rolling(T_ma*freq, min_periods=1).mean()

    df = pd.DataFrame({k: v for k, v in zip(['Time', f'{T_ma}s flow rate (lpm)'], [
        time, ma])})
    df.drop(index=df.index[((df['Time'] % 1) != 0)], inplace=True)
    df.to_csv(f'{fname}.csv', index=False)
    
    if plot:
        import plotly.express as px
        fig = px.line(df, x='Time', y=f'{T_ma}s flow rate (lpm)')
        fig.update_layout(title=fname).show()
