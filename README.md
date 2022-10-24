# RCOS I/O
The final RCOS web client. Built on the RCOS database via Hasura and an extremely safe and boring Python Flask stack.

# Motivation

The RCOS website goes through a periodic cycle of being frantically written, never finished, losing the maintainers to graduation, falling out of use, and then eventually being rewritten. We need to **break** this cycle! Below are the reasonings for the technologies used.

## Stack

### Python

Python is a well-known, general purpose language taught at RPI. It has a huge ecosystem and support community. Pick a random RCOS Coordinator or member and they will be comfortable with Python. Every future group of Coordinators will likely have at least a few Python developers, and this cannot be said for less popular languages. It has happened before that all Coordinators present don't know the language the current RCOS website used. That can't happen again.

#### Flask

Flask is an extremely popular Python microframework. It's simple, powerful, easy to deploy, and easy to find answers to online. It was chosen over a larger framework like Django as we don't need the "batteries included" and added complexity.

A traditional server-rendered website is preferred to a fancy, modern single page application because it is simpler to understand, less code to write (no separate frontend and backend projects) and no crazy Javascript build steps that require understanding of 10 different tools and configuration files. Do we need React for a CRUD application that isn't real-time or particularly interactive? No.

#### Bootstrap CSS

Mocked for being easy-to-use and generic, that's exactly the reason to use it here! It is recognizable to developers, easy to pickup, and avoids the need for custom CSS in most cases. Less written CSS is better CSS.

## Developing Locally

Setup is very straightforward.

### Requirements
1. Python 3.10.x

### Setup

1. `python3 -m venv ./venv`
2. `source ./venv/bin/activate`
3. `pip install -r requirements.txt` (note: `pip` and not `pip3`)
4. `cp .env.example .env`
5. Fill out `.env` with valid values

### Running

1. `source ./venv/bin/activate`
2. `flask run`

## Deploying

~~The deployment at https://rcos.io automatically deploys on updates to the `main` branch!~~ (will be true)

## License

MIT