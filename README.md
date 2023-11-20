# Consumption-recorder
```cmd
+ ----------------------------------------------------------------------- +
 | __     __           _                               _                   |
 | \ \   / /___  _ __ | |__   _ __  __ _  _   _   ___ | |__   ___          |
 |  \ \ / // _ \| '__|| '_ \ | '__|/ _` || | | | / __|| '_ \ / __| _____   |
 |   \ V /|  __/| |   | |_) || |  | (_| || |_| || (__ | | | |\__ \|_____|  |
 |    \_/  \___||_|   |_.__/ |_|   \__,_| \__,_| \___||_| |_||___/         |
 |                     _          _           _  _         _               |
 |  _ __   _ __  ___  | |_  ___  | | __ ___  | || |  __ _ | |_  ___   _ __ |
 | | '_ \ | '__|/ _ \ | __|/ _ \ | |/ // _ \ | || | / _` || __|/ _ \ | '__||
 | | |_) || |  | (_) || |_| (_) ||   <| (_) || || || (_| || |_| (_) || |   |
 | | .__/ |_|   \___/  \__|\___/ |_|\_\\___/ |_||_| \__,_| \__|\___/ |_|   |
 | |_|                                                                     |
 + ----------------------------------------------------------------------- +
```

~~Small and simple~~ Python project to neatly organize and record the consumption of electricity, gas and water of a rental.
(UI currently only supports German language)

## functionality

- handle the consumptions and tenants for your rental
- create and export statists of the consumptions and tenants


## future plans

- implement personal customizations


## Setup for developers

1. instantiate a venv environment for python v3.11:

    python3.11 must already be installed

    ```cmd
    Consumption-recorder$ py -3.11 -m venv
    ```

2. activate the venv:
    
    - `POSIX`
        
        Shell       | command
        ------------|--------
        bash/zsh    | `$ source ./bin/activate`
        fish        | `$ source ./bin/activate.fish`
        csh/tcsh    | `$ source ./bin/activate.csh`
        PowerShell  | `$ ./bin/Activate.ps1`
    
    - `Windows`:

        Shell       | command
        ------------|--------
        cmd.exe     | `C:.../Consumption-recorder\> Scripts\activate.bat`
        PowerShell  | `PS C:.../Consumption-recorder\> Scripts\Activate.ps1`

3. install all pip requirements:

    ```cmd
    Consumption-recorder$ python -m pip install -r requirements.txt
    ```


<!--
---
## NOTES to myself:
- When relocating the venv folder it is mandatory to change the activation scripts
    
    dependent on your OS following activation scripts are in the `bin/` or `Scripts/` folder

    - `./activate.bat`:
        ```cmd
        set VIRTUAL_ENV=new_path_to_venv\Consumption-recorder
        ```
    
    - `./activate.bat`:
        ```bash
        VIRTUAL_ENV="new_path_to_venv\Consumption-recorder"
        ```
-->