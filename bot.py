import socket
import ssl
import logging
import os
import importlib.util
import re
import atexit
import json
from typing import Callable, Optional

with open('settings.json', 'r') as f:
    settings = json.load(f)

SERVER   = settings["server"]
PORT     = settings["port"]
NICK     = settings["nick"]
REALNAME = settings["realname"]
PASSWORD = settings["password"]
LOGFILE  = settings.get("logfile", "bot.log")
USE_SSL  = settings.get("use_ssl", True)
CHANNEL  = settings.get('default_channel')

logging.basicConfig(
    filename=LOGFILE,
    level=logging.INFO,
    format="%(asctime)s - %(message)s"
)

class Bot:

    # send raw
    def __call__(self, message, raise_on_exc=False, *args, **kwds):
        if hasattr(self, 'sock') and self.sock:
            try:
                self.sock.send((message + "\r\n").encode("utf-8"))
                print(">>>", message)
            except Exception as e:
                print(e)
                if raise_on_exc:
                    raise e
        else:
            raise AttributeError(f'Sock not initialized.')

    def __init__(
            self,
            server,
            port,
            nick,
            realname,
            default_channel:Optional[str]=None,
            password:Optional[str]=None,
            prefix="!"
        ):

        self.Connected = False

        ######################
        def _load_commands() -> dict[str, Callable]:
            '''Load the commands from the `./command/` folder.'''
            commands = {}
            commands_dir = os.path.join(os.path.dirname(__file__), "command")
            for fname in os.listdir(commands_dir):
                if fname.endswith(".py") and not fname.startswith("_"):
                    mod_name = fname[:-3]
                    mod_path = os.path.join(commands_dir, fname)
                    spec = importlib.util.spec_from_file_location(mod_name, mod_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    # Expect each command file to have a 'main' function
                    if hasattr(module, "main"):
                        commands[mod_name] = getattr(module, "main")
                    logging.info(f'Command Load OK "{fname}"')
            return commands
        ######################

        # load commands
        self.commands = _load_commands()

        # defaults
        self.server = server
        self.port = port
        self.nick = nick
        self.default_channel = default_channel
        self.realname = realname
        self.password = password
        self.prefix = prefix

        self.netadmin_pattern = re.compile(r'@op\.[a-zA-Z0-9.-]+$')

        # memory
        self.user_modes = {}

        atexit.register(lambda: self._quit(message='Terminated'))

        logging.info('Load OK')
        pass

    # connect
    def connect(self):
        raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Less strict SSL context
        context = ssl._create_unverified_context()
        self.sock = context.wrap_socket(raw_sock, server_hostname=self.server)

        self.sock.connect((self.server, self.port))

        if self.password:
            self(f'PASS {self.password}')

        self(f'NICK {self.nick}')
        self(f'USER {self.nick} 0 * :{self.realname}')

        self.Connected = True

    # join channel
    def join_channel(self, channel):
        if self.Connected:
            self(f'JOIN {channel}')

    # send message to target
    def send_message(self, target, message):
        if self.Connected:
            self(f'PRIVMSG {target} :{message}')

    # chanop
    def is_chanop(self, channel, user):
        return "o" in self.user_modes.get(channel, {}).get(user, '')

    # internal quit/exit
    def _quit(self, message="Disconnecting"):
        if self.Connected:
            try:
                quit_msg = f'QUIT :{message}'
                print(f'>>> {quit_msg}')
                self(quit_msg, raise_on_exc=True)
            except Exception as e:
                logging.error('Error at shutdown: %s', e)
                print(e)
            finally:
                print('Disconnect Success')
                self.Connected = False

    def handle_message(self, prefix, user, channel, message):
        '''Log the raw '''
        logging.info(f'[{channel}] <{user}> ({prefix}) {message}')

        netadmin = bool(self.netadmin_pattern.search(prefix))

        if not message.startswith(self.prefix):
            return
        
        parts = message[len(self.prefix):].split()
        if not parts:
            return
        
        # PREFIX GETS CALLED HERE
        cmd, *args = parts
        if cmd in self.commands:
            self.commands[cmd](
                self,       # this class
                user,       # user running command
                channel,    # current channel
                netadmin,   # boolean, user is netadmin
                args        # *arguments
            )

        return
    
    def run(self):
        buffer = ""
        while True:
            buffer += self.sock.recv(2048).decode("utf-8", errors='ignore')
            lines = buffer.split('\r\n')
            buffer = lines.pop()

            for line in lines:
                
                if not line:
                    continue

                # DEBUG : Print received line data
                print('<<<', line)
                parts = line.split(' ') # split into parts

                # Server PING
                if line.startswith('PING'):
                    self(f'PONG {parts[1]}')
                    continue

                if len(parts) > 1 and parts[1] == "001":
                    # Login Success
                    if self.default_channel:
                        self.join_channel(self.default_channel)

                # Handles NAMES response
                if len(parts) > 3 and parts[1] == "353": # RPL_NAMREPLY
                    channel = parts[4]
                    users = parts[5:]
                    if channel not in self.user_modes:
                        self.user_modes[channel] = {}
                    for raw_user in users:
                        user = raw_user.lstrip(":@%+")
                        if raw_user.startswith('@'):
                            mode = "o"
                        elif raw_user.startswith('%'):
                            mode = "h"
                        elif raw_user.startswith('+'):
                            mode = ""
                        else:
                            mode = ""
                        self.user_modes[channel][user] = mode
                        
                        print(f'Mode +{mode} given for {raw_user}')

                # Handle PRIVMSG
                if len(parts) > 3 and parts[1] == 'PRIVMSG':
                    prefix = parts[0]
                    user = prefix.split('!')[0][1:]
                    channel = parts[2]
                    message = " ".join(parts[3:])[1:]
                    self.handle_message(prefix, user, channel, message)

if __name__ == "__main__":

    bot = Bot(server=SERVER, port=PORT, nick=NICK, realname=REALNAME, default_channel=CHANNEL, password=PASSWORD)

    bot.connect()
    bot.run()