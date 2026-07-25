import sys, os
sys.path.insert(0, r"C:\Users\ADMIN\Downloads\RAC-Compiler-main (1)\RAC-Compiler-main")
from libcompiler import loader
attrs = [a for a in dir(loader) if not a.startswith('_') and not callable(getattr(loader, a))]
print("Loader attributes:", attrs)

from libcompiler import engine
attrs = [a for a in dir(engine) if not a.startswith('_') and not callable(getattr(engine, a))]
print("Engine attributes:", attrs)

from libcompiler import handlers
attrs = [a for a in dir(handlers) if not a.startswith('_') and not callable(getattr(handlers, a))]
print("Handlers attributes:", attrs)
