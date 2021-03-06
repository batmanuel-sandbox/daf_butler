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

from .utils import slotValuesAreEqual

__all__ = ("StorageInfo", )


class StorageInfo:
    """Represents storage information.

    Parameters
    ----------
    datastoreName : `str`
        Name of datastore.
    checksum : `str`
        Checksum.
    size : `int`
        Size of stored object in bytes.
    """
    __eq__ = slotValuesAreEqual
    __slots__ = ("_datastoreName", "_checksum", "_size")

    def __init__(self, datastoreName, checksum=None, size=None):
        assert isinstance(datastoreName, str)
        self._datastoreName = datastoreName
        assert checksum is None or isinstance(checksum, str)
        self._checksum = checksum
        assert size is None or isinstance(size, int)
        self._size = size

    @property
    def datastoreName(self):
        """Name of datastore (`str`).
        """
        return self._datastoreName

    @property
    def checksum(self):
        """Checksum (`str`).
        """
        return self._checksum

    @property
    def size(self):
        """Size of stored object in bytes (`int`).
        """
        return self._size
