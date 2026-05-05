## Getting my own firewall to work on a new fresh installed Mac OS 11 - 26 

### One time:

Install: Python3.14 (by letting a Mac package do it's magic so it won't interfere with the Mac sometimes still using python2.9.6 scripts), Homebrew, Node.js  

then: log out of user account, log back in.
Open Terminal.

```
~ % brew update

~ % brew upgrade
```
Basic installs are now done. Now we make for this, and future use, a folder for all projects and 1 specifically for the firewall app:

```
~ % mkdir ~/Developer

~ % mkdir ~/Developer/WireFall
```

Then we need to install "pyQt6" (pie-cutie-six) in a temporary virtual enviroment.

```
~ % cd /Developer/Wirefall

WireFall % python3 -m venv venv

WireFall % source venv/bin/activate

(venv) % pip3 install pyQt6 psutil
```

Then we log user out & back in.
Open Terminal.
Then we get your fantastic script in the right folder:

```
~ % cp ~/Documents/Coding & (Apple) Scripts/DankjewelClaude/Nerdathron3000.py ~/Developer/Wirefall

~ % cd ~/Developer/Wirefall

WireFall % source venv/bin/activate

(venv) % python3 nerdathron3000.py

(venv) % deactivate
```

---
The 1-time actions are done. We have the folders in place. The right installs and the prototype firewall python script is in the right folder.
Now we do the things that need doing every time after a restart:

### To start the firewall
open Terminal

```
~ % brew update

~ % brew upgrade

~ % cd ~/Developer/WireFall

WireFall % source venv/bin/activate

(venv) % sudo python3 nerdathron3000.py
```
When done go back in the Terminal & then:

```
control-C

(venv) % deactivate

WireFall % exit
```

quit Terminal


>
---
