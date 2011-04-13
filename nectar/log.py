"""A simple logging module. 
Basically it makes pythons logging module even easier by having a preconfigured loggin setup."""
import logging
import config

logging.basicConfig(filename=config.debug_file, level=logging.DEBUG)

def log(msg):
	logging.debug(msg)
	
