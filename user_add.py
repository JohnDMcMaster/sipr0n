#!/usr/bin/env python3

import shutil
import os
import glob
from sipr0n import util
from sipr0n import env
from sipr0n.util import validate_username
from sipr0n.metadata import assert_collection_exists


def users():
    ret = {}
    user_fn = env.WWW_DIR + "/conf/users.auth.php"
    with open(user_fn, "r") as f:
        for l in f:
            user, _hash, _name, _email, groups = l.strip().split(":")
            if not user:
                continue
            ret[user] = set(groups)
    return ret    


def run(user=None, dry=True, copyright=None):
    env.setup_env_default()

    print("Checking if user exists...")
    # validate_username(user)
    user_index = users()
    assert user in user_index, f"Create user account first for {user}"
    assert "tool" in user_index[user], "User must be part of tool group"

    def update_copyright():
        # This could be added here
        if copyright:
            copyright_fn = env.WWW_DIR + "/archive/data/pages/tool/copyright.txt"
            assert os.path.exists(copyright_fn)
            with open(copyright_fn, "r") as f:
                full = f.read()
            assert f" {user} " not in full, "duplicate user add?"
            new = f"\n| {user}     | {copyright}                                        |       |\n"
            full = full + new
            full = full.replace("\n\n", "\n")
            if not dry:
                with open(copyright_fn, "w") as f:
                    f.write(full)
        else:
            print("Checking if copyright info has been filled out...")
            assert_collection_exists(user)
    update_copyright()

    print("")

    # tool_index_fn = env.WWW_DIR + "/archive/data/pages/tool/start.txt"
    # assert os.path.exists(tool_index_fn)

    def update_simapper():
        index_fn = env.WWW_DIR + "/archive/data/pages/tool/simapper.txt"
        assert os.path.exists(index_fn)
    
        """
          * [[tool:simapper:mcmaster]]
        """    
        with open(index_fn, "r") as f:
            full = f.read()
        ref = "  * [[tool:simapper:mcmaster]]\n"
        new = f"  * [[tool:simapper:{user}]]\n"
        full = full.replace(ref, ref + new)
        if not dry:
            with open(index_fn, "w") as f:
                f.write(full)
        
        log_template = f"""\
{{FileSharing>sipager/{user}}}

====== Log ======
"""
        log_fn = env.WWW_DIR + f"/archive/data/pages/tool/sipager/{user}.txt"
        if not dry:
            with open(log_fn, "w") as f:
                f.write(log_template)

    def update_sipager():
        index_fn = env.WWW_DIR + "/archive/data/pages/tool/sipager.txt"
        assert os.path.exists(index_fn)
        with open(index_fn, "r") as f:
            full = f.read()
        ref = "  * [[tool:sipager:mcmaster]]\n"
        new = f"  * [[tool:sipager:{user}]]\n"
        full = full.replace(ref, ref + new)
        if not dry:
            with open(index_fn, "w") as f:
                f.write(full)


        log_template = f"""\
{{FileSharing>simapper/{user}}}

====== Log ======
"""
        log_fn = env.WWW_DIR + f"/archive/data/pages/tool/simapper/{user}.txt"
        if not dry:
            with open(log_fn, "w") as f:
                f.write(log_template)

    update_simapper()
    update_sipager()

    print(f"Account created for {user}")
    print(f"This page contains information on quickly uploading images")
    print(f"Please also check out the tool pages there for additional information such as naming rules")
    print("https://siliconpr0n.org/archive/doku.php?id=tool:start")
    print("  Direct link to upload high resolution image (ex: big die scan):")
    print(f"  https://siliconpr0n.org/archive/doku.php?id=tool:simapper:{user}")
    print("  Direct link to upload misc wiki images (ex: package):")
    print(f"  https://siliconpr0n.org/archive/doku.php?id=tool:sipager:{user}")
    print(f"More general info can be found here:")
    print("https://siliconpr0n.org/archive/doku.php?id=your_first_page")

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Create a user that can upload assets")
    util.add_bool_arg(parser, "--dry", default=True)
    parser.add_argument("--user", required=True)
    parser.add_argument("--copyright", required=True)
    args = parser.parse_args()
    run(vendor=args.vendor, chipid=args.chipid, user=args.user, copyright=copyright, dry=args.dry)


if __name__ == "__main__":
    main()
