
import fluke
import argparse

parser = argparse.ArgumentParser()
parser.add_argument(
    '-n', '--name', help='filename',

)
parser.add_argument(
    '-t', '--time', help='time in minutes'
)

parser.add_argument(
    '-m', '--mode',default='airway', help='fluke mode'
)

parser.add_argument(
    '-f', '--freq', default=80, help='logging frequency Hz'
)

parser.add_argument(
    '-p', '--port', default='COM3', help='COM port, eg COM3'
)

parser.add_argument(
    '-s', '--show', default=False, help='show plots'
)


if __name__ == '__main__':
    # freq = 80  # Hz, must be between 20 & 100 go with mux of 2

    #note reporting at 20Hz for some reason

    args = parser.parse_args()

    import time
    t_str = time.strftime('%H-%m',time.localtime())

    experiment_name = args.name  # put the setting name
    # will include current hour-time_ in order to prevent overriding

    # DO NOT FORGET TO SET THE TIME PROPERLY!! currently 10 mins, must be int
    res = fluke.StreamFluke(args.port, args.mode, args.freq).measure(minutes=int(args.time))
    fluke.store(
        res, t_str, experiment_name, args.freq, 60,)
    # prin-t t(fluke.debug_command_responses)