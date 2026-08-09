# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Service wiring for Volkanos API error handling (see django_utils.api.v2_errors)."""

from django_contentdb.utils import standard_exception_handler
from django_utils.api.v2_errors import make_exception_handler

volkanos_exception_handler = make_exception_handler(v1_handler=standard_exception_handler)
