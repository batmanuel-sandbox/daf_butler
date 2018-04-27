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

import os

from lsst.log import Log
from lsst.utils import getPackageDir

from lsst.daf.butler import Config, Butler
from lsst.daf.persistence import Butler as FallbackButler

__all__ = ("ShimButler", )

def _fallbackOnFailure(func):
    """Decorator that wraps a `ShimButler` method and falls back to the
    corresponding Gen2 `Butler` method when an `Exception` is raised.
    """
    def inner(self, *args , **kwargs):
        try:
            return func(self, *args, **kwargs)
        except NotImplementedError as e:
            log = Log.getLogger("lsst.daf.butler.shimButler")
            log.info("Fallback called for: %s, original call failed with: %s on args=%s, kwargs=%s",
                func.__name__, e, args, kwargs)
        fallbackFunc = getattr(self._fallbackButler, func.__name__)
        return fallbackFunc(*args, **kwargs)
    return inner

class ShimButler:
    """Shim around Butler that acts as a Gen2 Butler.

    TODO until implementation is complete we fall back to a Gen2 Butler
    instance upon receiving an unimplemented call.
    """
    def __init__(self, *args, gen3Root=None, **kwargs):
        if gen3Root is None:
            raise ValueError("Need gen3Root to construct ShimButler")
        butlerConfig = Config()
        butlerConfig["run"] = "ci_hsc"
        butlerConfig["registry.cls"] = "lsst.daf.butler.registries.sqliteRegistry.SqliteRegistry"
        butlerConfig["registry.db"] = "sqlite:///{}/gen3.sqlite3".format(gen3Root)
        butlerConfig["registry.schema"] = os.path.join(getPackageDir("daf_butler"),
                                                    "config/registry/default_schema.yaml")
        butlerConfig["storageClasses.config"] = os.path.join(getPackageDir("daf_butler"),
                                                            "config/registry/storageClasses.yaml")
        butlerConfig["datastore.cls"] = "lsst.daf.butler.datastores.posixDatastore.PosixDatastore"
        butlerConfig["datastore.root"] = gen3Root
        butlerConfig["datastore.create"] = True
        butlerConfig["datastore.formatters"] = {
            "SourceCatalog": "lsst.daf.butler.formatters.fitsCatalogFormatter.FitsCatalogFormatter",
            "ImageF": "lsst.daf.butler.formatters.fitsCatalogFormatter.FitsCatalogFormatter",
            "MaskX": "lsst.daf.butler.formatters.fitsCatalogFormatter.FitsCatalogFormatter",
            "Exposure": "lsst.daf.butler.formatters.fitsExposureFormatter.FitsExposureFormatter",
            "ExposureF": "lsst.daf.butler.formatters.fitsExposureFormatter.FitsExposureFormatter",
            "ExposureI": "lsst.daf.butler.formatters.fitsExposureFormatter.FitsExposureFormatter",
        }
        self._butler = Butler(butlerConfig)
        self._fallbackButler = FallbackButler(*args, **kwargs)

    def _mapDatasetType(self, datasetType):
        log = Log.getLogger("lsst.daf.butler.shimButler")
        log.info("mapping datasetType: %s", datasetType)
        return datasetType

    def _mapDataId(self, dataId):
        log = Log.getLogger("lsst.daf.butler.shimButler")
        log.info("mapping dataId: %s", dataId)
        return dataId

    @_fallbackOnFailure
    def getKeys(self, datasetType=None, level=None, tag=None):
        """Get the valid data id keys at or above the given level of hierarchy for the dataset type or the
        entire collection if None. The dict values are the basic Python types corresponding to the keys (int,
        float, string).

        Parameters
        ----------
        datasetType - string
            The type of dataset to get keys for, entire collection if None.
        level - string
            The hierarchy level to descend to. None if it should not be restricted. Use an empty string if the
            mapper should lookup the default level.
        tags - any, or list of any
            Any object that can be tested to be the same as the tag in a dataId passed into butler input
            functions. Applies only to input repositories: If tag is specified by the dataId then the repo
            will only be read from used if the tag in the dataId matches a tag used for that repository.

        Returns
        -------
        Returns a dict. The dict keys are the valid data id keys at or above the given level of hierarchy for
        the dataset type or the entire collection if None. The dict values are the basic Python types
        corresponding to the keys (int, float, string).
        """
        raise NotImplementedError()

    @_fallbackOnFailure
    def queryMetadata(self, datasetType, format, dataId={}, **rest):
        """Returns the valid values for one or more keys when given a partial
        input collection data id.

        Parameters
        ----------
        datasetType - string
            The type of dataset to inquire about.
        format - str, tuple
            Key or tuple of keys to be returned.
        dataId - DataId, dict
            The partial data id.
        **rest -
            Keyword arguments for the partial data id.

        Returns
        -------
        A list of valid values or tuples of valid values as specified by the
        format.
        """
        raise NotImplementedError()

    @_fallbackOnFailure
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
        raise NotImplementedError()

    @_fallbackOnFailure
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
        raise NotImplementedError()

    @_fallbackOnFailure
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
        self._butler.put(obj,
                         datasetType=self._mapDatasetType(datasetType),
                         dataId=self._mapDataId(dataId))
        raise NotImplementedError()

    @_fallbackOnFailure
    def dataRef(self, datasetType, level=None, dataId={}, **rest):
        """Returns a single ButlerDataRef.

        Given a complete dataId specified in dataId and **rest, find the unique dataset at the given level
        specified by a dataId key (e.g. visit or sensor or amp for a camera) and return a ButlerDataRef.

        Parameters
        ----------
        datasetType - string
            The type of dataset collection to reference
        level - string
            The level of dataId at which to reference
        dataId - dict
            The data id.
        **rest
            Keyword arguments for the data id.

        Returns
        -------
        dataRef - ButlerDataRef
            ButlerDataRef for dataset matching the data id
        """
        raise NotImplementedError()

    def subset(self, datasetType, level=None, dataId={}, **rest):
        """Return complete dataIds for a dataset type that match a partial (or empty) dataId.

        Given a partial (or empty) dataId specified in dataId and **rest, find all datasets that match the
        dataId.  Optionally restrict the results to a given level specified by a dataId key (e.g. visit or
        sensor or amp for a camera).  Return an iterable collection of complete dataIds as ButlerDataRefs.
        Datasets with the resulting dataIds may not exist; that needs to be tested with datasetExists().

        Parameters
        ----------
        datasetType - string
            The type of dataset collection to subset
        level - string
            The level of dataId at which to subset. Use an empty string if the mapper should look up the
            default level.
        dataId - dict
            The data id.
        **rest
            Keyword arguments for the data id.

        Returns
        -------
        subset - ButlerSubset
            Collection of ButlerDataRefs for datasets matching the data id.

        Examples
        -----------
        To print the full dataIds for all r-band measurements in a source catalog
        (note that the subset call is equivalent to: `butler.subset('src', dataId={'filter':'r'})`):

        >>> subset = butler.subset('src', filter='r')
        >>> for data_ref in subset: print(data_ref.dataId)
        """
        butlerSubset = self._fallbackButler.subset(datasetType, level=level, dataId=dataId, **rest)
        butlerSubset.butler = self  # Needs shim too
        return butlerSubset

    def __getattr__(self, name):
        """Forwards all unwrapped attributes directly to Gen2 `Butler`.
        """
        # Do not forward special members (prevents recursion and other
        # surprising behavior)
        if name.startswith("__"):
            raise AttributeError("Attribute not found")
        return getattr(self._fallbackButler, name)
