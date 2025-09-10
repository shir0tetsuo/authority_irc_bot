from typing import Callable
def main(self:Callable, user, channel, netadmin, args):
    self.send_message(channel, f'{user}: pong!')