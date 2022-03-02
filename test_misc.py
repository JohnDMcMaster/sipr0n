#!/usr/bin/env python3

import unittest
import os
import shutil
import sipager
import simapper


def rm_f(fn):
    try:
        os.unlink(fn)
    except FileNotFoundError:
        pass


def rm_rf(fn):
    shutil.rmtree(fn, ignore_errors=True)


def cp(src, dst):
    shutil.copy(src, dst)


def cp_r(src, dst):
    shutil.copytree(src, dst)


def setup_wiki():
    os.makedirs("dev/map", exist_ok=True)
    os.makedirs("dev/archive/data/media", exist_ok=True)
    os.makedirs("dev/archive/data/pages/tool", exist_ok=True)
    os.makedirs("dev/archive/data/pages/tool/sipager", exist_ok=True)
    os.makedirs("dev/archive/data/pages/tool/simapper", exist_ok=True)
    # os.makedirs("dev/archive/data/pages/protected", exist_ok=True)
    os.makedirs("dev/uploadtmp/sipager/mcmaster", exist_ok=True)
    os.makedirs("dev/uploadtmp/simapper/mcmaster", exist_ok=True)
    shutil.copy("test/copyright.txt", "dev/archive/data/pages/tool/")


def cleanup():
    rm_rf("dev")


class TestCase(unittest.TestCase):
    def setUp(self):
        """Call before every test case."""
        print("")
        print("")
        print("")
        print("Start " + self._testMethodName)
        self.verbose = os.getenv("VERBOSE", "N") == "Y"
        cleanup()
        setup_wiki()

    def tearDown(self):
        """Call after every test case."""
        # cleanup()

    def test_sipager_jpg_canonical(self):
        """
        Canonical file names should work in root dir
        """
        shutil.copy("test/sipager/mcmaster_atmel_at328p_die.jpg",
                    "dev/uploadtmp/sipager/")
        sipager.run(dev=True, once=True, verbose=self.verbose)
        assert os.path.exists(
            "./dev/archive/data/pages/mcmaster/atmel/at328p.txt")

    def test_sipager_jpg_user(self):
        """
        User directories can be used to assume file prefix
        """
        shutil.copy("test/sipager/mcmaster_atmel_at328p_die.jpg",
                    "dev/uploadtmp/sipager/mcmaster/atmel_at328p_die.jpg")
        sipager.run(dev=True, once=True, verbose=self.verbose)
        assert os.path.exists(
            "./dev/archive/data/pages/mcmaster/atmel/at328p.txt")

    def test_sipager_tar_canonical(self):
        """
        Should be able to upload multiple files at once using a tar
        """
        shutil.copy("test/sipager/mcmaster_atmel_at328p_packs.tar",
                    "dev/uploadtmp/sipager/")
        sipager.run(dev=True, once=True, verbose=self.verbose)
        assert os.path.exists(
            "./dev/archive/data/pages/mcmaster/atmel/at328p.txt")

    def test_sipager_tar_user(self):
        """
        Should be able to upload multiple files at once using a tar
        """
        shutil.copy("test/sipager/atmel_at328p_packs.tar",
                    "dev/uploadtmp/sipager/mcmaster/")
        sipager.run(dev=True, once=True, verbose=self.verbose)
        assert os.path.exists(
            "./dev/archive/data/pages/mcmaster/atmel/at328p.txt")

    def test_sipager_tar_jpg_mixed(self):
        """
        Mixing jpgs and tar should be fine
        (although probably rarely used in practice)
        """
        shutil.copy("test/sipager/mcmaster_atmel_at328p_packs.tar",
                    "dev/uploadtmp/sipager/")
        shutil.copy("test/sipager/mcmaster_atmel_at328p_die.jpg",
                    "dev/uploadtmp/sipager/")
        sipager.run(dev=True, once=True, verbose=self.verbose)
        assert os.path.exists(
            "./dev/archive/data/pages/mcmaster/atmel/at328p.txt")

    def test_sipager_append(self):
        """
        Existing page should just append
        """

        print("pass 1")
        shutil.copy("test/sipager/mcmaster_atmel_at328p_die.jpg",
                    "dev/uploadtmp/sipager/mcmaster_atmel_at328p_die.jpg")
        sipager.run(dev=True, once=True, verbose=self.verbose)
        assert os.path.exists(
            "./dev/archive/data/pages/mcmaster/atmel/at328p.txt")

        print("pass 2")
        shutil.copy("test/sipager/mcmaster_atmel_at328p_die.jpg",
                    "dev/uploadtmp/sipager/mcmaster_atmel_at328p_die2.jpg")
        sipager.run(dev=True, once=True, verbose=self.verbose)
        assert os.path.exists(
            "./dev/archive/data/pages/mcmaster/atmel/at328p.txt")

    def test_simapper_user(self):
        shutil.copy("test/sipager/mcmaster_atmel_at328p_die.jpg",
                    "dev/uploadtmp/simapper/mcmaster/atmel_at328p_mz3.jpg")
        assert os.path.exists(
            "dev/uploadtmp/simapper/mcmaster/atmel_at328p_mz3.jpg")
        simapper.run(dev=True, once=True, verbose=self.verbose)
        assert os.path.exists("./dev/map/atmel/at328p/mz3/index.html")
        # logged?
        assert os.path.exists(
            "./dev/archive/data/pages/tool/simapper/mcmaster.txt")

    def test_simapper_append(self):
        """
        Existing page should just append
        """
        shutil.copy("test/sipager/mcmaster_atmel_at328p_die.jpg",
                    "dev/uploadtmp/simapper/mcmaster/atmel_at328p_mz.jpg")
        simapper.run(dev=True, once=True, verbose=self.verbose)
        assert os.path.exists("./dev/map/atmel/at328p/mz/index.html")

        shutil.copy("test/sipager/mcmaster_atmel_at328p_die.jpg",
                    "dev/uploadtmp/simapper/mcmaster/atmel_at328p_mz2.jpg")
        simapper.run(dev=True, once=True, verbose=self.verbose)
        assert os.path.exists("./dev/map/atmel/at328p/mz/index.html")


if __name__ == "__main__":
    unittest.main()  # run all tests
