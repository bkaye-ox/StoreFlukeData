
import fluke
import argparse

parser = argparse.ArgumentParser()
parser.add_argument(
    '-n', '--name', help='filename',

)
parser.add_argument(
    '-t', '--time', default=2,  help='time in minutes'
)

parser.add_argument(
    '-m', '--mode',default='airway', help='fluke mode'
)


if __name__ == '__main__':
    freq = 80  # Hz, must be between 20 & 100 go with mux of 2

    #note reporting at 20Hz for some reason

    args = parser.parse_args()

    import datetime
    tnow = datetime.datetime.now()

    experiment_name = args.name  # put the setting name
    # will include current hour-time_ in order to prevent overriding

    # DO NOT FORGET TO SET THE TIME PROPERLY!! currently 10 mins, must be int
    res = fluke.StreamFluke('COM3', args.mode, freq).measure(minutes=int(args.time))
    fluke.store(
        res, f'data/{tnow.hour}-{tnow.minute}_{experiment_name}', freq, 60,)
    print(fluke.cmd_res_store)