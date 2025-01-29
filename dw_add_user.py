from sipr0n import util
import shutil
import secrets
import string
import hashlib

def generate_password():
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for i in range(20))

def parse_user_file(s):
    users = set()
    for l in s.split("\n"):
        l = l.strip()
        user = l.split(":")[0]
        users.add(user)
    return users

def run(user, dry=True):
    user_file = "/var/www/archive/conf/users.auth.php"
    user_file_bak = "/var/www/archive/conf/users.auth.php.old"
    with open(user_file, "r") as f:
        user_file_string = f.read()
    users = parse_user_file(user_file_string)

    new_user = user
    new_password = generate_password()
    if new_user in users:
        raise ValueError(f"user {new_user} already exists")
    password_hash = hashlib.md5(new_password.encode()).hexdigest()
    real_name = new_user
    email = f"new_user@localhost"
    # use main admin interface to add additional groups
    groups = "user,tool"

    if not dry:
        shutil.copy(user_file, user_file_bak)

    new_line = f"{new_user}:{password_hash}:{real_name}:{email}:{groups}"
    user_file_string += new_line + "\n"
    if not dry:
        with open(user_file, "w") as f:
            f.write(user_file_string)

    print("Added successfully")
    print(f"{new_user} / {new_password}")
    return new_password

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Add a dokuwiki user")
    util.add_bool_arg(parser, "--dry", default=True)
    parser.add_argument("--ignore-errors", action="store_true")
    parser.add_argument("--user")
    #parser.add_argument("fndir")
    args = parser.parse_args()
    run(user=args.user, dry=args.dry)


if __name__ == "__main__":
    main()
