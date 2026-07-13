# =================================================================
#
# Authors: Francesco Martinelli <francesco.martinelli@ingv.it>
#
# Copyright (c) 2026 Francesco Martinelli
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# =================================================================

import logging

from pygeoapi.process.manager.base import PostgreSQLManager

LOGGER = logging.getLogger(__name__)

class PostgreSQLManagerWithDelete(PostgreSQLManager):
    """
    PostgreSQL Manager

    Added temporary functionality while waiting implementation in core.
    """

    def __init__(self, manager_def: dict):
        """
        Initialize object
        """

        super().__init__(manager_def)

    def delete_job(self, job_id: str) -> bool:
        """
        Deletes a job
        :param job_id: job identifier
        :raises JobNotFoundError: if the job_id does not correspond to a
                                  known job
        :return `bool` of status result
        """

        # get process used for the job.
        process_id = self.get_job(job_id).get('process_id')

        deleted = super.deleteJob(job_id)
        if (deleted):
            # remove resources if present
            processor = self.get_processor(process_id)
            processor.remove_resources(job_id)
            
        return deleted
