### This document contain instructions on how to iterate on this repo.

## Current state:
start-dev.sh for dev server start, but don't run this during iteration as I will manually run it at the start

start.sh is production and can be referenced to understand how this project is setup. also don't run this, I'll manually run it at the beginning

This project is only using a single port 8000 by default, both frontend and backend.

if you need error checking, "npm run build" is what you can run

please make sure to always use the environment variables in the .env file and never hardcode port and site names
In this dev server always adhere to .env ports, as we're using single port for development. when you start frontend dev it will start on port 5175 etc, but we're using 8000.

When starting the python backend, make sure to use uv

