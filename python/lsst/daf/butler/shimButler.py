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

from lsst.daf.butler import Config, Butler
from lsst.daf.butler.gen2convert.structures import Gen2DatasetType
from lsst.daf.butler.gen2convert.translators import Translator
from lsst.daf.persistence import Butler as FallbackButler

import re

from lsst.daf.butler.instrument import Instrument
from lsst.daf.butler.gen2convert import KeyHandler
from lsst.daf.butler.gen2convert import ConstantKeyHandler, CopyKeyHandler

__all__ = ("HyperSuprimeCam",)


# Regular expression that matches HSC PhysicalFilter names (the same as Gen2
# filternames), with a group that can be lowercased to yield the
# associated AbstractFilter.
FILTER_REGEX = re.compile(r"HSC\-([GRIZY])2?")


class HyperSuprimeCam(Instrument):
    """Gen3 Butler specialization class for Subaru's Hyper Suprime-Cam.

    The current implementation simply retrieves the information it needs
    from a Gen2 HscMapper instance (the only constructor argument).  This
    will obviously need to be changed before Gen2 is retired, but it avoids
    duplication for now.
    """

    camera = "HSC"

    def __init__(self, mapper):
        self.sensors = [
            dict(
                sensor=sensor.getId(),
                name=sensor.getName(),
                # getType() returns a pybind11-wrapped enum, which
                # unfortunately has no way to extract the name of just
                # the value (it's always prefixed by the enum type name).
                purpose=str(sensor.getType()).split(".")[-1],
                # The most useful grouping of sensors in HSC is by their
                # orientation w.r.t. the focal plane, so that's what
                # we put in the 'group' field.
                group="NQUARTER{:d}".format(sensor.getOrientation().getNQuarter() % 4)
            )
            for sensor in mapper.camera
        ]
        self.physicalFilters = []
        for name in mapper.filters:
            # We use one of grizy for the abstract filter, when appropriate,
            # which we identify as when the physical filter starts with
            # "HSC-[GRIZY]".  Note that this means that e.g. "HSC-I" and
            # "HSC-I2" are both mapped to abstract filter "i".
            m = FILTER_REGEX.match(name)
            self.physicalFilters.append(
                dict(
                    physical_filter=name,
                    abstract_filter=m.group(1).lower() if m is not None else None
                )
            )


class HscAbstractFilterKeyHandler(KeyHandler):
    """KeyHandler for HSC filter keys that should be mapped to AbstractFilters.
    """

    __slots__ = ()

    def __init__(self):
        super().__init__("abstract_filter", "AbstractFilter")

    def extract(self, gen2id, skyMap, skyMapName):
        physical = gen2id["filter"]
        m = FILTER_REGEX.match(physical)
        if m:
            return m.group(1).lower()
        return physical


class HscPhysicalFilterKeyHandler(KeyHandler):
    """KeyHandler for HSC filter keys that should be mapped to PhysicalFilters.
    """

    __slots__ = ()

    def __init__(self):
        super().__init__("physical_filter", "PhysicalFilter")

    def extract(self, gen2id, skyMap, skyMapName):
        return gen2id["filter"]


# Add camera to Gen3 data ID if Gen2 contains "visit" or "ccd".
# (Both rules will match, so we'll actually set camera in the same dict twice).
Translator.addRule(ConstantKeyHandler("camera", "Camera", "HSC"),
                   camera="HSC", gen2keys=("visit",), consume=False)
Translator.addRule(ConstantKeyHandler("camera", "Camera", "HSC"),
                   camera="HSC", gen2keys=("ccd",), consume=False)

# Copy Gen2 'visit' to Gen3 'exposure' for raw only.
Translator.addRule(CopyKeyHandler("exposure", "Exposure", "visit"),
                   camera="HSC", datasetTypeName="raw", gen2keys=("visit",))

# Copy Gen2 'visit' to Gen3 'visit' otherwise
Translator.addRule(CopyKeyHandler("visit", "Visit"), camera="HSC", gen2keys=("visit",))

# Copy Gen2 'ccd' to Gen3 'sensor;
Translator.addRule(CopyKeyHandler("sensor", "Sensor", "ccd"), camera="HSC", gen2keys=("ccd",))

# Translate Gen2 `filter` to AbstractFilter iff Gen2 data ID contains "tract".
Translator.addRule(HscAbstractFilterKeyHandler(), camera="HSC", gen2keys=("tract", "filter"),
                   consume=("filter",))
Translator.addRule(HscPhysicalFilterKeyHandler(), camera="HSC", gen2keys=("filter"))


__all__ = ("ShimButler", )


