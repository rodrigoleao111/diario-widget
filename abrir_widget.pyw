import os
import runpy
import sys

raiz = os.path.dirname(os.path.abspath(__file__))
os.chdir(raiz)
sys.path.insert(0, raiz)
sys.argv = ["diario", "widget"]
runpy.run_module("diario", run_name="__main__", alter_sys=True)
