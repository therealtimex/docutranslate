# SPDX-FileCopyrightText: 2025 RealTimeX
# SPDX-License-Identifier: MPL-2.0
import logging



# Create logger object
global_logger = logging.getLogger("TranslaterLogger")
global_logger.setLevel(logging.DEBUG)
# Output to console
console_handler = logging.StreamHandler()
global_logger.addHandler(console_handler)