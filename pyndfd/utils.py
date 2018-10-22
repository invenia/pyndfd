import warnings


def deprecate_func(old_name, new_function):
    """
    Deprecate a function name, and return the new function that should be used. This
    will allow users to still call the new function as the old function name, but will
    generate a deprecation warning.

    Args:
        old_name (str): The old function name that shouldn't be used anymore
        new_function (func): The new function to be called instead

    Returns:
        func: Return a function that takes in *args, and **kwargs. This function will
        generate a deprecation warning, and then return the results of calling the
        new function.
    """
    def df(*args, **kwargs):
        warnings.warn(
            "'{}' is not a Pep8 compliant function name, use '{}' instead".format(
                old_name, new_function.__name__
            ),
            DeprecationWarning,
            stacklevel=2,
        )
        return new_function(*args, **kwargs)

    return df
