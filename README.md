# Trading Agorithm

This is a python trading algorithm for the FOREX market.


## Installing Python and Pip


### WINDOWS

- **Install Python**

Go to https://www.python.org/downloads/windows/ and download 
    
Select either Windows x86-64 executable installer for 64-bit or Windows x86 executable installer for 32-bit

Once you have downloaded an installer, simply run the installer by double clicking
    
Follow installer instructions
    
You can check if the installation worked:
    
    $ python -V
    
The output should be:
    
    Python 3.7.2


- **Install Pip**

Download get-pip.py from https://bootstrap.pypa.io/get-pip.py to a folder on your computer.
    
Open a command prompt and navigate to the folder containing get-pip.py.
    
Run the following command:
    
    $ python get-pip.py
    
You can verify that Pip was installed correctly by opening a command prompt and entering the following command:
    
    $ pip -V
    
You should see output similar to the following:
    
    pip 18.0 from c:\users\administrator\appdata\local\programs\python\python37\lib\site-packages\pip (python 3.7)


    
### MAC OS X

- **Install Python**

Install brew, Paste this in a macOS Terminal prompt.
    
    $ /usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"

Once brew is installed:
    
    $ brew install python3
    
You can check if the installation worked:
    
    $ python3 --version
    
The output should be:
    
    Python 3.7.2


- **Install Pip**

Start with:

    $ sudo easy_install pip
    
Check that the installation worked:
    
    $ pip --version
    
The output should be:
    
    pip 19.1.1 from /Users/luis/virtualenvironment/interface/lib/python3.7/site-packages/pip (python 3.7)
    

    

### UBUNTU 16.10 OR NEWER 16.10 or newer

- **Install Python**

Start with:

    $ sudo apt-get update
    $ sudo apt-get install python3.6
    
You can check if the installation worked:
    
    $ python3 --version
    
The output should be:
    
    Python 3.7.2


- **Install Pip**

Start with:
   
    $ sudo apt update 
    
    $ sudo apt install python3-pip
    
Once the installation is completed, verify the installation by checking the pip version:
    
    $ pip3 --version
    
The version number may vary, but it will look something like this:
    
    pip 9.0.1 from /usr/lib/python3/dist-packages (python 3.6)
    
    
    
## Requirements

Create a virtual environment:

**MAC OS X**

    $ pip install virtualenv
    
    $ virtualenv my_venv
    
    $ source my_venv/bin/activate
   
**WINDOWS**

    $ pip install virtualenv
    
    $ virtualenv my_venv
    
    $ my_venv\Scripts\activate

**UBUNTU**

    $ sudo apt-get update
    
    $ sudo pip3 install virtualenv 
    
    $ virtualenv venv
    
    $ source venv/bin/activate

Once you have downloaded the repository, and with python and pip installed, go the the repository folder and install the requirements:

    $ pip install requirements.txt    


## Run 

To run the program, go to the repository folder:
    
    $ python3 Main.py
