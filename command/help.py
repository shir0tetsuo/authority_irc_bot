from typing import Callable
def main(self:Callable, user, channel, netadmin, args):
    
    commands = ', '.join([self.prefix+key for key in self.commands.keys()])
    self.send_message(channel, f'{commands}')