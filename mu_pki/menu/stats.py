import math
import statistics
from typing import Sequence

# 0.95
T_DISTRIBUTION: list[float] = [
    0,
    0,
    4.303,
    3.182,
    2.776,
    2.571,
    2.447,
    2.365,
    2.306,
    2.262,
    2.228,
    2.201,
    2.179,
    2.160,
    2.145,
    2.131,
    2.120,
    2.110,
    2.101,
    2.093,
    2.086,
    2.080,
    2.074,
    2.069,
    2.064,
    2.060,
    2.056,
    2.052,
    2.048,
    2.045,
    2.042,
    2.040,
    2.037,
    2.035,
    2.032,
    2.030,
    2.028,
    2.026,
    2.024,
    2.023,
    2.021,
]


def ci(clip: Sequence[int], avg_only=False):
    """+95% ci"""
    n = len(clip)
    len_avg = statistics.mean(clip)
    if 2 < n and not avg_only:
        len_stdev = statistics.pstdev(clip)
        t = T_DISTRIBUTION[n - 1] if n <= len(T_DISTRIBUTION) else 1.960

        return len_avg + (t * len_stdev / math.sqrt(n))

    return len_avg


def predict_index_avg_len(n: int):
    total = 1
    left = n - 1
    i = 1
    while left > 0:
        count = min(pow(10, i) - pow(10, i - 1), left)
        total += i * count
        left -= count
        i += 1

    return total / n
