# SPDX-License-Identifier: Apache-2.0

from haystack import ComponentError


class ExaError(ComponentError):
    """Exception raised when an error occurs while querying the Exa API."""
