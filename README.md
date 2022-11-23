# RCOS I/O

The final RCOS web client. Built on the RCOS database via Hasura and an extremely safe and boring Python Flask stack.


## Local Development

Setup is very straightforward. If you run into **any** problems big or small while going through these stesp, open an [Issue](https://github.com/Apexal/rcos_io/issues/new). It will greatly help us improve the docs.

### Requirements
1. Python 3.8 or above
2. An understanding of [Flask](https://flask.palletsprojects.com/en/2.2.x/quickstart/) 

### Setup

#### Setting up the Flask server

1. `python3 -m venv ./venv`
    or `python -m venv ./venv` for Windows
2. `source ./venv/bin/activate`
    - or `.\venv\Scripts\Activate.ps1` (in PowerShell) for Windows
3. `pip install -r requirements.txt` (note: `pip` and not `pip3`)
4. `pre-commit install`
5. `cp .env.example .env`
6. Fill out `.env` with valid values
    - these come from current Coordinators


### Running

1. `source ./venv/bin/activate`
    - or `.\venv\Scripts\Activate.ps1` (in PowerShell) for Windows
2. `flask run`
3. Navigate to the URL printed in the console, typically http://127.0.0.1:5000

Any code or template changes you make will automatically restart the server.

## Deploying to Production

Pushes to `main` automatically deploy to https://rcos.up.railway.app/

## License

MIT