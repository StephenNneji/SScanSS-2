"""
A collection of miscellaneous functions
"""
import math
import numpy as np


def clamp(value, min_value=0.0, max_value=1.0):
    """ clamps a value between a minimum and maximum value.
    Similar to ``numpy.clip`` but is faster for non-array

    :param value: number to clamp
    :type value: float
    :param min_value: maximum value
    :type min_value: float
    :param max_value: minimum value
    :type max_value: float
    :return: number clamped between the specified range
    :rtype: float
    """
    return max(min(value, max_value), min_value)


def map_range(old_min, old_max, new_min, new_max, value):
    """ takes two ranges and a real number, and returns the mapping of the
    real number from the first to the second range.

    :param old_min: minimum of first range
    :type old_min: float
    :param old_max: maximum of first range
    :type old_max: float
    :param new_min: minimum of second range
    :type new_min: float
    :param new_max: maximum of second range
    :type new_max: float
    :param value: real number to remap
    :type value: float
    :return: remapped value
    :rtype: float
    """
    return new_min + ((value - old_min) * (new_max - new_min) / (old_max - old_min))


def trunc(value, decimals=0):
    """ Truncates values after a number of decimal points

    :param value: number to truncate
    :type value: float
    :param decimals: number of decimals points to keep
    :type decimals: int
    :return: truncated float
    :rtype: float
    """
    step = 10 ** decimals
    return math.trunc(value * step)/step


def is_close(a, b, tol=1e-5):
    """ Checks that two values are close by comparing absolute difference with tolerance

    :param a: first value
    :type a: array_like
    :param b: second value
    :type b: array_like
    :param tol: tolerance
    :type tol: float
    :return: indicates if values are close
    :rtype: bool
    """
    if np.all(np.abs(np.subtract(a, b)) < tol):
        return True
    return False
