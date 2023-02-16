import re
import os
import sys


def add_bool_arg(parser, yes_arg, default=False, **kwargs):
    dashed = yes_arg.replace('--', '')
    dest = dashed.replace('-', '_')
    parser.add_argument(yes_arg,
                        dest=dest,
                        action='store_true',
                        default=default,
                        **kwargs)
    parser.add_argument('--no-' + dashed,
                        dest=dest,
                        action='store_false',
                        **kwargs)


class ParseError(Exception):
    pass


"""
Used by sipager/simapper for non-canonical file names with implicit username
They will get transformed into canonical name
"""
"""
Parse an image file name that doesn't have user/collection info
DEPRECATED: will be obsolete soon
"""


#def parse_vendor_chipid_flavor(fn):
def parse_map_image_vcfe(fn):
    # Normalize
    fnbase = os.path.basename(fn).lower()
    m = re.match(r'([a-z0-9\-]+)_([a-z0-9\-]+)_(.*)\.(.+)', fnbase)
    if not m:
        raise ParseError(
            "Non-confirming file name (need vendor_chipid_flavor.jpg): %s" %
            (fn, ))
    vendor = m.group(1)
    chipid = m.group(2)
    flavor = m.group(3)
    ext = m.group(4)
    return (vendor, chipid, flavor, ext)


def map_image_uvcfe_to_basename(vendor, chipid, user, flavor, ext):
    # vendor_chipid_user_flavor.ext
    return vendor + "_" + chipid + "_" + user + "_" + flavor + "." + ext


"""
Parse an image file name that has user/collection info
"""


def parse_map_image_vcufe(fn):
    """
    Canonical name like
    vendor_chipid_user_flavor.ext
    """
    # Normalize
    fnbase = os.path.basename(fn).lower()
    m = re.match(r'([a-z0-9\-]+)_([a-z0-9\-]+)_([a-z0-9\-]+)_(.*)\.(.+)',
                 fnbase)
    if not m:
        raise ParseError(
            "Non-confirming file name (need vendor_chipid_flavor.jpg): %s" %
            (fn, ))
    vendor = m.group(1)
    chipid = m.group(2)
    user = m.group(3)
    flavor = m.group(4)
    ext = m.group(5)
    return (vendor, chipid, user, flavor, ext)


def parse_map_url_vc(url):
    if url.lower() != url:
        raise Exception("Found uppercase in URL: %s" % (url, ))
    m = re.search(r'siliconpr0n.org/map/([_a-z0-9\-]+)/([_a-z0-9\-]+)/', url)
    if not m:
        raise Exception("Non-confirming map URL file name: %s" % (url, ))
    vendor = m.group(1)
    chipid = m.group(2)
    return (vendor, chipid)


def parse_map_url_vcuf(url):
    if url.lower() != url:
        raise Exception("Found uppercase in URL: %s" % (url, ))
    m = re.search(
        r'map/([_a-z0-9\-]+)/([_a-z0-9\-]+)/([a-z0-9\-]+)_([_a-z0-9\-]+)/index.html',
        url)
    if not m:
        raise Exception("Non-confirming map URL file name: %s" % (url, ))
    vendor = m.group(1)
    chipid = m.group(2)
    user = m.group(3)
    flavor = m.group(4)
    return (vendor, chipid, user, flavor)


def parse_map_local_vc(url):
    if url.lower() != url:
        raise Exception("Found uppercase in URL: %s" % (url, ))
    m = re.search(r'www/map/([_a-z0-9\-]+)/([_a-z0-9\-]+)/', url)
    if not m:
        raise Exception("Non-confirming map URL file name: %s" % (url, ))
    vendor = m.group(1)
    chipid = m.group(2)
    return (vendor, chipid)


def parse_single_url_vc(url):
    m = re.search(
        r'siliconpr0n.org/map/([_a-z0-9\-]+)/([_a-z0-9\-]+)/single/([a-z0-9\-]+)_([a-z0-9\-]+)',
        url)
    if not m:
        raise Exception("Non-confirming file name: %s" % (url, ))
    _vendor = m.group(1)
    _chipid = m.group(2)
    vendor = m.group(3)
    chipid = m.group(4)
    return (vendor, chipid)


