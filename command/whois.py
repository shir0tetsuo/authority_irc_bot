def main(self, user, channel, netadmin, args):
    if not args:
        self.send_message(channel, "Usage: !whois <nick>")
        return
    target_nick = args[0]
    self(f"WHOIS {target_nick}")