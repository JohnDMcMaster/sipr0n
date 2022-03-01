import os

WWW_DIR = None
SIPAGER_DIRS = None
WIKI_NS_DIR = None
WIKI_DIR = None
MAP_DIR = None
HI_SCRAPE_DIRS = None
# simapper wiki page
WIKI_PAGE = None
COPYRIGHT_TXT = None


def setup_env(dev=False, remote=False):
    global WWW_DIR
    # Directory containing high resolution maps
    global MAP_DIR
    global WIKI_DIR
    # Directory containing simapper pages
    global WIKI_NS_DIR
    # File holding manual import table
    global WIKI_PAGE
    # List of directories to look for high resolution images
    # Must be in a sub-directory with the user that wants to import it
    global HI_SCRAPE_DIRS
    global SIPAGER_DIRS
    global COPYRIGHT_TXT

    # XXX: consider removing this now that have unit test
    assert not remote

    # Production
    WWW_DIR = "/var/www"
    # Production debugged remotely
    # discouraged, used for intiial testing mostly
    if remote:
        WWW_DIR = "/mnt/si/var/www"
    # Local development
    if dev:
        WWW_DIR = os.getcwd() + "/dev"
    assert os.path.exists(WWW_DIR), "Failed to find " + WWW_DIR

    MAP_DIR = WWW_DIR + "/map"
    assert os.path.exists(MAP_DIR), MAP_DIR
    WIKI_DIR = WWW_DIR + "/archive"
    WIKI_NS_DIR = WWW_DIR + "/archive/data/pages/simapper"
    assert os.path.exists(WIKI_NS_DIR), WIKI_NS_DIR
    WIKI_PAGE = WIKI_NS_DIR + "/start.txt"
    assert os.path.exists(WIKI_PAGE), WIKI_PAGE
    # TODO: consider SFTP bridge
    HI_SCRAPE_DIRS = [WWW_DIR + "/uploadtmp/simapper"]
    for d in HI_SCRAPE_DIRS:
        assert os.path.exists(d), d
    SIPAGER_DIRS = [WWW_DIR + "/uploadtmp/sipager"]
    for d in HI_SCRAPE_DIRS:
        assert os.path.exists(d), d
    # TODO: create a way to quickly import low resolution images
    # Add the image directly to the page

    # but good enough right now
    COPYRIGHT_TXT = WWW_DIR + "/archive/data/pages/simapper/copyright.txt"

    # print_log_break()
    print("Environment:")
    print("  WWW_DIR: ", WWW_DIR)
    print("  MAP_DIR: ", MAP_DIR)
    print("  WIKI_PAGE: ", WIKI_PAGE)
    print("  HI_SCRAPE_DIRS: ", HI_SCRAPE_DIRS)
    print("  SIPAGER_DIRS: ", SIPAGER_DIRS)
