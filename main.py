#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, sysconfig
print(sys._is_gil_enabled())
print(sysconfig.get_config_var("Py_GIL_DISABLED"))


# Section 尾注 开源许可证

# Bill_Analyzer © 2025 by ee19971 is licensed under Creative Commons Attribution 4.0 International
# https://creativecommons.org/licenses/by/4.0/