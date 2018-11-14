#! /usr/bin/python3
import subprocess as sp
import os, csv, json, sqlite3, sys
import time
from ilmdbtools import ilmdbtools
from ilmbatchwriter import ilmbatchwriter

basedir = "./pics/batch_test"

class Profile():
    def __init__(self, name, location="", id=-1, crashed=False, crashedAt=0, lastAttempted=0):
        self.Name = name
        self.Id = id
        self.Location = location
        self.Crashed = crashed
        self.CrashedAt = crashedAt
        self.LastAttempetd = lastAttempted

    def __str__(self):
        s = """Profile: {{name: {0}, loc: {1}, id: {2}, crashed: {3}, crashedAt: {4}, lastAttempted: {5}}}"""
        return s.format(self.Name, self.Location, self.Id, self.Crashed, self.CrashedAt, self.LastAttempetd)

class Login():
    def __init__(self, username, password=None):
        self.Username = username
        self.Password = password
        self.Id = -1
        return

class Section():
    def __init__(self, header, login = None):
        self.Header = header
        self.Login = login
        self.Id = -1
        return

def ReadProfiles(fname):
    lines = [x.strip() for x in fname.readlines() if x]
    unames = ilmbatchwriter.UsernamesFromUrls(lines)
    profs = [Profile(x) for x in unames]
    return profs

def parseargs():
    import argparse
    parser = argparse.ArgumentParser(description='Monitor script for Instalooter')
    mut = parser.add_mutually_exclusive_group()

    adminStuff = mut.add_mutually_exclusive_group()
    adminStuff.add_argument("--wipe_db", action="store_true", dest="wipedb", help="Wipes the monitor db. All profile, section and login information will be erased.")
    adminStuff.add_argument("--stats", dest="getstats", action="store_true", help="Prints the number of crashed profiles, the number of complete profiles, and the number of remaining profiles")
    adminStuff.add_argument('-i', "--input", type=argparse.FileType('r', encoding="utf8"), nargs='+', dest="inpath")

    performStuff = mut.add_argument_group()
    crashOptions = performStuff.add_mutually_exclusive_group()
    crashOptions.add_argument("--ignore_crashed", action="store_true", dest="ignore_crash", help="Will download crashed profiles from page 0 instead of picking up at last crash page. This is a separate option from --skip_crash.")
    crashOptions.add_argument("--skip_crashed", action="store_true", dest="skip_crash", help="Will skip downloading any crashed profiles. This is a separate option from --ignore_crash.")

    performStuff.add_argument("-m", "--mock", dest="mock", action="store_true", help="Only shows what would be processed, doesn't actually send anything to Instalooter.")

    MDorSD = performStuff.add_mutually_exclusive_group()
    MDorSD.add_argument("-sd", "--single_dequeue", dest="sd", action="store_true", help="Takes a single profile from the db and downloads it.")
    MDorSD.add_argument("-md", "--multiple_dequeue", dest="md", type=int, default=0, help="Runs through the queue until there are no items left. Sets timeouts for rate limits")

    argv = vars(parser.parse_args())
    return argv

def GetStats():
    s = ilmdbtools.GetStats()
    s = "Crashed: {0}\nDone: {1}\nRemaining: {2}\nTotal: {3}".format(s[0], s[1], s[2], s[3])
    print(s)
    return

def WipeDb():
    print("Are you sure you want to wipe the database? This action cannot be undone.\nType 'y' or 'yes' to continue. Any other input will cancel.")
    answer = input()
    if(answer == "y" or answer == "yes"):
        ilmdbtools.WipeDb()
        print("Wiped database successfully")
    else:
        print("Aborted database wipe.")
    return

# TODO turn this into cli arg
AddUsers = True

_TimeoutInMinutes=31
TIMEOUT = 60*_TimeoutInMinutes

