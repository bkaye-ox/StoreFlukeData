import argparse
import math
import serial
import time
import asyncio

# char reference
language = {
    'CR': 0x0D,
    'LF': 0x0A,
    'SP': 0x20,
    'BS': 0x08,
    'ESC': 0x1B,
}
# responses, 0 good, >=1 error
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

debug_command_responses = []


def cmd_response(ser, cmd: bytes):
    ser.flush()
    ser.write(cmd + b'\r\n')
    while not ser.in_waiting:
        pass
    data = ser.readline()
    return data


def read_data(ser: serial.Serial, data_store: list, length: int, poll_freq: float = 1):

    start_time = time.time()

    while time.time() - start_time < length:
        count = ser.in_waiting
        if count > 4000:  # every approx 400 readings, store
            data = ser.read(count)
            data_store.append(data)
            # counter += 1
        else:
            time.sleep(1/poll_freq)  # timeout

    count = ser.in_waiting
    data = ser.read(count)
    data_store.append(data)


def stream_cmds(mode, freq):
    setup = [b'REMOTE']
    if mode == 'airway':
        setup += [b'MEAS=AW',
                  b'MFLAW=TRUE']
    elif mode == 'ulflow':
        setup += [b'MEAS=FLULO',
                  b'MFLULO=TRUE']
    else:
        raise Exception('unexpected mode!')
    setup += [b'MFREQ='+bytes(str(freq), 'UTF-8'), b'STREAMIDX']
    return setup


def start_stream(ser, mode, freq):
    cmd_sequence = stream_cmds(mode, freq)

    ser.flush()
    for cmd in cmd_sequence:
        time.sleep(1e-6)
        res = cmd_response(ser, cmd)

        try:
            if response[decode(res).upper()] > 0:
                print('ERR, restart!!')
                return 0
        except:
            # send escape character
            cmd_response(b'\x1b')

        debug_command_responses.append(res)
        # print(res)

    return 1


def end_stream(ser):
    res = cmd_response(ser, b'\x1b')
    debug_command_responses.append(res)
    time.sleep(1e-6)


def clear_buffer(ser):
    if ser.in_waiting:
        ser.read(ser.in_waiting)


def decode(b):
    return b.decode('UTF-8').replace('\r', '').replace('\n', '')

def stitch_data(data):
    temp =  b'x'.join(data)
    # eg stitching ....\r\n30

def extract_data(data, freq):
    data = b''.join(data).replace(b'\r\n',b'\n').replace(b'\r',b'\n')

    import pickle as pkl
    pkl.dump(data, open('tmp.pkl', 'wb'))

    end_dex = len(data)-1
    while data[end_dex] != b'\n'[0]:
        end_dex -= 1
    start_dex = 0
    while data[start_dex] != b'\n'[0]:
        start_dex += 1

    split_data = data[start_dex+1:end_dex].split(b'\n')

    def extract_line(line):
        data = decode(line)
        # data = 

        try:
            x = data.split(',')
            if len(x) == 2:
                num, index = x
            elif len(x) == 3:
                num, _, index = x
            else:
                return math.nan, math.nan

            if 'OL' in num:
                # num = 'OL' # out of range
                num = 'OL'
            else:
                num = float(num)

            index = int(index)
        except:
            num = math.nan
            index = math.nan
        return num, index

    if len(data):
        _, i0 = extract_line(split_data[0])
        # scaled by 2 idk why
        return [(n, (k - i0)/freq) for (n, k) in map(extract_line, split_data)]
    else:
        return []


class StreamFluke():
    def __init__(self, COM, mode, freq=40):

        self.ser = serial.Serial(COM,
                                 timeout=0.1,
                                 baudrate=115200,
                                 parity='N',
                                 stopbits=1,
                                 xonxoff=False,
                                 )
        self.ser.close()

        assert freq >= 20 and freq <= 100
        self.freq = freq

        self.mode = 'airway' if mode == 'airway' else 'ulflow'

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

        clear_buffer(self.ser)

        if start_stream(self.ser, self.mode, self.freq):
            read_data(self.ser, dstore, N)
            end_stream(self.ser)
            clear_buffer(self.ser)
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
    fname = f'data/{ename}/{ename}_{time_str}'

    pd.DataFrame({k: v for k, v in zip(['Time', 'Flow rate (lpm)'], [
                 time, flowr])}).to_csv(f'{fname}_raw.csv', index=False)

    num_flow = [f if f != 'OL' else 0.750 for f in flowr]
    print(f'{1000*sum(num_flow)/len(num_flow):.2f} mLpm')

    flowr = pd.Series(flowr)
    ma = pd.to_numeric(flowr, errors='coerce').rolling(
        T_ma*freq, min_periods=1,).mean()

    df = pd.DataFrame({k: v for k, v in zip(['Time', f'{T_ma}s flow rate (lpm)'], [
        time, ma])})
    df.drop(index=df.index[((df['Time'] % 1) != 0)], inplace=True)
    df.to_csv(f'{fname}.csv', index=False)

    if plot:
        import plotly.express as px
        fig = px.line(df, x='Time', y=f'{T_ma}s flow rate (lpm)')
        fig.update_layout(title=fname).show()


def recover(freq, e_time, e_name ):
    import pickle
    data = pickle.load(open('tmp.pkl', 'rb'))
    res = extract_data([data], freq)
    store(res, e_time, e_name, freq, 60, plot=False)


if __name__ == '__main__':
    # import time
    # t_str = time.strftime('%H-%m', time.localtime())
    # name = 'o2sweep'
    # freq = 60
    # t_length = 26
    # mode = 'airway'

    # res = StreamFluke(
    #     'COM3',
    #     mode,
    #     freq,
    # ).measure(minutes=t_length)

    # store(res, t_str, name, freq, 60, plot=False)7
    # recover(60, '11-15','o2sweep')
    pass