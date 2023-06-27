import time

_timestamps = dict()
_start = None


def init():
    global _timestamps, _start
    _timestamps.clear()
    _start = time.time()


def log(name):
    global _timestamps, _start
    if not _start:
        return
    if name in _timestamps:
        return
    duration = time.time() - _start
    _timestamps[name] = duration
    print(f'timing - {name}: {duration: .2f}s')
    return duration


def get(name, default_value=None):
    global _timestamps, _start
    if not _start or name not in _timestamps:
        return default_value
    return _timestamps[name]


def report():
    return ', '.join([
        f'{name}: {duration: .2f}s'
        for name, duration in sorted(
                _timestamps.items(),
                key=lambda name_duration: name_duration[1],
        )
    ])
