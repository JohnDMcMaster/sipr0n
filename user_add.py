#!/usr/bin/env python3

import shutil
import os
import glob
from sipr0n import util
from sipr0n import env
from sipr0n.util import validate_username
from sipr0n.metadata import assert_collection_exists
import dw_add_user
import json


def users():
    ret = {}
    user_fn = env.WWW_DIR + "/archive/conf/users.auth.php"
    with open(user_fn, "r") as f:
        for l in f:
            l = l.strip()
            if not l:
                continue
            if "#" in l:
                continue
            user, _hash, _name, _email, groups = l.strip().split(":")
            if not user:
                continue
            ret[user] = set(groups.split(","))
    return ret    


def run(user=None, dry=True, login=True, copyright_=None):
    env.setup_env_default()

    assert user
    if not login:
        print("Not creating / checking login")
    else:
        print("Checking if user exists...")
        # validate_username(user)
        user_index = users()
        if user in user_index:
            print("User account already exists")
            new_password = None
        else:
            # We have a bit of a namespace conflict
            # Make sure there isn't something special in the way
            # ex: you don't create a user named "tool"
            if os.path.exists(f"/var/www/archive/data/pages/{user}"):
                raise ValueError("ERROR: namesapce conflict with user name")
            new_password = dw_add_user.run(user=user, dry=False)
            # re-index after add
            user_index = users()

        assert "tool" in user_index[user], f"User must be part of tool group, got {user_index[user]}"

    def update_copyright():
        # This could be added here
        if copyright_:
            copyright_fn = env.WWW_DIR + "/archive/data/pages/tool/copyright.txt"
            assert os.path.exists(copyright_fn)
            with open(copyright_fn, "r") as f:
                full = f.read()
            assert f" {user} " not in full, "duplicate user add?"
            new = f"\n| {user}     | {copyright_}                                        |       |\n"
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
{{{{FileSharing>simapper/{user}}}}}

====== Log ======
"""
        log_fn = env.WWW_DIR + f"/archive/data/pages/tool/simapper/{user}.txt"
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
{{{{FileSharing>sipager/{user}}}}}

====== Log ======
"""
        log_fn = env.WWW_DIR + f"/archive/data/pages/tool/sipager/{user}.txt"
        if not dry:
            with open(log_fn, "w") as f:
                f.write(log_template)


    def add_user_page():
        user_dir = env.WWW_DIR + f"/archive/data/pages/{user}"
        assert not os.path.exists(user_dir)
        user_page_fn = user_dir + "/start.txt"
        full = """\
{{tag>collection}}

Data is released under a """ + copyright_ + """ license unless otherwise specified.

Images:

{{topic>collection_""" + user + """}}
"""
        if not dry:
            os.mkdir(user_dir)
            with open(user_page_fn, "w") as f:
                f.write(full)


    update_simapper()
    update_sipager()
    add_user_page()

    if login:
        print(f"Account created for {user}")
        print(f"{user} / {new_password}")
        print("Your namespace / home page is here. Feel free to edit it as you like")
        print(f"https://siliconpr0n.org/archive/doku.php?id={user}:start")
        print(f"This page contains information on quickly uploading images")
        print(f"Please also check out the tool pages there for additional information such as naming rules")
        print("https://siliconpr0n.org/archive/doku.php?id=tool:start")
        print("  Direct link to upload high resolution image (ex: big die scan):")
        print(f"  https://siliconpr0n.org/archive/doku.php?id=tool:simapper:{user}")
        print("  Direct link to upload misc wiki images (ex: package):")
        print(f"  https://siliconpr0n.org/archive/doku.php?id=tool:sipager:{user}")
        print(f"More general info can be found here:")
        print("https://siliconpr0n.org/archive/doku.php?id=your_first_page")
    else:
        print(f"Upload stubs created for {user}")
        print(f"https://siliconpr0n.org/archive/doku.php?id={user}:start")
        print(f"  https://siliconpr0n.org/archive/doku.php?id=tool:simapper:{user}")
        print(f"  https://siliconpr0n.org/archive/doku.php?id=tool:sipager:{user}")

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Create a user landing page and (optionally) a login to upload assets")
    util.add_bool_arg(parser, "--dry", default=True)
    util.add_bool_arg(parser, "--login", default=True, help="Just the copyright or can the user also log in")
    parser.add_argument("--user", required=True, help="User ID for login and copyright table")
    # Blank if not needed
    parser.add_argument("--copyright", required=True)
    args = parser.parse_args()
    run(user=args.user, copyright_=args.copyright, login=args.login, dry=args.dry)


if __name__ == "__main__":
    main()
