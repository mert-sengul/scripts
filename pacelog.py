import os
import subprocess
import sys
from collections import deque
from time import time

import colorama as clr

# get terminal width
TERM_WIDTH = int(os.popen("stty size", "r").read().split()[1])
# for windows
clr.init()


class TimeTracker:
    "For tracking time elapsed over a sliding window of timestamps."

    def __init__(self, window_length=10):
        self.window_length = window_length
        self.timestamps = deque([time()], maxlen=window_length)
        self.max_time_elapsed = 0.0

    def __call__(self):
        self.update_timestamp()
        return self.get_time_elapsed()

    def update_timestamp(self):
        curr_time = time()
        self.timestamps.append(curr_time)
        self._update_max_time_elapsed()

    def _update_max_time_elapsed(self):
        if len(self.timestamps) > 1:  # Ensure there are at least two timestamps to compare
            time_elapsed = self.timestamps[-1] - self.timestamps[0]
            self.max_time_elapsed = max(self.max_time_elapsed, time_elapsed)

    def get_time_elapsed(self):
        return self.timestamps[-1] - self.timestamps[0] if len(self.timestamps) > 1 else 0.0

    def get_max_time_elapsed(self):
        "Return the maximum time elapsed observed in the current window."
        return self.max_time_elapsed


def get_color(f: float):
    if f < 0.05:
        return clr.Fore.WHITE
    elif f < 0.1:
        return clr.Fore.GREEN
    elif f < 0.2:
        return clr.Fore.YELLOW
    elif f < 0.3:
        return clr.Fore.MAGENTA
    elif f < 0.5:
        return clr.Fore.RED
    else:
        return clr.Fore.RED + clr.Style.BRIGHT


def break_line(line: str, max_len=80, tab=4):
    line_sep = "\n" + " " * tab
    if len(line) <= max_len:
        return line
    return line_sep.join([line[i : i + max_len] for i in range(0, len(line), max_len)]) + "\n"


BUFFER_SIZE = 10
TIMESTAMPS = deque((time() for _ in range(BUFFER_SIZE)), maxlen=BUFFER_SIZE)
MAX_TIME_ELAPSED = 0.0

TO_BE_PRINTED: deque[str] = deque(("" for _ in range(BUFFER_SIZE // 2)), maxlen=BUFFER_SIZE // 2)


tracker = TimeTracker(window_length=BUFFER_SIZE)


def handle_time() -> float:
    """Keeps track of time using global TIMESTAMPS dequeue.
    Witch each call, it appends the current time to the deque, discards oldest timestamp.
    Returns the time elapsed since the first timestamp."""
    global TIMESTAMPS, MAX_TIME_ELAPSED

    curr_time = time()
    window_start = TIMESTAMPS[0]

    time_elapsed = curr_time - window_start

    if time_elapsed > MAX_TIME_ELAPSED:
        # this can be useful for adjusting get_color function
        MAX_TIME_ELAPSED = time_elapsed

    TIMESTAMPS.append(curr_time)

    return time_elapsed


def process_and_print_batch(batch):
    """Process the batch of lines and print them with the time elapsed. Color is based on time elapsed."""
    global TIMESTAMPS, MAX_TIME_ELAPSED, TERM_WIDTH, TO_BE_PRINTED
    TAB_WIDTH = 10  # for "|0.000| - " in the beginning

    # time_elapsed = handle_time()
    time_elapsed = tracker()

    print_later = "".join(batch)
    print_now = f"{get_color(time_elapsed)}|{time_elapsed:2.3f}| - " + TO_BE_PRINTED[0]
    print(break_line(print_now, TERM_WIDTH + 5, TAB_WIDTH), end=clr.Style.RESET_ALL)
    TO_BE_PRINTED.append(print_later)


def parse_command():
    SEPERATOR = " -- "
    s_input = " ".join(sys.argv[1])
    commands_list = (s_input).split(SEPERATOR)
    return " && ".join(commands_list)


if __name__ == "__main__":
    # Start the process

    command = parse_command()
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, shell=True, text=True, bufsize=-1, universal_newlines=True
    )

    # Initialize an empty list to hold the batch of lines
    batch = []
    batch_size = 1  # Specify the desired batch size
    assert process.stdout is not None

    # Read output line by line in real time
    while True:
        with process.stdout as pipe:
            for line in pipe:
                batch.append(line)
                if len(batch) == batch_size:
                    process_and_print_batch(batch)
                    batch = []  # Reset the batch to empty

        # Process and print any remaining lines in the last batch
        if batch:
            process_and_print_batch(batch)

    # Wait for the subprocess to finish if it's not done
    process.wait()
