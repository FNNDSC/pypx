from .echo   import Echo
from .find   import Find
from .listen import Listen
from .move   import Move

def echo(opt={}):
    return Echo(opt).run()

def find(opt={}):
    return Find(opt).run(opt)

def listen(opt={}):
    return Listen(opt).run()

def move(opt={}):
    return Move(opt).run(opt)