# This file is part of daf_butler.
#
# Developed for the LSST Data Management System.
# This product includes software developed by the LSST Project
# (http://www.lsst.org).
# See the COPYRIGHT file at the top-level directory of this distribution
# for details of code ownership.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
ShimButler
"""

__all__ = ("ShimButler", )


class ShimButler:
    """Shim around Gen3 Butler that acts as a Gen2 Butler.

    Parameters
    ----------
    butler : `Butler`
        A Gen3 Butler instance.
    """
    def __init__(self, butler):
        self._butler = butler

    def datasetExists(self, datasetType, dataId={}, write=False, **rest):
        """Determines if a dataset file exists.
        Parameters
        ----------
        datasetType - string
            The type of dataset to inquire about.
        dataId - DataId, dict
            The data id of the dataset.
        write - bool
            If True, look only in locations where the dataset could be written,
            and return True only if it is present in all of them.
        **rest keyword arguments for the data id.
        Returns
        -------
        exists - bool
            True if the dataset exists or is non-file-based.
        """
        raise NotImplementedError("missing")

    def get(self, datasetType, dataId=None, immediate=True, **rest):
        """Retrieves a dataset given an input collection data id.
        Parameters
        ----------
        datasetType - string
            The type of dataset to retrieve.
        dataId - dict
            The data id.
        immediate - bool
            If False use a proxy for delayed loading.
        **rest
            keyword arguments for the data id.
        Returns
        -------
            An object retrieved from the dataset (or a proxy for one).
        """
        raise NotImplementedError("missing")

    def put(self, obj, datasetType, dataId={}, doBackup=False, **rest):
        """Persists a dataset given an output collection data id.
        Parameters
        ----------
        obj -
            The object to persist.
        datasetType - string
            The type of dataset to persist.
        dataId - dict
            The data id.
        doBackup - bool
            If True, rename existing instead of overwriting.
            WARNING: Setting doBackup=True is not safe for parallel processing, as it may be subject to race
            conditions.
        **rest
            Keyword arguments for the data id.
        """
        raise NotImplementedError("missing")
