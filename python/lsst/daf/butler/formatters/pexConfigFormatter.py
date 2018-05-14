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

import os.path

from lsst.daf.butler.formatters.fileFormatter import FileFormatter

__all__ = ("PexConfigFormatter", )


class PexConfigFormatter(FileFormatter):
    """Interface for reading and writing pex.config.Config objects from disk.
    """
    extension = ".py"

    def _readFile(self, path, pytype):
        """Read a pex.config.Config instance from the given file.

        Parameters
        ----------
        path : `str`
            Path to use to open the file.
        pytype : `class`
            Class to use to read the config file.

        Returns
        -------
        data : `lsst.pex.config.Config`
            Instance of class `pytype` read from config file. None
            if the file could not be opened.
        """
        if not os.path.exists(path):
            return None
        instance = pytype()
        instance.load(path)
        return instance

    def _writeFile(self, inMemoryDataset, fileDescriptor):
        """Write the in memory dataset to file on disk.

        Parameters
        ----------
        inMemoryDataset : `object`
            Object to serialize.
        fileDescriptor : `FileDescriptor`
            Details of the file to be written.

        Raises
        ------
        Exception
            The file could not be written.
        """
        inMemoryDataset.save(fileDescriptor.location.path)