def _fallbackOnFailure(func):
    """Decorator that wraps a `ShimButler` method and falls back to the
    corresponding Gen2 `Butler` method when an `Exception` is raised.
    """

    def inner(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except NotImplementedError as e:
            log = Log.getLogger("lsst.daf.butler.shimButler")
            log.info("Fallback called for: %s, original call failed with: %s on args=%s, kwargs=%s",
                     func.__name__, e, args, kwargs)
        fallbackFunc = getattr(self._fallbackButler, func.__name__)
        return fallbackFunc(*args, **kwargs)
    return inner


class ShimButlerMeta(type):
    """Metaclass for ShimButler to also forward static and classmethods to
    the FallbackButler.
    """
    def __getattr__(cls, name):
        return getattr(FallbackButler, name)


class ShimButler(metaclass=ShimButlerMeta):
    """Shim around Butler that acts as a Gen2 Butler.

    TODO until implementation is complete we fall back to a Gen2 Butler
    instance upon receiving an unimplemented call.
    """
    def __init__(self, butler, fallbackButler=None):
        self._butler = butler
        self._fallbackButler = fallbackButler
        self._translators = {}
        self._camera = "HSC"

    def _mapDatasetType(self, datasetType):
        log = Log.getLogger("lsst.daf.butler.shimButler")
        log.info("mapping datasetType: %s", datasetType)
        return datasetType

    def _mapDataId(self, datasetType, dataId):
        log = Log.getLogger("lsst.daf.butler.shimButler")
        log.info("mapping datasetType: %s with dataId: %s", datasetType, dataId)
        if "raw" == datasetType:
            raise NotImplementedError(
                "Skipping {}, do not know what to do with raw yet".format(datasetType))
        if "Coadd" in datasetType:
            raise NotImplementedError(
                "Skipping {}, do not know what to do with Coadds yet".format(datasetType))
        if "config" in datasetType:
            raise NotImplementedError(
                "Skipping {}, do not know what to do with configs yet".format(datasetType))
        # Make (or look up) a Translator to go from Gen2 -> Gen3 DataId
        if datasetType not in self._translators:
            gen2dst = Gen2DatasetType(name=datasetType,
                                      keys={k: type(v) for k, v in dataId.items()},
                                      persistable=None,
                                      python=None)
            self._translators[datasetType] = Translator.makeMatching(camera=self._camera,
                                                                     datasetType=gen2dst,
                                                                     skyMapNames={},
                                                                     skyMaps={})
        newId = self._translators[datasetType](dataId)
        newId["camera"] = self._camera  # TODO this should be added automatically?
        log.info("mapped datasetType %s with dataId %s to %s", datasetType, dataId, newId)
        return newId

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
        if dataId is None:
            inputId = {}
        else:
            inputId = dataId.copy()
        inputId.update(**rest)
        try:
            self._butler.registry.getDatasetType(datasetType)
        except KeyError:
            with open("get.txt", "a") as f:
                f.write("{}, {}\n".format(datasetType, {k: str(type(v)) for k, v in inputId.items()}))
            raise NotImplementedError("Skipped, do not have DatasetType {}".format(datasetType))
        value = self._butler.get(datasetType=self._mapDatasetType(datasetType),
                                 dataId=self._mapDataId(datasetType, inputId))
        # Exposure needs to have detector set which is not persistable (yet).
        # The only way to get it currently is from the fallback butler.
        if hasattr(value, 'setDetector'):
            camera = self._fallbackButler.get('camera')
            value.setDetector(camera[int(inputId['ccd'])])
        log = Log.getLogger("lsst.daf.butler.shimButler")
        log.info("Succeeded in get of datasetType: {} with dataId: {}, rest: {}, returns: {}".format(
            datasetType,
            inputId,
            rest,
            value))
        return value

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
        if dataId is None:
            inputId = {}
        else:
            inputId = dataId.copy()
        inputId.update(**rest)
        try:
            self._butler.registry.getDatasetType(datasetType)
        except KeyError:
            with open("put.txt", "a") as f:
                f.write("{}, {}\n".format(datasetType, {k: str(type(v)) for k, v in inputId.items()}))
            raise NotImplementedError("Skipped, do not have DatasetType {}".format(datasetType))
        self._butler.put(obj,
                         datasetType=self._mapDatasetType(datasetType),
                         dataId=self._mapDataId(datasetType, inputId))
        log = Log.getLogger("lsst.daf.butler.shimButler")
        log.info("Succeeded in put of datasetType: {} with dataId: {}, rest: {}".format(datasetType,
                                                                                        inputId, rest))
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
            raise AttributeError()
        return getattr(self._fallbackButler, name)
