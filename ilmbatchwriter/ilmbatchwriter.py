import os

def UsernamesFromUrls(lst):
    return [UsernameFromUrl(x.strip()) for x in lst if x.strip()]

def UsernameFromUrl(s):
    numSlash = s.count('/')
    if numSlash == 0:
        uname = s
    elif numSlash == 1:
        idx = s.index('/')
        uname = s[idx+1:]
    elif numSlash >= 2:
        lastSlash = s.rfind('/')
        tmpStr = s[:lastSlash]
        secondSlash = tmpStr.rfind('/')
        uname = s[secondSlash+1:lastSlash]
    else:
        return None
    return uname

def FormatSection(header, basepath, users = [], username=None, password=None):
    h = "[{0}]".format(header)
    uname = "" if not username else "username={0}\n".format(username)
    pword = "" if not password else "password={0}\n".format(password)
    ufirst = ""
    if users:
        ufirst = "users = \n"
        for u in users:
            ufirst += "    {0}: {1}\n".format(u, os.path.join(basepath, u)) 
    sectionString = "{0}\n{1}{2}{3}".format(h, uname, pword, ufirst)
    return sectionString

def ReadUsernameFile(fname):
    lines = []
    with open(fname, 'r', encoding="utf8") as f:
        lines = f.readlines()
    return UsernamesFromUrls(lines)

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Batch ini formatter for instalooter')
    parser.add_argument("-t", "--title", dest="header", type=str)

    pgroup = parser.add_mutually_exclusive_group(required=True)
    pgroup.add_argument("-ps", "--profiles", type=str, dest="profiles", nargs="+")
    pgroup.add_argument("-pf", "--profile_file", type=str, dest="profile_file")

    parser.add_argument("-un", "--username", type=str, required=False)
    parser.add_argument("-pw", "--password", type=str, required=False)

    parser.add_argument("-bp", "--basepath", type=str, default="./", dest="basepath")

    args = parser.parse_args()
    argv = vars(args)
    
    users = []
    if argv["profiles"]:
        users = UsernamesFromUrls(argv["profiles"])
    else:
        users = ReadUsernameFile(argv["profile_file"])
    fromurls = UsernamesFromUrls(users)
    fmt = FormatSection(argv["header"], argv["basepath"], fromurls, argv["username"], argv["password"])
    print(fmt)

if __name__ == "__main__":
    main()