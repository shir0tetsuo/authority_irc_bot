from typing import Callable
def main(self:Callable, user, channel, netadmin, args):
    
    modes = self.user_modes.get(channel, {})
    self.send_message(channel, f'netadmin: {netadmin}')
    for u, m in modes.items():
        self.send_message(channel, f'{u}: {m}')