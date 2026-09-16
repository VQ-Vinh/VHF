"""Operator console client layer.

Transport and state machines for driving remote Stations. Deliberately free of
any GUI toolkit import so the desktop app can compose it and the tests can run
it without a QApplication.
"""
