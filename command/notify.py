from typing import Callable
import subprocess

def main(self:Callable, user, channel, netadmin, args):
    msg = f'{user} ({channel}): ' + " ".join(args)

    if not args:
        self.send_message(channel, "Usage: !discord <message>")
        return
    
    # Send desktop notification (Ubuntu)
    try:
        subprocess.run(['notify-send', 'IRC Alert', msg])
    except Exception as e:
        print(f"Local notification failed: {e}")
