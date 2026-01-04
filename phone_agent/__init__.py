# Copyright (c) 2025, Alibaba Cloud and its affiliates;
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
MAI Phone Agent Framework

A complete autonomous Android control system for MAI-UI vision-language models.
Enables users to control Android devices with natural language commands.
"""

__version__ = "0.1.0"
__author__ = "Alibaba Cloud - Tongyi MAI Team"
__license__ = "Apache-2.0"

from phone_agent.device_bridge import DeviceBridge
from phone_agent.executor import TaskExecutor
from phone_agent.integration import AgentIntegration
from phone_agent.config import Config

__all__ = [
    "DeviceBridge",
    "TaskExecutor",
    "AgentIntegration",
    "Config",
    "__version__",
]
