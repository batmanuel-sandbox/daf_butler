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

import pickle
import unittest
import lsst.utils.tests

import lsst.daf.butler.core.storageClass as storageClass

"""Tests related to the StorageClass infrastructure.
"""


class PythonType:
    """A dummy class to test the registry of Python types."""
    pass


class StorageClassFactoryTestCase(lsst.utils.tests.TestCase):
    """Tests of the storage class infrastructure.
    """

    def testCreation(self):
        """Test that we can dynamically create storage class subclasses.

        This is critical for testing the factory functions."""
        className = "TestImage"
        sc = storageClass.StorageClass(className, pytype=dict)
        self.assertIsInstance(sc, storageClass.StorageClass)
        self.assertEqual(sc.name, className)
        self.assertFalse(sc.components)
        # Check we can create a storageClass using the name of an importable
        # type.
        sc2 = storageClass.StorageClass("TestImage2",
                                        "lsst.daf.butler.core.storageClass.StorageClassFactory")
        self.assertIsInstance(sc2.pytype(), storageClass.StorageClassFactory)

    def testRegistry(self):
        """Check that storage classes can be created on the fly and stored
        in a registry."""
        className = "TestImage"
        factory = storageClass.StorageClassFactory()
        newclass = storageClass.StorageClass(className, pytype=PythonType)
        factory.registerStorageClass(newclass)
        sc = factory.getStorageClass(className)
        self.assertIsInstance(sc, storageClass.StorageClass)
        self.assertEqual(sc.name, className)
        self.assertFalse(sc.components)
        self.assertEqual(sc.pytype, PythonType)

    def testPickle(self):
        """Test that we can pickle storageclasses.
        """
        className = "TestImage"
        sc = storageClass.StorageClass(className, pytype=dict)
        self.assertIsInstance(sc, storageClass.StorageClass)
        self.assertEqual(sc.name, className)
        self.assertFalse(sc.components)
        sc2 = pickle.loads(pickle.dumps(sc))
        self.assertEqual(sc2, sc)


class MemoryTester(lsst.utils.tests.MemoryTestCase):
    pass


def setup_module(module):
    lsst.utils.tests.init()


if __name__ == "__main__":
    lsst.utils.tests.init()
    unittest.main()
