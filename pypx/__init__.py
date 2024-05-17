from .echo import Echo
from .find import Find
from .listen import Listen
from .move import Move
from .report import Report
from .nxstatus import Status
from .do import Do
from .push import Push
from .register import Register
from .pfstorage import swiftStorage, fileStorage


def echo(opt={}):
    return Echo(opt).run()


async def find(opt={}):
    return await Find(opt).run(opt)


def listen(opt={}):
    return Listen(opt).run()


def move(opt={}):
    return Move(opt).run(opt)


def report(opt={}):
    return Report(opt).run(opt)


def do(opt={}):
    return Do(opt).run(opt)


async def status(opt={}):
    return await Status(opt).run(opt)


def push(opt={}):
    return Push(opt).run(opt)


def register(opt={}):
    return Register(opt).run(opt)


def swiftStore(opt={}):
    if opt.get("str_storeBaseLocation"):
        return fileStorage(opt).run(opt)
    else:
        return swiftStorage(opt).run(opt)