def main():
    argv = parseargs()
    if argv["getstats"]:
        GetStats()
        exit(0)
    elif argv["wipedb"]:
        WipeDb()
        exit(0)
    files = argv["inpath"]
    if files:
        # Create DB if not Exist
        ilmdbtools.MakeDBIfNotExists()
        for f in files:
            fn = os.path.splitext(os.path.basename(f.name))[0]
            # Read profiles into database
            if AddUsers:
                profiles = ReadProfiles(f)
                section = Section(fn)
                ilmdbtools.AddSections([section])
                ilmdbtools.AddProfiles(profiles, section)
    elif argv["sd"]:
        tup = ilmdbtools.SingleDequeue(ignore_crash = argv["ignore_crash"], skip_crash=argv["skip_crash"])
        if tup:
            loc = os.path.join(basedir, tup[2])
            profid = tup[0]
            profname = tup[1]
            crashed = tup[3] == 1
            crashedAt = tup[4]
            prof = Profile(profname, loc, profid, crashed, crashedAt)
            loc = os.path.join(prof.Location, prof.Name)
            if(argv["mock"]):
                s = "instalooter user {0} {1}".format(prof.Name, loc)
                print(s)
                return 0
            ratelimited, timeleft = ilmdbtools.CheckRateLimit()
            if ratelimited:
                print("Still rate limited for another {0} seconds".format(timeleft))
                return 0
            print("ilm: preparing to run the following command: instalooter user {0} {1}".format(prof.Name, loc))
            returncode = sp.call(["instalooter", "user", prof.Name, loc])
            if returncode == 429 or returncode == 173: # Rate Limited
                print("Rate limited.")
                crashedAt = -1 # TODO need to update instalooter to respond with last known page
                ilmdbtools.SetCrashed(profname, crashedAt)
            elif returncode == 404 or returncode == 403 or returncode == 148:
                print("user not found")
                ilmdbtools.SetInvalid(profname, returncode)
            elif returncode == 0:
                print("Done")
                ilmdbtools.SetDone(profname)
            elif returncode == 503: # timeout, il got killed
                print("Timeout ocurred.")
            else:
                print("err:")
                print(returncode)
                print("An error happened.")
        else:
            print("Failed to single dequeue user")
    elif argv["md"] is not None and argv["md"] >= 0:
        print("Will run for each user dequeued.")
        print(argv["md"])
        md = argv["md"]
        profiles = ilmdbtools.MultipleDequeue(md, ignore_crash = argv["ignore_crash"], skip_crash=argv["skip_crash"])
        if not profiles:
            print("There were no items left in the database to dequeue")
            return 0
        print("Begining a multiple dequeue session")
        for profile in profiles:
            loc = os.path.join(basedir, profile[2])
            profid = profile[0]
            profname = profile[1]
            crashed = profile[3] == 1
            crashedAt = profile[4]
            prof = Profile(profname, loc, profid, crashed, crashedAt)
            loc = os.path.join(prof.Location, prof.Name)
            if(argv["mock"]):
                s = "instalooter user {0} {1}".format(prof.Name, loc)
                print(s)
                continue
            ratelimited, timeleft = ilmdbtools.CheckRateLimit()
            if ratelimited:
                print("Still rate limited for another {0} seconds".format(timeleft))
                print("Sleeping thread...")
                time.sleep(timeleft)
                print("Continuing exection")
            print("ilm: preparing to run the following command: instalooter user {0} {1}".format(prof.Name, loc))
            returncode = sp.call(["instalooter", "user", prof.Name, loc])
            if returncode == 429 or returncode == 173: # Rate Limited
                print("Rate limited.")
                crashedAt = -1 # TODO need to update instalooter to respond with last known page
                ilmdbtools.SetCrashed(profname, crashedAt, TIMEOUT)
                print("Sleeping thread for {0} seconds...".format(TIMEOUT))
                time.sleep(TIMEOUT)
                print("Continuing exection")
                continue
            elif returncode == 404 or returncode == 148:
                print("user not found")
                ilmdbtools.SetInvalid(profname, returncode)
                continue
            elif returncode == 403 or returncode == 147:
                print("User is private")
                ilmdbtools.SetInvalid(profname, returncode)
                continue
            elif returncode == 0:
                print("Done")
                ilmdbtools.SetDone(profname)
                continue
            elif returncode == 503: # timeout, il got killed
                print("Timeout ocurred - ceasing execution")
                ilmdbtools.SetCrashed(profname, 0, TIMEOUT)
                return 503
            else:
                print("err:")
                print(returncode)
                #ilmdbtools.SetInvalid(profname, returncode)
                #continue
                return 500
        print("Finished downloading users in queue")
        return 0

        # Crash Conditions:
        #   If instalooter returns an error code isn't (429,173), (404,403,148), (0), (503)
        # Timeout conditions:
        #   if Instalooter returns (429,173)
        # Stop Conditions:
        #   if MultipleDequeue returns empty.
        #   if the queue is emptied

    return 0

if __name__ == "__main__":
    sys.exit(main())