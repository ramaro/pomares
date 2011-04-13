"""The serialize module contains methods to encapsulate and decapsulate data between pomares peers."""
import json


def pack(type, obj):
	return json.dumps({type:obj})

def unpack(obj):
	return json.loads(obj)

