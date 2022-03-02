import os

WWW_DIR = None
# Directory containing high resolution maps
# ex: /var/www/map
MAP_DIR = None
# List of directories to ingest into simapper service
SIMAPPER_DIR = None
# List of directories to ingest into sipager service
SIPAGER_DIR = None
COPYRIGHT_TXT = None
ARCHIVE_WIKI_DIR = None
ARCHIVE_TOOL_DIR = None
SIMAPPER_USER_DIR = None
SIPAGER_USER_DIR = None


def setup_env(dev=False, remote=False):
    global WWW_DIR
    global MAP_DIR
    global ARCHIVE_WIKI_DIR
    global SIMAPPER_DIR
    global SIPAGER_DIR
    global COPYRIGHT_TXT
    global WIKI_TOOL_DIR
    global SIMAPPER_USER_DIR
    global SIPAGER_USER_DIR

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

    # simapper
    MAP_DIR = WWW_DIR + "/map"
    # tmp dirs
    assert os.path.exists(MAP_DIR), MAP_DIR
    SIMAPPER_DIR = WWW_DIR + "/uploadtmp/simapper"
    assert os.path.exists(SIMAPPER_DIR), SIMAPPER_DIR
    SIPAGER_DIR = WWW_DIR + "/uploadtmp/sipager"
    assert os.path.exists(SIPAGER_DIR), SIPAGER_DIR

    # shared archive folders
    ARCHIVE_WIKI_DIR = WWW_DIR + "/archive"
    ARCHIVE_TOOL_DIR = WWW_DIR + "/archive/data/pages/tool"
    assert os.path.exists(ARCHIVE_TOOL_DIR), ARCHIVE_TOOL_DIR
    SIMAPPER_USER_DIR = WWW_DIR + "/archive/data/pages/tool/simapper"
    assert os.path.exists(SIMAPPER_USER_DIR), SIMAPPER_USER_DIR
    SIPAGER_USER_DIR = WWW_DIR + "/archive/data/pages/tool/sipager"
    assert os.path.exists(SIPAGER_USER_DIR), SIPAGER_USER_DIR
    # but good enough right now
    COPYRIGHT_TXT = WWW_DIR + "/archive/data/pages/tool/copyright.txt"

    print("Environment:")
    print("  WWW_DIR: ", WWW_DIR)
    print("  MAP_DIR: ", MAP_DIR)
    print("  SIMAPPER_DIR: ", SIMAPPER_DIR)
    print("  SIPAGER_DIR: ", SIPAGER_DIR)
