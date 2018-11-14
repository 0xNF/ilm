# ILM - Instalooter Monitor

Instalooter crashes a lot and has no tools for timeout recovery.  
This tool exists to be a monitor for large instagram download sessions where being rate limited or encountering invalid users is likely.

This script is intended to essentially replace the batch option from instalooter.

## Requirements
You must have Instalooter installed and accessible from your shell

## Usage

We assume you have a `users00.txt` file where each line is the full URL to that users instagram page:

| users.txt
```txt 
https://www.instagram.com/fumikoteijo/
https://www.instagram.com/irene.rvelvet/
https://www.instagram.com/hrk.m310/
```

The filename of a users file will become a section. Pictures from a section will be downloaded into a folder named for the section. In our example case, the 3 users will be downloaded to a `/users00/` folder.

### Import Users

First we need to import users into a sqlite file:

```bash
python ./ilm.py -i [files]
```
for example:
```bash
python ./ilm.py -i ./users00.txt ./users01.txt ./users02.txt
```

### Download Multiple Users

The most common usage pattern involves downloading multiple users per invocation of ilm:


```bash
python ./ilm.py -md [num] --skip_crashed
```

for example
```bash
python ./ilm.py -md 50 --skip_crashed
```
This will dequeue 50 users from the database that haven't been downloaded yet and then download them.

If you omit the `num` parameter, the script will dequeue the entire database.

The `--skip_crashed` option tells the dequeue process to skip over any profiles that have already been attempted but failed for one reason or another. This assures that an unmonitored run of ilm won't get stuck trying to download the same half-complete users over and over again.

### Download Single Users

A less common but still useful pattern involves downloading just the next user in the queue:

```bash
python ./ilm.py -sd --skip_crashed
```

### Mocking the download

If you want to see what users will be dequeued and what Instalooter command will be run, you can add the `-m` flag to a command, which will print what would have happened:

```bash
>> python ./ilm.py -sd -m
<< instalooter user fumikoteijo ./pics/batch_test/users00/fumikoteijo
```

# Current Limitations

* There is no current ability to pickup from being rate limited on a given user.
    If you are trying to download a user with more than 20 pages of images, you can't get to the rest. 
* Some errors will crash `ilm`. Any run of Instalooter that produces an error code of 1 will cause ilm to cease execution. You can change this by uncommenting `lines 203 and 204` in `ilm.py`:
    ```python
    #ilmdbtools.SetInvalid(profname, returncode)
    #continue
    ```
    