"""
mcmaster_mz_mit20x => (mcmaster, mz_mit20x)
"""


def parse_map_basename_uf(url):
    m = re.search(r'([a-z0-9\-]+)_([_a-z0-9\-]+)', url)
    if not m:
        raise Exception("Non-confirming file name: %s" % (url, ))
    user = m.group(1)
    flavor = m.group(2)
    return (user, flavor)


def parse_map_image_user_vcufe(fn_can, assume_user):
    if assume_user:
        parsed = parse_map_image_vcfe(fn_can)
        basename, vendor, chipid, flavor, ext = parsed
        user = assume_user
    else:
        parsed = parse_map_image_vcufe(fn_can)
        basename, vendor, chipid, user, flavor, ext = parsed
    return (basename, vendor, chipid, user, flavor, ext)


"""
Wiki page images
Currently these use more or less the same naming convention

ex:
intel_80c186_mcmaster_mz_mit20x.jpg
as map: intel/80c186/mcmaster_mz_mit20x/
as wiki: mcmaster/intel/80c186/mz_mit20x.jpg
Its up to higher level logic to chop it up
"""


def parse_wiki_image_vcfe(fn):
    return parse_map_image_vcufe(fn)


def wiki_image_fe_to_dirbase(vendor, chipid, user, flavor, ext):
    dirname = user + "/" + vendor + "/" + chipid
    basename = flavor + "." + ext
    return dirname, basename


def parse_wiki_image_vcufe(fn):
    return parse_map_image_vcufe(fn)


def parse_wiki_image_user_vcufe(fn_can, assume_user):
    return parse_map_image_user_vcufe(fn_can, assume_user)


def validate_username(username):
    return re.match("[a-z]+", username)


def tobytes(buff):
    if type(buff) is str:
        #return bytearray(buff, 'ascii')
        return bytearray([ord(c) for c in buff])
    elif type(buff) is bytearray or type(buff) is bytes:
        return buff
    else:
        assert 0, type(buff)


def tostr(buff):
    if type(buff) is str:
        return buff
    elif type(buff) is bytearray or type(buff) is bytes:
        return ''.join([chr(b) for b in buff])
    else:
        assert 0, type(buff)


# Log file descriptor to file
class IOLog(object):
    def __init__(self,
                 obj=sys,
                 name='stdout',
                 out_fn=None,
                 out_fd=None,
                 mode='a'):
        if out_fd:
            self.out_fd = out_fd
        else:
            self.out_fd = open(out_fn, 'w')

        self.obj = obj
        self.name = name

        self.fd = obj.__dict__[name]
        obj.__dict__[name] = self
        self.nl = True

    def __del__(self):
        if self.obj:
            self.obj.__dict__[self.name] = self.fd

    def flush(self):
        self.fd.flush()

    def write(self, data):
        self.fd.write(data)
        self.out_fd.write(data)


def make_iolog(out_fn):
    outlog = IOLog(obj=sys, name='stdout', out_fn=out_fn, mode='a')
    errlog = IOLog(obj=sys, name='stderr', out_fd=outlog.out_fd)
    return (outlog, errlog)


"""
Used to manage whether a filename should be retried on bad upload
Prevents CPU overloading and spamming log file
"""


class FnRetry:
    def __init__(self):
        # filename to modtime
        self.tried = {}

    def should_try_fn(self, fn):
        """
        If the filename is newer and hasn't been blacklisted
        """
        new_mtime = os.path.getmtime(fn)
        old_mtime = self.tried.get(fn)
        if old_mtime and (old_mtime == True or old_mtime == new_mtime):
            return False
        return True

    def try_fn(self, fn):
        """
        Like above, but also note it as attempted
        """
        new_mtime = os.path.getmtime(fn)
        old_mtime = self.tried.get(fn)
        if old_mtime and (old_mtime == True or old_mtime == new_mtime):
            return False
        self.tried[fn] = new_mtime
        return True

    def blacklist_fn(self, fn):
        """
        Something unrecoverable
        Ex: bad user database
        Need to think how to handle this better
        """
        self.tried[fn] = True


class VCMismatch(Exception):
    pass
