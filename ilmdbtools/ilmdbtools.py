#! /usr/bin/python3
import os, sqlite3
from datetime import datetime, timezone, timedelta
from dateutil.parser import parse as timeparse

dbloc = os.path.join('ilmdb.sqlite')

def CheckDbExits():
    return os.path.isfile(dbloc)


def MakeDBIfNotExists():
    if CheckDbExits():
        print("Using current db located at: {0}".format(dbloc))
    else:
        print("Database didn't exist, creating new one located at: {0}".format(dbloc))
        MakeDB(dbloc)
    return

def MakeDB(loc):
    with open('./ilmdbtools/ilmdb.sqlite.sql', 'r', encoding="utf8") as f:
        t = f.read()
        conn, cursor = sqlGet()
        conn.executescript(t)
    return

def GetStats():
    _, cursor = sqlGet()
    q = "SELECT SUM(Crashed) as Crashed, Sum(Complete) as Done, (Count(*)-Sum(Complete)) AS Remaining, Count(*) AS Total FROM Profiles;"
    row = next(cursor.execute(q))
    crashed = row[0]
    done = row[1]
    remaining = row[2]
    total = row[3]
    return (crashed, done, remaining, total)


def sqlGet():
    conn = sqlite3.connect(dbloc)
    cursor = conn.cursor()
    return conn, cursor

def AddProfiles(profiles, section=None):
    print("Adding {0} profiles to section {1}".format(len(profiles), "" if not section else section.Header))
    q = "INSERT OR IGNORE INTO Profiles (Name) VALUES (?);"
    conn, cursor = sqlGet()

    for prof in profiles:
        cursor.execute(q, (prof.Name,))
        prof.Id = cursor.lastrowid

    if section and section.Id != -1:
        q2 = "INSERT OR IGNORE INTO Section2Profiles (Section, Profile) VALUES (?,?);"
        tups = [(section.Id, x.Id) for x in profiles]
        cursor.executemany(q2, tups)
    conn.commit()
    return

def AddSections(sections):
    q = "INSERT OR IGNORE INTO Sections (Header) VALUES (?);"
    conn, cursor = sqlGet()
    sectionheaders = [(x.Header,) for x in sections]
    for sec in sections:
        cursor.execute(q, (sec.Header,))
        sec.Id = cursor.lastrowid
    conn.commit()
    return

def AddLogins(logins):
    return

def AssignLoginsToSections():
    return

def FetchCrashed():
    return

def SetCrashed(profile, pageid, timeoutDuration=3600):
    ds = str(datetime.now(timezone.utc))
    q = "UPDATE Profiles SET Crashed=1, CursorLocation=?, LastAttempted=? WHERE Name=?"
    conn, cursor = sqlGet()
    tup = (pageid, ds, profile)
    cursor.execute(q, tup)

    q2 = "UPDATE RateLimits SET Timestamp=?, Profile=?, Duration=?"
    tup2=(ds, profile, timeoutDuration)
    cursor.execute(q2, tup2)
    conn.commit()
    return

def CheckRateLimit():
    _, cursor = sqlGet()
    n = datetime.now(timezone.utc)
    q = "SELECT Timestamp, Duration FROM RateLimits LIMIT 1"
    row = next(cursor.execute(q))
    if row:
        then = row[0]
        then = timeparse(then)
        duration = row[1]
        duration = timedelta(seconds=duration)
        expires = then+duration
        limited = expires>n
        timeleft = (expires-n).total_seconds()
        return limited, max(0, timeleft)
    return False, 0

def SetInvalid(profile, reason=404):
    ds = str(datetime.now(timezone.utc))
    q = "UPDATE Profiles SET Invalid=1, LastAttempted=? WHERE Name=?"
    conn, cursor = sqlGet()
    tup = (ds, profile)
    cursor.execute(q, tup)
    conn.commit()
    return

def SetDone(profile):
    ds = str(datetime.now(timezone.utc))
    q = "UPDATE Profiles SET Crashed=0, CursorLocation=0, Complete=1, LastAttempted=? WHERE Name=?"
    conn, cursor = sqlGet()
    tup = (ds, profile)
    cursor.execute(q, tup)
    conn.commit()
    return

def SingleDequeue(ignore_crash=False, skip_crash=False):
    dd = CheckDbExits()
    _, cursor = sqlGet()
    print("ayyy")
    print(cursor)
    q = "SELECT p.Id, p.Name, se.Header, Crashed, CursorLocation FROM profiles AS p JOIN Section2Profiles AS s ON s.Profile=p.Id JOIN Sections as se ON se.Id=s.Section WHERE p.Complete=0 AND p.Invalid=0{0} ORDER BY p.LastAttempted ASC LIMIT 1"
    if ignore_crash:
        q = q.format("")
    elif skip_crash:
        q = q.format(" AND Crashed=0")
    else:
        q = q.format("")
    row = next(cursor.execute(q))
    prof = None
    if row:
        prof = row
    return prof

def MultipleDequeue(amount, ignore_crash=False, skip_crash=False):
    _, cursor = sqlGet()
    q = "SELECT p.Id, p.Name, se.Header, Crashed, CursorLocation FROM profiles AS p JOIN Section2Profiles AS s ON s.Profile=p.Id JOIN Sections as se ON se.Id=s.Section WHERE p.Complete=0 AND p.Invalid=0{0} ORDER BY p.LastAttempted ASC"
    if ignore_crash:
        q = q.format("")
    elif skip_crash:
        q = q.format(" AND Crashed=0")
    else:
        q = q.format("")
    
    if amount > 0:
        q += " LIMIT {0}".format(amount)
    tups = []
    for row in cursor.execute(q):
        if row:
            tups.append(row)
    return tups


def DequeuWholeSection():
    return

def DequeuePartialSection():
    return

def WipeDb():
    conn, cursor = sqlGet()
    q = "SELECT name FROM sqlite_master WHERE type='table' AND name IS NOT 'sqlite_sequence'"
    tables =[]
    for row in cursor.execute(q):
        tables.append(row[0])
    q2 = "DELETE FROM {0};"
    for t in tables:
        cursor.execute(q2.format(t))
    conn.commit()
    return