from .base import Base

class Move(Base):
    """docstring for Move."""
    def __init__(self, arg):
        super(Move, self).__init__(arg)
    
    def run(self):
        print('run Move')