#!/bin/sh
gunicorn 'driving_theory_test:create_app()' -b 0.0.0.0:$PORT
