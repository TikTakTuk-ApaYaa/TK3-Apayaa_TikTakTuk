#!/usr/bin/env python3
from livereload import Server
import os

# Create a livereload server
server = Server()

# Watch for changes in HTML files
server.watch('*.html')

# Start the server on port 8080
server.serve(port=8080, host='localhost', root='.')